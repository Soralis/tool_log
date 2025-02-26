from fastapi import APIRouter, Depends, Form
from sqlmodel import Session, select
from datetime import datetime
from fastapi.responses import JSONResponse
from app.models import LogDevice, Heartbeat
from app.models import User, Shift
from app.database_config import get_session



router = APIRouter()


@router.get("/usersByShift")
async def users_by_shift(session: Session = Depends(get_session)):
    users = session.exec(select(User).where(User.active)).all()
    users_by_shift = {}
    active_shift = None
    now = datetime.now().time()

    shifts = session.exec(select(Shift).where(Shift.number < 4)).all()
    for shift in shifts:
        start_time = shift.start_time.time()
        end_time = shift.end_time.time()
        if start_time <= now <= end_time:
            active_shift = shift.number
            break

    for user in users:
        if user.shift.number > 3:
            continue
        if user.shift.number not in users_by_shift:
            users_by_shift[user.shift.number] = []
        users_by_shift[user.shift.number].append({"name": user.name, "initials": user.initials})

    for shift in users_by_shift:
        users_by_shift[shift] = sorted(users_by_shift[shift], key=lambda x: x["name"])

    return {"users_by_shift": users_by_shift, "active_shift": active_shift}

@router.post("/heartbeat_old")
async def heartbeat_old(device_token: str = Form(...), session: Session = Depends(get_session)):
    log_device: LogDevice = session.exec(select(LogDevice).filter(LogDevice.token == device_token)).one_or_none()
    if log_device is None:
        return JSONResponse(content={"error": "Log Device not found"}, status_code=404)

    # Create a new Heartbeat record
    heartbeat = Heartbeat(timestamp=datetime.now(), log_device_id=log_device.id)
    session.add(heartbeat)
    session.commit()

    return JSONResponse(content={"message": "Heartbeat recorded successfully"}, status_code=200)

@router.post("/heartbeat")
async def heartbeat(device_token: str, session: Session = Depends(get_session)):
    if not device_token:
        return JSONResponse(content={"error": "Log Device token not provided"}, status_code=400)
    log_device: LogDevice = session.exec(select(LogDevice).filter(LogDevice.token == device_token)).one_or_none()
    if log_device is None:
        return JSONResponse(content={"error": "Log Device not found"}, status_code=404)

    # Create a new Heartbeat record
    heartbeat = Heartbeat(timestamp=datetime.now(), log_device_id=log_device.id)
    session.add(heartbeat)
    session.commit()

    return JSONResponse(content={"message": "Heartbeat recorded successfully"}, status_code=200)
