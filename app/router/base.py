from fastapi import APIRouter, Request, Depends, status
from fastapi.responses import JSONResponse
from psycopg.errors import UniqueViolation, IntegrityError
from app.models import LogDevice, Machine
from sqlmodel import Session, select
from sqlalchemy.orm import joinedload
from datetime import datetime
from auth import get_current_device

from app.templates.jinja_functions import templates
from app.models import User, Shift
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


@router.patch('/changePin/{user_id}')
async def change_pin(request: Request, 
                     user_id: int,
                     operator: User = Depends(get_current_operator),
                     session: Session = Depends(get_session)):
    if user_id != operator.id:
        return {"message": "You are not authorized to change this PIN"}
    form = await request.form()
    new_pin = form["new_pin"]
    operator.pin = new_pin
    session.add(operator)
    session.commit()
    session.refresh(operator)
    return {"message": "PIN changed successfully"}

@router.post('/createOperator')
async def create_operator(request: Request, 
                          session: Session = Depends(get_session)):
    form = await request.form()
    current_time = datetime.now()
    current_shift = session.exec(select(Shift).where(Shift.start_time <= current_time.time(), Shift.end_time >= current_time.time())).one_or_none()
    try:
        new_operator = User(name=form["name"], 
                            initials=form["initials"], 
                            pin=form["pin"], 
                            payment_type=1,
                            role=1,
                            shift_id=current_shift.id if current_shift else None,
                            )
        session.add(new_operator)
        session.commit()
        session.refresh(new_operator)

        return JSONResponse(
            content={"message": f"Operator {new_operator.name} created successfully"},
            status_code=status.HTTP_201_CREATED
        )
    except IntegrityError as e:
        session.rollback()
        if isinstance(e.orig, UniqueViolation):
            return JSONResponse(
                content={"message": "Operator with these initials already exists"},
                status_code=status.HTTP_409_CONFLICT
            )
        else:
            return JSONResponse(
                content={"message": e.args},
                status_code=status.HTTP_409_CONFLICT
            )
    except Exception as e:
        return JSONResponse(
            content={"message": f"Error creating operator: {str(e)}"},
            status_code=status.HTTP_400_BAD_REQUEST
        )
