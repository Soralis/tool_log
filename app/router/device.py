from fastapi import APIRouter, Request, Form
from fastapi.responses import JSONResponse
from fastapi.exceptions import HTTPException
from app.models import LogDevice, LogDeviceSetMachine
from app.models import Machine
from sqlmodel import Session, select
from typing import Annotated
from app.templates.jinja_functions import templates
from app.database_config import engine

router = APIRouter()

@router.get("/getDeviceInfo")
async def root(request: Request):
    context = {
        'model': LogDeviceSetMachine,
        'item_type': "Log_Device",
        'form_action': '/engineer/setMachine',
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
            # log_device = LogDevice(name=device_token)
            # session.add(log_device)
            # await session.commit()
            # await session.refresh(log_device)
            raise HTTPException(status_code=404, detail="Device not found")

        # Fetch related items
        item_dict = log_device.model_dump()
        related_items = {}
        relationship_options = {}
        
        # Dynamically fetch all relationships
        for relation in log_device.__class__.__mapper__.relationships.keys():
            related_objects = getattr(log_device, relation)
            if related_objects is not None:
                # It's a singular item
                related_items[relation] = {
                    "id": related_objects.id, 
                    "name": getattr(related_objects, 'name', str(related_objects))
                }
                
                # Fetch all possible options for this relationship
                related_model = log_device.__class__.__mapper__.relationships[relation].mapper.class_
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
            "item_type": "log_device",
            "model": LogDeviceSetMachine,
            "form_action": '/device/setMachine',
            "submit_text": "Set Machine"
        }
        
        # Add this debug print
        print(f"Context: {context}")

        return templates.TemplateResponse(
            request=request,
            name="engineer/partials/info_modal.html.j2",
            context=context
        )


@router.post("/setMachine")
async def set_machine(request: Request, form_data: Annotated[LogDeviceSetMachine, Form()]):
    device_name = request.headers.get("X-Device-ID")
    with Session(engine) as session:
        machine: Machine = session.exec(select(Machine).filter(Machine.id == form_data.machine_id)).one_or_none()
        if machine is None:
            return {"error": "Machine not found or ambiguous"}
        
        log_device: LogDevice = session.exec(select(LogDevice).filter(LogDevice.name == device_name)).one_or_none()
        if log_device is None:
            return {"error": "Machine not found or ambiguous"}
            
        log_device.machine_id = form_data.machine_id
        await session.commit()

    return JSONResponse(content={"message": "Machine connected successfully"}, status_code=202)
    

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
    
    return JSONResponse(content={"message": "Machine dicconnected successfully"}, status_code=202)