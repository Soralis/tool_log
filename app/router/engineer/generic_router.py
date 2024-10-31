import json
from fastapi import APIRouter, Request, Form, HTTPException, status, Header
from fastapi.responses import HTMLResponse, JSONResponse, Response
from pydantic import ValidationError
from sqlmodel import Session, select, inspect, SQLModel, func
from sqlalchemy.sql import sqltypes
from sqlmodel.sql.sqltypes import AutoString
from sqlalchemy.orm.collections import InstrumentedList
from app.database_config import engine
from app.templates.jinja_functions import templates
from app.models import Manufacturer, ManufacturerCreate
from app.models import Machine, MachineCreate
from app.models import User, UserCreate
from app.models import Tool, ToolCreate, ToolAttribute, ToolAttributeCreate
from app.models import ToolLife, ToolLifeCreate
from app.models import ToolType, ToolTypeCreate
from app.models import Recipe, RecipeCreate
from typing import Annotated, Type, Dict, Any, ForwardRef, get_origin, get_args

# Create a mapping of string names to SQLModel classes
model_mapping = {
    "manufacturer": {"model": Manufacturer, "create": ManufacturerCreate},
    "machine": {"model": Machine, "create": MachineCreate},
    "user": {"model": User, "create": UserCreate},
    'tool': {"model": Tool, "create": ToolCreate},
    'toollife': {"model": ToolLife, "create": ToolLifeCreate},
    'toolattribute': {"model": ToolAttribute, "create": ToolAttributeCreate},
    'tooltype': {"model": ToolType, "create": ToolTypeCreate},
    'recipe': {"model": Recipe, "create": RecipeCreate}
    # Add other mappings as needed
}

def create_generic_router(
    model: Type[SQLModel],
    create_model: Type[SQLModel],
    update_model: Type[SQLModel],
    item_type: str,
    extra_context: Dict[str, Any] = None
):
    router = APIRouter()

    @router.get("/", response_class=HTMLResponse)
    async def get_items(request: Request):
        context = {
            'model': create_model,
            'item_type': item_type,
            'form_action': f'/engineer/{item_type.lower()}s',
            'relationship_options': {},
            'list_relationships': [],
            'referred_models': {}
        }

        with Session(engine) as session:
            for field_name, field in create_model.model_fields.items():
                if field_name != "id":
                    field_type = field.annotation
                    if get_origin(field_type) is list:
                        context['list_relationships'].append(field_name)

                        # Handle ForwardRef
                        arg_type = get_args(field_type)[0]
                        if isinstance(arg_type, ForwardRef):
                            related_model_name = arg_type.__forward_arg__
                        elif hasattr(arg_type, '__name__'):
                            related_model_name = arg_type.__name__
                        else:
                            related_model_name = str(arg_type)

                        related_model_info = model_mapping.get(related_model_name.lower())
                        if related_model_info:
                            related_model = related_model_info['model']
                            related_items = session.exec(select(related_model)).all()
                            context['relationship_options'][field_name] = [
                                {"id": item.id, "name": getattr(item, 'name', str(item))}
                                for item in related_items
                            ]
                            # Add referred model information
                            context['referred_models'][field_name] = {
                                'model': related_model_info['create'],
                                'name': related_model.__name__
                            }
                    elif field_name.endswith('_id'):
                        related_model_name = ''.join(word.capitalize() for word in field_name[:-3].split('_'))
                        related_model = globals().get(related_model_name)
                        if related_model:
                            related_items = session.exec(select(related_model)).all()
                            context['relationship_options'][field_name[:-3]] = [
                                {"id": item.id, "name": getattr(item, 'name', str(item))}
                                for item in related_items
                            ]

        if extra_context:
            context.update(extra_context)

        # Store the context in a closure so it can be accessed by other endpoints
        router.context = context

        return templates.TemplateResponse(
            request=request,
            name="engineer/data.html.j2",
            context=context
        )

    @router.get("/{field_name}/referred_form", response_class=HTMLResponse)
    async def get_referred_form(field_name: str, request: Request):
        referred_model = router.context['referred_models'].get(field_name)
        if not referred_model:
            raise HTTPException(status_code=404, detail="Referred model not found")

        return templates.TemplateResponse(
            request=request,
            name="engineer/partials/referred_model_modal.html.j2",
            context={
                "model": referred_model['model'],
                "field_name": field_name,
                "form_action": f"/engineer/{field_name.lower()}"
            }
        )

    @router.get("/filter")
    async def get_filter(request: Request):
        with Session(engine) as session:
            filter_options = get_filter_options(model, session)  # You'll need to implement this function
        return templates.TemplateResponse(
            request=request,
            name="engineer/partials/filter.html.j2",
            context={"filter_options": filter_options, 'item_type': item_type}
        )

    @router.get("/list", response_class=HTMLResponse)
    async def get_item_list(request: Request, hx_request: str = Header(None)):
        filters = request.query_params
        statement = select(model)

        # Apply filters to the statement
        for key, value in filters.items():
            if value and key != 'with_filter':
                statement = statement.where(getattr(model, key).in_(value.split(',')))

        with Session(engine) as session:
            results = session.exec(statement)
            items = results.all()


        # For full page load, return the complete template
        return templates.TemplateResponse(
            request=request,
            name="engineer/partials/list.html.j2",
            context={"items": items, 'item_type': item_type}
        )

    def get_filter_options(model, session):
        filter_options = {}
        columns = inspect(model).columns

        for column in columns:
            if column.name != 'id':  # Exclude id from filters
                if isinstance(column.type, (sqltypes.String, sqltypes.Integer, sqltypes.Enum, sqltypes.JSON, sqltypes.DateTime, AutoString)):
                    # Query unique values for this column
                    unique_values = session.query(func.distinct(getattr(model, column.name))).all()
                    # Flatten the result and convert to strings
                    unique_values = [str(value[0]) for value in unique_values if value[0] is not None]
                    filter_options[column.name] = sorted(unique_values)
                elif isinstance(column.type, sqltypes.Boolean):
                    filter_options[column.name] = [True, False]
                else:
                    print(f"Unhandled column type for {column.name}: {type(column.type)}")
        
        return filter_options

    @router.get("/{item_id}/info", response_class=HTMLResponse)
    async def get_item_info(item_id: int, request: Request):
        statement = select(model).where(model.id == item_id)
        with Session(engine) as session:
            results = session.exec(statement)
            db_item = results.one_or_none()
            
            if not db_item:
                raise HTTPException(status_code=404, detail=f"{item_type} not found")
            
            # Fetch related items
            item_dict = db_item.model_dump()
            related_items = {}
            relationship_options = {}
            
            # Dynamically fetch all relationships
            for relation in db_item.__class__.__mapper__.relationships.keys():
                related_objects = getattr(db_item, relation)
                if related_objects is not None:
                    if isinstance(related_objects, InstrumentedList):
                        # It's an iterable (like InstrumentedList)
                        related_items[relation] = {"amount": len(related_objects)}
                    else:
                        # It's a singular item
                        related_items[relation] = {
                            "id": related_objects.id, 
                            "name": getattr(related_objects, 'name', str(related_objects))
                        }
                        # pass
                    
                    # Fetch all possible options for this relationship
                    related_model = db_item.__class__.__mapper__.relationships[relation].mapper.class_
                    options_statement = select(related_model)
                    options = session.exec(options_statement).all()
                    relationship_options[relation] = [{"id": opt.id, "name": getattr(opt, 'name', str(opt))} for opt in options]
            
            # I dont need the same field as relation and as attribute
            for item in item_dict.keys():
                if item.replace('_id', '') in related_items.keys():
                    del related_items[item.replace('_id', '')]

            context = {
                "item": item_dict,
                "related_items": related_items,
                "relationship_options": relationship_options,
                "item_type": item_type,
                "model": update_model,
                "form_action": f'/engineer/{item_type.lower()}s',
                "submit_text": "Update"
            }
            
            # Add this debug print
            print(f"Context: {context}")
            
            if extra_context:
                context.update(extra_context)
            
            return templates.TemplateResponse(
                request=request,
                name="engineer/partials/info_modal.html.j2",
                context=context
            )

    @router.post("/", response_class=JSONResponse)
    async def create_item(request: Request):
        
        form_data = await request.form()
        form_dict: Dict[str, Any] = {}
        references_dict: Dict[str, Any] = {}

        for field_name in create_model.model_fields.keys():
            if field_name in form_data:
                # Handle regular fields
                form_dict[field_name] = form_data[field_name]
            elif f"{field_name}[]" in form_data:
                if form_data.get(f"{field_name}[]"):
                    form_dict[field_name] = json.loads(form_data.get(f"{field_name}[]"))
            if f"{field_name}_new" in form_data:
                # Handle array fields
                references_dict[f"{field_name}"] = json.loads(form_data.get(f"{field_name}_new"))

        # Validate the data manually
        try:
            validated_data = create_model(**form_dict)
            item = model(**validated_data.model_dump())
        except ValidationError as e:
            raise HTTPException(status_code=422, detail=str(e))
        
        with Session(engine) as session:
            session.add(item)
            try:
                session.commit()
                session.refresh(item)
            except Exception as e:
                raise HTTPException(status_code=500, detail=str(e))

            db_additions = []
            for field_name in references_dict:
                if field_name in create_model.model_fields and references_dict[field_name]:
                    # Handle new models
                    related_model_info = model_mapping.get(field_name.replace("_","").rstrip("s").lower())
                    related_model = related_model_info['model']
                    for new_model in references_dict[field_name]:
                        new_model[item_type.lower() + "_id"] = item.id
                        try:
                            validated_new_refer_model = related_model(**new_model)
                            db_additions.append(validated_new_refer_model)
                        except ValidationError as e:
                            raise HTTPException(status_code=422, detail=str(e))

            session.add_all(db_additions)
            try:
                session.commit()
                session.refresh(item)
            except Exception as e:
                raise HTTPException(status_code=500, detail=str(e))
        
        return JSONResponse(content={'message': f'{item_type} successfully created'}, status_code=201)



    # async def create_item(form_data: Annotated[create_model, Form()],
    #                       request: Request):
    #     item_data = form_data.model_dump()
    
    #     # Handle new referred models
    #     for field_name in create_model.model_fields:
    #         if field_name.endswith('_new'):
    #             base_field = field_name[:-4]
    #             new_models_json = request.form.get(field_name)
    #             if new_models_json:
    #                 new_models = json.loads(new_models_json)
    #                 if base_field not in item_data:
    #                     item_data[base_field] = []
    #                 item_data[base_field].extend(new_models)
        
    #     item = model(**item_data)
    #     # item = model(**form_data.model_dump())
    #     with Session(engine) as session:
    #         session.add(item)
    #         try:
    #             session.commit()
    #             session.refresh(item)
    #         except Exception as e:
    #             raise HTTPException(status_code=500, detail=str(e))
    #     return JSONResponse(content={'message':f'{item_type} successfully created'}, status_code=201)

    @router.delete("/{item_id}")
    def delete_item(item_id: int):
        print('delete item was called')
        statement = select(model).where(model.id == item_id)
        with Session(engine) as session:
            results = session.exec(statement)
            item = results.one_or_none()
            if not item:
                raise HTTPException(status_code=404, detail=f"{item_type} not found")
            session.delete(item)
            session.commit()
        return Response(status_code=status.HTTP_204_NO_CONTENT)

    @router.put("/{item_id}")
    async def update_item(item_id: int, 
                          form_data: Annotated[update_model, Form()],
                          request: Request):
        if item_id != form_data.id:
            raise HTTPException(status_code=400, detail=f"Path {item_type.lower()}_id does not match form data id")
        
        item_data = form_data.model_dump(exclude_unset=True)

        # Handle new referred models
        for field_name in update_model.model_fields:
            if field_name.endswith('_new'):
                base_field = field_name[:-4]
                new_models_json = request.form.get(field_name)
                if new_models_json:
                    new_models = json.loads(new_models_json)
                    if base_field not in item_data:
                        item_data[base_field] = []
                    item_data[base_field].extend(new_models)

        statement = select(model).where(model.id == item_id)
        with Session(engine) as session:
            results = session.exec(statement)
            item = results.one_or_none()
            if not item:
                raise HTTPException(status_code=404, detail=f"{item_type} not found")
            
            for key, value in item_data.items():
                setattr(item, key, value)

            try:
                session.add(item)
                session.commit()
                session.refresh(item)
            except Exception as e:
                raise HTTPException(status_code=500, detail=str(e))

        return JSONResponse(content={"message": f"{item_type} updated successfully"}, status_code=202)

    return router

