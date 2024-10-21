from fastapi import APIRouter, Request, Form, HTTPException, status
from fastapi.responses import HTMLResponse, JSONResponse, Response
from sqlmodel import Session, select
from app.database_config import engine
from app.models.models import Tool, ToolCreate, ToolUpdate, ToolType, Manufacturer
from app.templates.jinja_functions import templates
from typing import Annotated

router = APIRouter()


@router.get("/", response_class=HTMLResponse)
async def get_tools(request: Request):
    with Session(engine) as session:
        manufacturers = session.exec(select(Manufacturer)).all()
    return templates.TemplateResponse(
        request=request,
        name="engineer/data.html.j2",
        context={
            'model': ToolCreate,
            'item_type': 'Tool',
            'form_action': '/engineer/tools',
            'enum_fields': {'tool_type': ToolType},
            'manufacturers': manufacturers,
            'relationship_fields': {
                'manufacturer_id': {
                    'options': manufacturers,
                    'option_value': 'id',
                    'option_text': 'name'
                }
            }
        }
    )

@router.get("/list", response_class=HTMLResponse)
async def get_tool_list(request: Request):
    statement = select(Tool)
    with Session(engine) as session:
        tools = session.exec(statement).all()
    return templates.TemplateResponse(
        request=request,
        name="engineer/partials/list.html.j2",
        context={"items": tools, 'item_type': 'Tool'}
    )

@router.post("/")
def create_tool(form_data: Annotated[ToolCreate, Form()]):
    tool = Tool(**form_data.model_dump())
    with Session(engine) as session:
        session.add(tool)
        try:
            session.commit()
            session.refresh(tool)
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))
    return JSONResponse(content={'message':'tool successfully created'}, status_code=201)

@router.delete("/{tool_id}")
def delete_tool(tool_id: int):
    statement = select(Tool).where(Tool.id == tool_id)
    with Session(engine) as session:
        tool = session.exec(statement).one_or_none()
        if not tool:
            raise HTTPException(status_code=404, detail="tool not found")
        session.delete(tool)
        session.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get("/{tool_id}/edit", response_class=HTMLResponse)
async def get_tool_for_edit(tool_id: int, request: Request):
    statement = select(Tool).where(Tool.id == tool_id)
    with Session(engine) as session:
        results = session.exec(statement)
        manufacturers = session.exec(select(Manufacturer)).all()
        tool = results.one_or_none()
    if not tool:
        raise HTTPException(status_code=404, detail="tool not found")
    return templates.TemplateResponse(
        request=request,
        name="engineer/partials/data_entry_modal.html.j2",
        context={
            'model': ToolUpdate,
            'item': tool,
            'item_type': 'Tool',
            'submit_text': 'Update',
            'form_action': '/engineer/tools',
            'enum_fields': {'tool_type': ToolType},
            'manufacturers': manufacturers,
            'relationship_fields': {
                'manufacturer_id': {
                    'options': manufacturers,
                    'option_value': 'id',
                    'option_text': 'name'
                }
            }
        }
    )

@router.put("/{tool_id}")
def update_tool(tool_id: int, form_data: Annotated[ToolUpdate, Form()]):
    if tool_id != form_data.id:
        raise HTTPException(status_code=400, detail="Path tool_id does not match form data id")
    
    statement = select(Tool).where(Tool.id == tool_id)
    with Session(engine) as session:
        results = session.exec(statement)
        tool = results.one_or_none()
        if not tool:
            raise HTTPException(status_code=404, detail="Tool not found")

        tool_data = form_data.model_dump(exclude_unset=True)
        for key, value in tool_data.items():
            setattr(tool, key, value)

        try:
            session.add(tool)
            session.commit()
            session.refresh(tool)
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))

    return JSONResponse(content={"message": "Tool updated successfully"}, status_code=202)
