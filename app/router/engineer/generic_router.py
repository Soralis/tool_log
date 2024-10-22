from fastapi import APIRouter, Request, Form, HTTPException, status, Header
from fastapi.responses import HTMLResponse, JSONResponse, Response
from sqlmodel import Session, select, inspect, SQLModel, func
from sqlalchemy.sql import sqltypes
from sqlmodel.sql.sqltypes import AutoString
from sqlalchemy.orm.collections import InstrumentedList
from app.database_config import engine
from app.templates.jinja_functions import templates
from app.models.models import Manufacturer, Machine, User, Tool, ToolLife, Recipe
from typing import Annotated, Type, Dict, Any, get_args, get_origin, List

# Create a mapping of string names to SQLModel classes
model_mapping = {
    "manufacturer": Manufacturer,
    "machine": Machine,
    "user": User,
    'tool': Tool,
    'toollife': ToolLife,
    'recipe': Recipe
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
            'list_relationships': []
        }

        with Session(engine) as session:
            for field_name, field in create_model.model_fields.items():
                if field_name != "id":
                    field_type = field.annotation
                    if get_origin(field_type) is List:
                        context['list_relationships'].append(field_name)
                        related_model_name = get_args(field_type)[0].__name__
                        related_model = globals().get(related_model_name)
                        if related_model:
                            related_items = session.exec(select(related_model)).all()
                            context['relationship_options'][field_name] = [
                                {"id": item.id, "name": getattr(item, 'name', str(item))}
                                for item in related_items
                            ]
                    elif field_name.endswith('_id'):
                        related_model_name = field_name[:-3].capitalize()
                        related_model = globals().get(related_model_name)
                        if related_model:
                            related_items = session.exec(select(related_model)).all()
                            context['relationship_options'][field_name[:-3]] = [
                                {"id": item.id, "name": getattr(item, 'name', str(item))}
                                for item in related_items
                            ]

        if extra_context:
            context.update(extra_context)

        return templates.TemplateResponse(
            request=request,
            name="engineer/data.html.j2",
            context=context
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
                if isinstance(column.type, (sqltypes.String, sqltypes.Integer, sqltypes.Enum, sqltypes.JSON, AutoString)):
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

    @router.post("/")
    async def create_item(form_data: Annotated[create_model, Form()]):
        item = model(**form_data.model_dump())
        with Session(engine) as session:
            session.add(item)
            try:
                session.commit()
                session.refresh(item)
            except Exception as e:
                raise HTTPException(status_code=500, detail=str(e))
        return JSONResponse(content={'message':f'{item_type} successfully created'}, status_code=201)

    @router.delete("/{item_id}")
    def delete_item(item_id: int):
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
    async def update_item(item_id: int, form_data: Annotated[update_model, Form()]):
        if item_id != form_data.id:
            raise HTTPException(status_code=400, detail=f"Path {item_type.lower()}_id does not match form data id")
        
        item_data = form_data.model_dump(exclude_unset=True)

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