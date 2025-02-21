from fastapi import APIRouter, Depends, Request
from sqlmodel import Session, select
from datetime import time, datetime

from app.models import User, Shift
from app.database_config import get_session
from app.templates.jinja_functions import templates

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
