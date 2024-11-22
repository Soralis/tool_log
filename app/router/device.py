from fastapi import APIRouter, Request, Form
from fastapi.responses import JSONResponse
from app.models import LogDevice, LogDeviceSetMachine
from app.models import Machine, MachineBase
from sqlmodel import Session, select
from typing import Annotated, List
from app.templates.jinja_functions import templates
from app.database_config import engine

router = APIRouter()

@router.get("/getDeviceInfo")
async def root(request: Request):
    context = {
        'model': MachineBase,
        'item_type': "Log_Device",
        'form_action': '/device/setMachine',
        'relationship_options': {},
        'list_relationships': []
    }

    device_token = request.cookies.get("device_token")
    if not device_token:
        return templates.TemplateResponse(
            request=request,
            name="error.html.j2",
            context= {
                'error_title':"Device Name Missing",
                'error_heading':"Device Name Missing",
                'error_message':"The device name is missing in the request headers.",
                'error_details':request.headers
            }
        )

    statement = select(LogDevice).where(LogDevice.token == device_token)
    with Session(engine) as session:
        log_device = session.exec(statement).one_or_none()
        
        if not log_device and device_token:
            # Create a new LogDevice if it doesn't exist
            log_device = LogDevice(name=device_token, token=device_token)
            session.add(log_device)
            session.commit()
            session.refresh(log_device)

        # Fetch related items
        item_dict = log_device.model_dump()
        related_items = {}
        relationship_options = {}
        
        # Fetch machines relationship
        if log_device.machines:
            related_items['machines'] = [
                {"id": machine.id, "name": machine.name}
                for machine in log_device.machines
            ]
        
        # Fetch all possible machines for the relationship
        options_statement = select(Machine)
        options = session.exec(options_statement).all()
        relationship_options['machines'] = [{"id": opt.id, "name": opt.name} for opt in options]

        context = {
            "item": item_dict,
            "related_items": related_items,
            "relationship_options": relationship_options,
            "item_type": "log_device",
            "model": MachineBase,
            "form_action": '/device/setMachine',
            "submit_text": "Set Machine"
        }

        return templates.TemplateResponse(
            request=request,
            name="logdevice.html.j2",
            context=context
        )


@router.post("/setMachine")
async def set_machines(request: Request, machine_ids: List[int] = Form(None)):
    device_token = request.cookies.get("device_token")
    
    with Session(engine) as session:
        log_device: LogDevice = session.exec(select(LogDevice).filter(LogDevice.token == device_token)).one_or_none()
        if log_device is None:
            return JSONResponse(content={"error": "Log Device not found"}, status_code=404)
        
        if machine_ids:
            machines = session.exec(select(Machine).filter(Machine.id.in_(machine_ids))).all()
            if len(machines) != len(machine_ids):
                return JSONResponse(content={"error": "One or more machines not found"}, status_code=404)
        else:
            machines = []
        
        log_device.machines = machines
        session.add(log_device)
        session.commit()
        session.refresh(log_device)

    return JSONResponse(content={"message": "Machines connected successfully", "machine_count": len(machines)}, status_code=202)
    

@router.post("/disconnectMachine")
async def disconnect_machine(request: Request):
    device_name = request.headers.get("X-Device-ID")
    if not device_name:
        return {"message": "This Page can only be viewed on a named Log Device - but a name was not provided"}
    
    with Session(engine) as session:
        log_device: LogDevice = session.exec(select(LogDevice).filter(LogDevice.name == device_name)).one_or_none
        if log_device is None:
            return {"error": "Log Device not found or ambiguous"}
        log_device.machine_id = None
        await session.commit()
    
    return JSONResponse(content={"message": "Machine disconnected successfully"}, status_code=202)