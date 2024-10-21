from fastapi import APIRouter, Request, Form, HTTPException, status
from fastapi.responses import HTMLResponse, JSONResponse, Response
from sqlmodel import Session, select
from app.database_config import engine
from app.models.models import Machine, MachineCreate, MachineUpdate
from app.templates.jinja_functions import templates
from typing import Annotated

router = APIRouter()


@router.get("/", response_class=HTMLResponse)
async def get_machines(request: Request):
    return templates.TemplateResponse(
        request=request,
        name="engineer/data.html.j2",
        context={
            'model': MachineCreate,
            'item_type': 'Machine',
            'form_action': '/engineer/machines'
        }
    )

@router.get("/list", response_class=HTMLResponse)
async def get_machine_list(request: Request):
    statement = select(Machine)
    with Session(engine) as session:
        results = session.exec(statement)
        machines = results.all()
    return templates.TemplateResponse(
        request=request,
        name="engineer/partials/list.html.j2",
        context={"items": machines, 'item_type': "machine"}
    )

@router.post("/")
async def create_machine(form_data: Annotated[MachineCreate, Form()], request: Request):
    # Convert list fields from form data
    request_form_data = await request.form()
    position_list = []
    position_name = 'positions'
    for field, value in request_form_data._list:
        if field.endswith('[]'):
            position_list.append(value)

    setattr(form_data, position_name, position_list)
    
    machine = Machine(**form_data.model_dump())
    
    with Session(engine) as session:
        session.add(machine)
        try:
            session.commit()
            session.refresh(machine)
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))
    return JSONResponse(content={'message':'Machine successfully created'}, status_code=201)

@router.delete("/{machine_id}")
def delete_machine(machine_id: int):
    statement = select(Machine).where(Machine.id == machine_id)
    with Session(engine) as session:
        results = session.exec(statement)
        machine = results.one_or_none()
        if not machine:
            raise HTTPException(status_code=404, detail="Machine not found")
        session.delete(machine)
        session.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get("/{machine_id}/edit", response_class=HTMLResponse)
async def get_machine_for_edit(machine_id: int, request: Request):
    statement = select(Machine).where(Machine.id == machine_id)
    with Session(engine) as session:
        results = session.exec(statement)
        machine = results.one_or_none()
    if not machine:
        raise HTTPException(status_code=404, detail="Machine not found")
    return templates.TemplateResponse(
        request=request,
        name="engineer/partials/data_entry_modal.html.j2",
        context={
            'model': MachineUpdate,
            'item': machine,
            'item_type': "machine",
            'submit_text': 'Update',
            'form_action': '/engineer/machines'
        }
    )

@router.put("/{machine_id}")
async def update_machine(machine_id: int, form_data: Annotated[MachineUpdate, Form()], request:Request):
    if machine_id != form_data.id:
        raise HTTPException(status_code=400, detail="Path machine_id does not match form data id")
    
    request_form_data = await request.form()
    position_list = []
    position_name = 'positions'
    for field, value in request_form_data._list:
        if field.endswith('[]'):
            position_list.append(value)

    setattr(form_data, position_name, position_list)

    machine_data = form_data.model_dump(exclude_unset=True)

    statement = select(Machine).where(Machine.id == machine_id)
    with Session(engine) as session:
        results = session.exec(statement)
        machine = results.one_or_none()
        if not machine:
            raise HTTPException(status_code=404, detail="Machine not found")
        
        for key, value in machine_data.items():
            setattr(machine, key, value)

        try:
            session.add(machine)
            session.commit()
            session.refresh(machine)
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))

    return JSONResponse(content={"message": "Machine updated successfully"}, status_code=202)
