import json
from datetime import datetime, time
from fastapi import APIRouter, Request, HTTPException, status, Depends
from fastapi.responses import HTMLResponse, JSONResponse, Response
from pydantic import ValidationError
from sqlmodel import Session, select, inspect, SQLModel, func
from sqlalchemy import Integer, String, Boolean, Float, DateTime, or_, cast
from sqlalchemy.orm import joinedload, RelationshipProperty
from sqlalchemy.sql import sqltypes
from sqlmodel.sql.sqltypes import AutoString
from app.database_config import engine
from app.templates.jinja_functions import templates
from app.models import Manufacturer, ManufacturerCreate, ManufacturerRead
from app.models import Measureable,MeasureableCreate, MeasureableRead
from app.models import Machine, MachineCreate, MachineRead
from app.models import Line, LineCreate, LineRead
from app.models import Workpiece, WorkpieceCreate, WorkpieceRead
from app.models import User, UserCreate, UserRead
from app.models import Shift, ShiftCreate, ShiftRead
from app.models import Tool, ToolCreate, ToolRead, ToolAttribute, ToolAttributeCreate, ToolAttributeRead
from app.models import ToolAttributeValue, ToolAttributeValueCreate, ToolAttributeValueRead
from app.models import ToolLife, ToolLifeCreate, ToolLifeRead
from app.models import ToolPosition, ToolPositionCreate, ToolPositionRead
from app.models import Note, NoteCreate, NoteRead
from app.models import ToolType, ToolTypeCreate, ToolTypeRead
from app.models import ToolSetting, ToolSettingCreate, ToolSettingRead
from app.models import Recipe, RecipeCreate, RecipeRead
from app.models import ChangeReason, ChangeReasonCreate, ChangeReasonRead
from typing import Type, Dict, Any, ForwardRef, get_origin, get_args, List, Optional, Callable
from auth import get_current_operator

# Create a mapping of string names to SQLModel classes
model_mapping = {
    'changereason': {"model": ChangeReason, "create": ChangeReasonCreate, "read": ChangeReasonRead},
    "manufacturer": {"model": Manufacturer, "create": ManufacturerCreate, "read": ManufacturerRead},
    "machine": {"model": Machine, "create": MachineCreate, "read": MachineRead},
    "line": {"model": Line, "create": LineCreate, "read": LineRead},
    'measureable':{'model': Measureable, 'create': MeasureableCreate, 'read': MeasureableRead},
    "user": {"model": User, "create": UserCreate, "read": UserRead},
    'tool': {"model": Tool, "create": ToolCreate, "read": ToolRead},
    'toollife': {"model": ToolLife, "create": ToolLifeCreate, "read": ToolLifeRead},
    'tool_type': {"model": ToolType, "create": ToolTypeCreate, "read": ToolTypeRead},
    'note': {"model": Note, "create": NoteCreate, "read": NoteRead},
    'toolattribute': {"model": ToolAttribute, "create": ToolAttributeCreate, "read": ToolAttributeRead},
    'toolattributevalue': {"model": ToolAttributeValue, "create": ToolAttributeValueCreate, "read": ToolAttributeValueRead},
    'toolsetting': {"model": ToolSetting, "create": ToolSettingCreate, "read": ToolSettingRead},
    'tooltype': {"model": ToolType, "create": ToolTypeCreate, "read": ToolTypeRead}, # needed????
    'toolposition': {"model": ToolPosition, "create": ToolPositionCreate, "read": ToolPositionRead},
    'recipe': {"model": Recipe, "create": RecipeCreate, "read": RecipeRead},
    'shift': {"model": Shift, "create": ShiftCreate, "read": ShiftRead},
    'workpiece': {"model": Workpiece, "create": WorkpieceCreate, "read": WorkpieceRead},
}

def create_generic_router(
    model: Type[SQLModel],
    read_model: Type[SQLModel],
    create_model: Type[SQLModel],
    update_model: Type[SQLModel],
    filter_model: Type[SQLModel],
    item_type: str,
    extra_context: Dict[str, Any] = None,
    fixed_field_callback: Optional[Callable[[], List[Dict[str, Any]]]] = None
):
    router = APIRouter()
    # Store the last search value per-router so we can reset pagination when the search changes
    router.last_search = None

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
                                    {"id": item.id, **{field: getattr(item, field) for field in related_read_model.model_fields.keys() if '__' not in field} }
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
                                related_read_model = related_model_info['model'] # read
                                relations[field_name[:-3]] = [
                                    {field: getattr(item, field) for field in related_read_model.model_fields.keys()}
                                    for item in related_items
                                ]
        for childname in children:
            if relations.get(childname):
                del relations[childname]
        
        # Sort the relations by the items name
        for relation in relations:
            relations[relation] = sorted(relations[relation], key=lambda x: str(x.get('name', '')))
        

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
        
        context = router.context.copy()
        context['model']= referred_model
        context["field_name"]= field_name
        context['form_action']= f'/engineer/{field_name.lower()}'

        return templates.TemplateResponse(
            request=request,
            name="engineer/partials/referred_model_modal.html.j2",
            context=context
        )

    @router.get("/filter")
    async def get_filter(request: Request):
        with Session(engine) as session:
            filter_options = get_filter_options(filter_model, session)
        return templates.TemplateResponse(
            request=request,
            name="engineer/partials/filter.html.j2",
            context={
                "filter_options": filter_options,
                "item_type": item_type,
            }
        )

    @router.get("/list", response_class=HTMLResponse)
    async def get_item_list(request: Request):
        def get_joinedload_options(model: SQLModel, read_model: SQLModel) -> List[joinedload]:
            """
            Generates joinedload options for a given SQLAlchemy model.
            It will eagerly load the first-level relationships that are defined in the read_model, 
            while keeping the nested relationships as IDs.
            """
            joinedload_options = []
            for name in read_model.__fields__.keys():
                # Eagerly load all relationships to prevent detached instance errors
                if hasattr(model, name) and getattr(getattr(model, name), 'property', None):
                    if isinstance(getattr(model, name).property, RelationshipProperty):
                        joinedload_options.append(joinedload(getattr(model, name)))
            return joinedload_options
        
        filters = request.query_params
        statement = select(model).options(*get_joinedload_options(model, read_model))
        # Search support: read `search` query param and build OR across string-like columns
        search_value = request.query_params.get("search")
        # Read offset/limit from client (if provided). We'll reset offset to 0 when search changes.
        raw_offset = request.query_params.get("offset")
        offset = int(raw_offset) if raw_offset is not None else 0
        limit = int(request.query_params.get("limit", 50))

        # If the search value changed since the last request for this router, reset pagination.
        if getattr(router, "last_search", None) != search_value:
            offset = 0
            router.last_search = search_value

        # If searching, build clauses across searchable columns on the model.
        # Exclude Enum columns since PostgreSQL does not support ILIKE between enum and text.
        # For numeric columns (int/float) cast to text so the user can search numbers as strings.
        if search_value:
            try:
                search_clauses = []
                for c in inspect(model).columns:
                    # Skip Enum types entirely
                    if isinstance(c.type, sqltypes.Enum):
                        continue

                    col_attr = getattr(model, c.name)

                    # Textual SQL types: use ilike directly
                    if isinstance(c.type, (sqltypes.String, AutoString)):
                        search_clauses.append(col_attr.ilike(f"%{search_value}%"))
                        continue

                    # Numeric SQL types: cast to text then ilike
                    if isinstance(c.type, (sqltypes.Integer, sqltypes.Float, Integer, Float)):
                        try:
                            search_clauses.append(cast(col_attr, String).ilike(f"%{search_value}%"))
                        except Exception:
                            # If cast fails for any reason, skip this column
                            continue
                        continue

                    # Fallback: if the underlying python type is str, use ilike
                    py_type = getattr(c.type, "python_type", None)
                    if py_type is str:
                        search_clauses.append(col_attr.ilike(f"%{search_value}%"))
                        continue

                    # Last resort: attempt to cast to text and use ilike
                    try:
                        search_clauses.append(cast(col_attr, String).ilike(f"%{search_value}%"))
                    except Exception:
                        # ignore columns we cannot search
                        continue
            except Exception:
                search_clauses = []
            if search_clauses:
                statement = statement.where(or_(*search_clauses))

        # Apply filters to the statement
        def get_column_type(model, key):
            """Get the Python type for a model's column"""
            column = inspect(model).columns[key]
            type_mapping = {
                Integer: int,
                String: str,
                Boolean: bool,
                Float: float,
                DateTime: lambda x: datetime.strptime(x, '%Y-%m-%d %H:%M:%S.%f').date()
            }
            
            for sql_type, python_type in type_mapping.items():
                if isinstance(column.type, sql_type):
                    return python_type
                    
            # Default to string if type is not recognized
            return str
        
        for key, value in filters.items():
            if value and key not in ['with_filter', 'offset', 'limit', 'search']:
                statement = statement.where(
                    getattr(model, key).in_(
                        [get_column_type(model, key)(x) for x in value.split(',')]
                    )
                )
        with Session(engine) as session:
            try:
                order_field = read_model._order_by.default
            except AttributeError:
                order_field = "name"
            try:
                descending = read_model._descending.default
            except AttributeError:
                descending = False
            ordering = getattr(model, order_field)
            if descending:
                ordering = ordering.desc()
            else:
                ordering = ordering.asc()

            # First select primary keys (ids) using the filtered statement so filters/search are respected.
            # Use distinct() to avoid duplicate ids caused by joins and limit+1 to detect has_more.
            # Include the ordering column in SELECT to satisfy PostgreSQL's DISTINCT requirement
            order_attr = getattr(model, order_field)
            id_stmt = statement.with_only_columns(model.id, order_attr).distinct().order_by(ordering).offset(offset).limit(limit + 1)
            id_results = session.exec(id_stmt).all()
            # Extract just the IDs (first element of each tuple)
            ids = [r[0] if isinstance(r, (list, tuple)) else r for r in id_results]

            # Preserve order and uniqueness
            unique_ids = []
            for i in ids:
                if i not in unique_ids:
                    unique_ids.append(i)

            has_more = len(unique_ids) > limit
            page_ids = unique_ids[:limit]

            if page_ids:
                # Load full model instances for the page ids with joinedload options
                items_stmt = select(model).options(*get_joinedload_options(model, read_model)).where(model.id.in_(page_ids))
                items_fetched = session.exec(items_stmt).all()
                items_by_id = {getattr(it, "id"): it for it in items_fetched}
                # Restore original order
                items = [items_by_id[i] for i in page_ids if i in items_by_id]
            else:
                items = []

        # Trim the full items according to the read_model,
        # extracting nested attributes from related models using the '__' separator.
            def trim_item(item, fields):
                trimmed = {}
                for field in fields:
                    if field.startswith('_'):
                        continue # ignore these fields
                    # If field uses '__', traverse the related objects.
                    if "__" in field:
                        parts = field.split("__")
                        value = item
                        # Recursively drill down each part. For example, for 'tool__name',
                        # get the 'tool' relationship, then its 'name' attribute.
                        for part in parts:
                            value = getattr(value, part, None)
                            if value is None:
                                break
                        trimmed[field] = value
                    else:
                        trimmed[field] = getattr(item, field, None)
                return trimmed

            items = [trim_item(item, read_model.__fields__) for item in items]

        # For full page load, return the complete template
        return templates.TemplateResponse(
            request=request,
            name="engineer/partials/list.html.j2",
            context={
                "items": items,
                "item_type": item_type,
                "has_more": has_more,
                "next_offset": offset + limit,
                "limit": limit,
                "offset": offset
            }
        )

    def get_filter_options(filter_model, session):
        filter_options = {}
        # Iterate over the field names defined in the filter_model (a pydantic-style model)
        for field_name in filter_model.model_fields.keys():
            try:
                # Get the corresponding column from the primary SQLModel 'model'
                column = inspect(model).columns[field_name]
            except Exception as e:
                print(f"Could not find column {field_name} in model. Relationship references are not allowed: {e}")
                continue
            if field_name.endswith('_id'):
                relation_name = field_name[:-3]
                related_model_info = model_mapping.get(relation_name.lower())
                if related_model_info:
                    related_model = related_model_info['model']
                    distinct_ids = session.query(func.distinct(getattr(model, field_name))).all()
                    id_list = [value[0] for value in distinct_ids if value[0] is not None]
                    if id_list:
                        related_items = session.query(related_model).filter(related_model.id.in_(id_list)).all()
                        filter_options[field_name] = sorted(
                            [{"id": getattr(item, "id"), "name": getattr(item, "name", None)} for item in related_items],
                            key=lambda x: str(x["name"]) if x["name"] is not None else ""
                        )
                continue
            elif isinstance(column.type, (sqltypes.String, sqltypes.Integer, sqltypes.Enum, sqltypes.JSON, sqltypes.DateTime, AutoString)):
                unique_values = session.query(func.distinct(getattr(model, field_name))).all()
                unique_values = [str(value[0]) for value in unique_values if value[0] is not None]
                filter_options[field_name] = sorted(unique_values)
            elif isinstance(column.type, sqltypes.Boolean):
                filter_options[field_name] = [True, False]
            else:
                print(f"Unhandled column type for {field_name}: {type(column.type)}")
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
        if fixed_field_callback:
            fixed_field_options = fixed_field_callback(item_id)
            for key, value in fixed_field_options.items():
                context['fixed_field_options'] = {}
                if key in context['relationship_options']:
                    del context['relationship_options'][key]
                context['fixed_field_options'][key] = value

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
        fixed_fields: Dict[str, Any] = {}

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
            elif field_name.startswith('fixed_'):
                parts = field_name.split('__')
                if not parts[1] in fixed_fields:
                    fixed_fields[parts[1]] = []
                fixed_fields[parts[1]].append({f'{parts[1].rstrip('s')}_id':parts[2], 'value': value})

        return form_dict, existing_relations, new_relations, fixed_fields
    

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

        # Convert datetime.time to datetime.datetime
        for key, value in item.__dict__.items():
            if not value:
                item.__dict__[key] = None
            if isinstance(value, time):
                item.__dict__[key] = datetime.combine(datetime.today(), value)
        
        with Session(engine) as session:
            session.add(item)
            try:
                session.commit()
                session.refresh(item)
            except Exception as e:
                # return JSONResponse(content={'message': f'{item_type} Database conflict: {str(e)}'}, status_code=status.HTTP_409_CONFLICT)
                raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(e))
            
            # Handle references to new related items
            for relation_name, new_items in references_dict.items():
                relation_list = getattr(item, relation_name)
                related_model_info = model_mapping.get(relation_name.replace("_","").rstrip('s').lower())
                if related_model_info:
                    seen_names = set()
                    related_create_model = related_model_info['create']
                    for new_item_data in new_items:
                        if new_item_data['name'] in seen_names:
                            continue
                        seen_names.add(new_item_data['name'])
                        new_item_data[f'{item_type.lower()}_id'] = item.id
                        # new_item_data['user_id'] = user.id
                        try:
                            validated_new_item = related_create_model(**new_item_data)
                            new_item = related_model_info['model'](**validated_new_item.model_dump())
                            relation_list.append(new_item)
                        except ValidationError as e:
                            raise HTTPException(status_code=422, detail=f"Validation error in {relation_name}: {str(e)}")

            try:
                session.commit()
                session.refresh(item)
            except Exception as e:
                raise HTTPException(status_code=500, detail=str(e))
        
        return JSONResponse(content={'message': f'{item_type} successfully created'}, status_code=201)

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
    async def update_item(item_id: int, request: Request, user: User = Depends(get_current_operator)):
        form_dict, existing_relations, new_relations, fixed_form_fields = await get_form_data(request)
        _, children = get_relations_and_children(item_id)
        for child_field in children.keys():
            if child_field not in existing_relations:
                existing_relations[child_field] = []

        if item_id != int(form_dict['id']):
            raise HTTPException(status_code=400, detail=f"Path {item_type.lower()}_id does not match form data id")
        
        with Session(engine) as session:
            item = session.exec(select(model).where(model.id == item_id)).one_or_none()
            if not item:
                raise HTTPException(status_code=404, detail=f"{item_type} not found")
            
            # Update main item fields
            try:
                # # Build a complete payload containing every field from the update model.
                # # If a field was not present in the form it will be explicitly set to None
                # # so that deletions from the UI are propagated to the database.
                # full_form: Dict[str, Any] = {}
                # for field_name in update_model.model_fields.keys():
                #     if field_name in form_dict:
                #         # use the value submitted in the form (checkbox handling was done in get_form_data)
                #         full_form[field_name] = form_dict[field_name]
                #     else:
                #         # field not present in the submitted form -> clear it 
                #         # MUST respect list, bool, str, int, float, datetime types
                #         field_info = update_model.model_fields[field_name]
                #         if get_origin(field_info.annotation) is list:
                #             full_form[field_name] = []
                #         elif field_info.annotation is bool:
                #             full_form[field_name] = False
                #         else:
                #             full_form[field_name] = None
                # # Validate the assembled payload so types/coercions are applied
                validated_data = update_model(**form_dict)

                # Apply all validated fields (except id) to the DB item.
                for key, value in validated_data.model_dump().items():
                    # if key != 'id':
                    if key in form_dict and key != 'id':
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
                    seen_names = set()
                    related_create_model = related_model_info['create']
                    for new_item_data in new_items:
                        if new_item_data['name'] in seen_names:
                            continue
                        seen_names.add(new_item_data['name'])
                        new_item_data[f'{item_type.lower()}_id'] = item_id
                        new_item_data['user_id'] = user.id
                        try:
                            validated_new_item = related_create_model(**new_item_data)
                            new_item = related_model_info['model'](**validated_new_item.model_dump())
                            relation_list.append(new_item)
                        except ValidationError as e:
                            raise HTTPException(status_code=422, detail=f"Validation error in {relation_name}: {str(e)}")

            if fixed_form_fields:
                for field_key, updates in fixed_form_fields.items():
                    fixed_field_list = getattr(item, field_key)
                    field_type = model.__annotations__.get(field_key)
                    model_class = None
                    if field_type:
                        origin = get_origin(field_type)
                        if origin is list:
                            inner = get_args(field_type)[0]
                        elif origin is not None and "Mapped" in str(origin):
                            inner = get_args(field_type)[0]
                        else:
                            continue
                        if get_origin(inner) is list:
                            model_inner = get_args(inner)[0]
                        else:
                            model_inner = inner
                        if isinstance(model_inner, ForwardRef):
                            model_class = globals().get(model_inner.__forward_arg__)
                        else:
                            model_class = model_inner
                    else:
                        continue
                    fixed_field_list.clear()
                    for update in updates:
                        new_instance = model_class(**update)
                        fixed_field_list.append(new_instance)

            try:
                # session.add(item)
                session.commit()
                session.refresh(item)
            except Exception as e:
                session.rollback()
                raise HTTPException(status_code=500, detail=f"An error occurred while updating the {item_type}: {str(e)}")

        return JSONResponse(content={"message": f"{item_type} updated successfully"}, status_code=202)

    return router
