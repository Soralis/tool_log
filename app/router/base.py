from fastapi import APIRouter, Request, Depends
from app.models import LogDevice, Machine
from sqlmodel import Session, select
from sqlalchemy.orm import joinedload
from auth import get_current_device

from app.templates.jinja_functions import templates
from app.models import User
from app.database_config import get_session
from auth import get_current_operator


router = APIRouter()

@router.get("/")
async def root(request: Request, 
               user: User = Depends(get_current_operator),
               device: LogDevice = Depends(get_current_device), 
               session: Session = Depends(get_session)):
    machines = session.exec(select(Machine).where((Machine.log_device_id == device.id), Machine.active)
                            .options(joinedload(Machine.current_recipe))).all()
    return templates.TemplateResponse(
            request=request,
            name="index.html.j2",
            context={'machines': machines,
                     'user': user}
        )


@router.get("/checkOperatorAuth")
async def check_operator_auth(request: Request, operator: User = Depends(get_current_operator)):  
    return {"message": f"Hello, operator {operator.initials}"}