import json
from fastapi import APIRouter, Request, HTTPException, status, Header
from fastapi.responses import HTMLResponse, JSONResponse, Response
from pydantic import ValidationError
from sqlmodel import Session, select, inspect, SQLModel, func
from sqlalchemy.orm import joinedload
from sqlalchemy.sql import sqltypes
from sqlmodel.sql.sqltypes import AutoString
from app.database_config import engine
from app.templates.jinja_functions import templates
from app.models import Manufacturer, ManufacturerCreate, ManufacturerRead
from app.models import Measureable,MeasureableCreate, MeasureableRead
from app.models import Machine, MachineCreate, MachineRead
from app.models import User, UserCreate, UserRead
from app.models import Tool, ToolCreate, ToolRead, ToolAttribute, ToolAttributeCreate, ToolAttributeRead
from app.models import ToolLife, ToolLifeCreate, ToolLifeRead
from app.models import ToolType, ToolTypeCreate, ToolTypeRead
from app.models import Recipe, RecipeCreate, RecipeRead
from app.models import ChangeReason, ChangeReasonCreate, ChangeReasonRead
from typing import Type, Dict, Any, ForwardRef, get_origin, get_args, List

# Create a mapping of string names to SQLModel classes
model_mapping = {
    'changereason': {"model": ChangeReason, "create": ChangeReasonCreate, "read": ChangeReasonRead},
    "manufacturer": {"model": Manufacturer, "create": ManufacturerCreate, "read": ManufacturerRead},
    "machine": {"model": Machine, "create": MachineCreate, "read": MachineRead},
    'measureable':{'model': Measureable, 'create': MeasureableCreate, 'read': MeasureableRead},
    "user": {"model": User, "create": UserCreate, "read": UserRead},
    'tool': {"model": Tool, "create": ToolCreate, "read": ToolRead},
    'toollife': {"model": ToolLife, "create": ToolLifeCreate, "read": ToolLifeRead},
    'toolattribute': {"model": ToolAttribute, "create": ToolAttributeCreate, "read": ToolAttributeRead},
    'tooltype': {"model": ToolType, "create": ToolTypeCreate, "read": ToolTypeRead},
    'recipe': {"model": Recipe, "create": RecipeCreate, "read": RecipeRead},
}

def create_generic_router(
    model: Type[SQLModel],
    read_model: Type[SQLModel],
    create_model: Type[SQLModel],
    update_model: Type[SQLModel],
    item_type: str,
    extra_context: Dict[str, Any] = None
):
    router = APIRouter()

    router.context = {
        'model': create_model,
        'item_type': item_type,
        'form_action': f'/engineer/{item_type.lower()}s',
        'relationship_options': {},
        'children': {},
    }

    def get_relations_and_children(id:int = None):
        relations = {}
        children = {}
        with Session(engine) as session:
            for field_name, field in create_model.model_fields.items():
                if field_name != "id":
                    field_type = field.annotation
                    if get_origin(field_type) is list:
                        children[field_name] = {}

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
                            if id:
                                related_items = session.exec(select(related_model).where(getattr(related_model, f"{item_type.lower()}_id") == id)).all()
                                # Get the read model for this relation
                                related_read_model = related_model_info['read']
                                relations[field_name] = [
                                    {field: getattr(item, field) for field in related_read_model.model_fields.keys()}
                                    for item in related_items
                                ]
                                children[field_name]['instances'] = relations[field_name]
                                
                            # Add referred model information
                            children[field_name]['create_model'] = related_model_info['create']
                            children[field_name]['name'] = related_model.__name__

                    elif field_name.endswith('_id'):
                        related_model_name = ''.join(word.capitalize() for word in field_name[:-3].split('_'))
                        related_model = globals().get(related_model_name)
                        if related_model:
                            related_items = session.exec(select(related_model)).all()
                            # Get the model info and read model
                            related_model_info = model_mapping.get(related_model_name.lower())
                            if related_model_info:
                                related_read_model = related_model_info['read']
                                relations[field_name[:-3]] = [
                                    {field: getattr(item, field) for field in related_read_model.model_fields.keys()}
                                    for item in related_items
                                ]
        for childname in children:
            if relations.get(childname):
                del relations[childname]

        return relations, children
    

    @router.get("/", response_class=HTMLResponse)
    async def get_items(request: Request):
        router.context['relationship_options'], router.context['children'] = get_relations_and_children()

        if extra_context:
            router.context.update(extra_context)

        return templates.TemplateResponse(
            request=request,
            name="engineer/data.html.j2",
            context=router.context
        )

    @router.get("/{field_name}/referred_form", response_class=HTMLResponse)
    async def get_referred_form(field_name: str, request: Request):
        referred_child = router.context['children'].get(field_name)
        if not referred_child:
            raise HTTPException(status_code=404, detail="Referred Child not found")
        
        referred_model = referred_child['create_model']
        if not referred_model:
            raise HTTPException(status_code=404, detail="Referred model not found")

        return templates.TemplateResponse(
            request=request,
            name="engineer/partials/referred_model_modal.html.j2",
            context={
                "model": referred_model,
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
        def get_joinedload_options(model: SQLModel) -> List[joinedload]:
            """
            Generates joinedload options for a given SQLAlchemy model.
            It will eagerly load the first-level relationships, while keeping the nested relationships as IDs.
            """
            joinedload_options = []
            for name in model.__sqlmodel_relationships__.keys():
                joinedload_options.append(joinedload(getattr(model, name)))
            return joinedload_options
        
        filters = request.query_params
        statement = select(model).options(*get_joinedload_options(model))

        # Apply filters to the statement
        for key, value in filters.items():
            if value and key != 'with_filter':
                statement = statement.where(getattr(read_model, key).in_(value.split(','))).options(*get_joinedload_options(model))

        with Session(engine) as session:
            items = session.exec(statement).unique().all()

        # Trim the full items according to the read_model
        # items = [
        #     {field: getattr(item, field) for field in read_model.__fields__ if field != 'id'}
        #     for item in items
        # ]

        # For full page load, return the complete template
        return templates.TemplateResponse(
            request=request,
            name="engineer/partials/list.html.j2",
            context={"items": items, 'item_type': item_type, 'read_model': read_model}
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
        context = router.context.copy()
        context['relationship_options'], context['children'] = get_relations_and_children(item_id)
        
        with Session(engine) as session:
            db_item = session.exec(select(model).where(model.id == item_id)).one_or_none()
            
        if not db_item:
            raise HTTPException(status_code=404, detail=f"{item_type} with id {item_id} not found")
        
        context['item'] = db_item
        context['model'] = update_model
            
        # Add this debug print
        print(f"Update Context: {context}")
        
        return templates.TemplateResponse(
            request=request,
            name="engineer/partials/info_modal.html.j2",
            context=context
        )

    async def get_form_data(request: Request):
        form_data = await request.form()
        form_dict: Dict[str, Any] = {}
        existing_relations: Dict[str, Any] = {}
        new_relations: Dict[str, Any] = {}

        for field_name, value in form_data._list:
            if not value:
                continue
            if field_name in update_model.model_fields:
                if update_model.model_fields[field_name].annotation is bool:
                    form_dict[field_name] = form_data[field_name] == 'on'
                else: 
                    form_dict[field_name] = form_data[field_name]
            elif field_name.endswith('[]'):
                list_field_name = field_name.rstrip('[]')
                if list_field_name not in existing_relations:
                    existing_relations[list_field_name] = []
                existing_relations[list_field_name].append(int(value))
            elif field_name.endswith('_new'):
                new_relations[field_name.rstrip('_new')] = json.loads(value)

        return form_dict, existing_relations, new_relations
    

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
                # return JSONResponse(content={'message': f'{item_type} Database conflict: {str(e)}'}, status_code=status.HTTP_409_CONFLICT)
                raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(e))

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
    async def update_item(item_id: int, request: Request):
        form_dict, existing_relations, new_relations = await get_form_data(request)

        if item_id != int(form_dict['id']):
            raise HTTPException(status_code=400, detail=f"Path {item_type.lower()}_id does not match form data id")
        
        with Session(engine) as session:
            item = session.exec(select(model).where(model.id == item_id)).one_or_none()
            if not item:
                raise HTTPException(status_code=404, detail=f"{item_type} not found")
            
            # Update main item fields
            try:
                validated_data = update_model(**form_dict)
                for key, value in validated_data.model_dump().items():
                    if key in form_dict and key != 'id':  # Only update fields that were sent in the form
                        setattr(item, key, value)
            except ValidationError as e:
                raise HTTPException(status_code=422, detail=str(e))

            # Update existing relations
            for relation_name, relation_ids in existing_relations.items():
                relation_list = getattr(item, relation_name)
                to_keep = []
                to_delete = []
                for instance in relation_list:
                    if instance.id in relation_ids:
                        to_keep.append(instance)
                    else:
                        to_delete.append(instance)

                # Delete instances not in relation_ids
                for instance in to_delete:
                    session.delete(instance)
                
                # Update relation_list with instances to keep
                relation_list[:] = to_keep

            # Add new relations
            for relation_name, new_items in new_relations.items():
                relation_list = getattr(item, relation_name)
                related_model_info = model_mapping.get(relation_name.replace("_","").rstrip('s').lower())
                if related_model_info:
                    related_create_model = related_model_info['create']
                    for new_item_data in new_items:
                        new_item_data[f'{item_type.lower()}_id'] = item_id
                        try:
                            validated_new_item = related_create_model(**new_item_data)
                            new_item = related_model_info['model'](**validated_new_item.model_dump())
                            relation_list.append(new_item)
                        except ValidationError as e:
                            raise HTTPException(status_code=422, detail=f"Validation error in {relation_name}: {str(e)}")

            try:
                session.add(item)
                session.commit()
                session.refresh(item)
            except Exception as e:
                session.rollback()
                raise HTTPException(status_code=500, detail=f"An error occurred while updating the {item_type}: {str(e)}")

        return JSONResponse(content={"message": f"{item_type} updated successfully"}, status_code=202)

    return router
