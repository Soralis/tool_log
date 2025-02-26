from fastapi import APIRouter, Depends, Form, Request
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

# @router.post("/heartbeat_old")
# async def heartbeat_old(device_token: str = Form(...), session: Session = Depends(get_session)):
#     log_device: LogDevice = session.exec(select(LogDevice).filter(LogDevice.token == device_token)).one_or_none()
#     if log_device is None:
#         return JSONResponse(content={"error": "Log Device not found"}, status_code=404)

#     # Create a new Heartbeat record
#     heartbeat = Heartbeat(timestamp=datetime.now(), log_device_id=log_device.id)
#     session.add(heartbeat)
#     session.commit()

#     return JSONResponse(content={"message": "Heartbeat recorded successfully"}, status_code=200)

@router.post("/heartbeat")
async def heartbeat(request: Request, session: Session = Depends(get_session)):
    try:
        # Try to get data from JSON body first
        data = await request.json()
        device_token = data.get("device_token")
    except:
        # Fall back to form data if JSON parsing fails
        form = await request.form()
        device_token = form.get("device_token")
        if not device_token:
            # Last resort: try query parameters
            device_token = request.query_params.get("device_token")
    
    if not device_token:
        return JSONResponse(content={"error": "Log Device token not provided"}, status_code=400)
    
    # Try to find device by token first
    log_device = session.exec(select(LogDevice).filter(LogDevice.token == device_token)).one_or_none()
    
    # If not found, try to find by name (MAC address)
    if log_device is None:
        log_device = session.exec(select(LogDevice).filter(LogDevice.name == device_token)).one_or_none()
    
    # If still not found, return error
    if log_device is None:
        return JSONResponse(content={"error": "Log Device not found"}, status_code=404)

    # Get client IP address
    client_ip = request.client.host if hasattr(request, 'client') else None
    
    # Update the log device's IP address if it has changed
    if client_ip and log_device.ip_address != client_ip:
        log_device.ip_address = client_ip
        session.add(log_device)
    
    # Create a new Heartbeat record
    logged_heartbeat = Heartbeat(timestamp=datetime.now(), log_device_id=log_device.id)
    session.add(logged_heartbeat)
    session.commit()

    return JSONResponse(content={"message": "Heartbeat recorded successfully", "success": True}, status_code=200)
