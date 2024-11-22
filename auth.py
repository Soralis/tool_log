from fastapi import HTTPException, Depends, Cookie, Request, status
from fastapi.responses import JSONResponse
from sqlmodel import Session, select
from sqlalchemy.orm import selectinload
from jose import JWTError, jwt
from datetime import datetime, timedelta
from app.database_config import get_session, engine
from app.models import LogDevice
from app.models import User, UserRole
from dotenv import dotenv_values
import pytz

def get_utc_now():
    return datetime.now(pytz.UTC)

env = dotenv_values('.env')

def create_token(data: dict, expires_delta: timedelta):
    to_encode = data.copy()
    expire = get_utc_now() + expires_delta
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, env['SECRET_KEY'], algorithm=env['ALGORITHM'])
    return encoded_jwt, expire


async def get_current_device(device_token: str = Cookie(None)):
    with Session(engine) as session:
        if not device_token:
            raise HTTPException(status_code=401, detail="Device token missing")
        try:
            payload = jwt.decode(device_token, env['SECRET_KEY'], algorithms=[env['ALGORITHM']])
            device_name: str = payload.get("sub")
            if device_name is None:
                raise HTTPException(status_code=401, detail="Invalid device token")
            device = session.exec(select(LogDevice)
                                   .where(LogDevice.name == device_name)
                                   .options(selectinload(LogDevice.machines))).one_or_none()
            if device is None or device.token != device_token:
                raise HTTPException(status_code=401, detail="Device not found or token mismatch")
            return device
        except JWTError:
            raise HTTPException(status_code=401, detail="Invalid device token")


async def get_current_operator(request: Request):
    with Session(engine) as session:
        operator_token = request.cookies.get("operator_token")
        try:
            if not operator_token:
                raise HTTPException(
                    status_code=status.HTTP_307_TEMPORARY_REDIRECT,
                    headers={'Location': '/login'}
                )
            payload = jwt.decode(operator_token, env['SECRET_KEY'], algorithms=[env['ALGORITHM']])
            operator_cred: str = payload.get("sub")
            if operator_cred is None:
                raise HTTPException(
                    status_code=status.HTTP_307_TEMPORARY_REDIRECT,
                    headers={'Location': '/login'}
                )
            initials, pin = operator_cred.split(':')
            operator = session.exec(select(User).where(User.pin == pin).where(User.initials == initials)).one_or_none()
            if operator is None or operator.token != operator_token or operator.token_expiry < get_utc_now():
                raise HTTPException(
                    status_code=status.HTTP_307_TEMPORARY_REDIRECT,
                    headers={'Location': '/login'}
                )
            return operator
        except JWTError as e:
            raise HTTPException(
                status_code=status.HTTP_307_TEMPORARY_REDIRECT,
                headers={'Location': '/login'}
            )


def require_role(required_role: UserRole):
    async def check_role(request: Request, user: User = Depends(get_current_operator)):
        if user.role < required_role:
            raise HTTPException(status_code=401, detail="Forbidden: Insufficient permissions")
        return user
    return check_role


async def authenticate_or_create_device(device_name: str, db: Session = Depends(get_session)):
    log_device = db.exec(select(LogDevice).where(LogDevice.name == device_name)).one_or_none()
    if log_device is None:
        log_device = LogDevice(name=device_name)
        db.add(log_device)
        db.commit()
        db.refresh(log_device)

    access_token, expire = create_token(
        data={"sub": log_device.name},
        expires_delta=timedelta(days=int(env['DEVICE_TOKEN_EXPIRE_DAYS']))
    )

    log_device.token = access_token
    log_device.token_expiry = expire
    db.commit()

    response = JSONResponse(content={"message": "Device authenticated"})
    response.set_cookie(
        key="device_token",
        value=access_token,
        httponly=True,
        secure=False,  # Set to False if not using HTTPS
        samesite="lax",
        domain=None,  # Set to your domain if needed
        max_age=int(env['DEVICE_TOKEN_EXPIRE_DAYS']) * 24 * 60 * 60
    )
    return response


async def authenticate_operator(initials: str, pin: str):
    with Session(engine) as session:
        operator = session.exec(select(User).where(User.initials == initials, User.pin == pin)).one_or_none()
        if operator is None:
            # if initials == 'ck' and pin == '1234':
            #     operator = User(initials=initials, pin=pin, role=UserRole.ENGINEER, name='Christopher Kunde')
            #     session.add(operator)
            #     session.commit()
            #     session.refresh(operator)
            # else:
            raise HTTPException(status_code=401, detail="Invalid initials or PIN")

        access_token, expire = create_token(
            data={"sub": f'{operator.initials}:{operator.pin}'},
            expires_delta=timedelta(minutes=int(env['OPERATOR_TOKEN_EXPIRE_MINUTES']))
        )

        operator.token = access_token
        operator.token_expiry = expire
        session.commit()

        response = JSONResponse(content={"message": "Operator authenticated", "redirect": "/"})
        response.set_cookie(
            key="operator_token",
            value=access_token,
            httponly=True,
            secure=False,  # Set to False if not using HTTPS
            samesite="lax",
            domain=None,  # Set to your domain if needed
            max_age=int(env['OPERATOR_TOKEN_EXPIRE_MINUTES']) * 60
        )
        print((f"Setting operator_token cookie: {access_token}"))
        return response

