from fastapi import APIRouter, Request, Form, HTTPException, status
from fastapi.responses import HTMLResponse, JSONResponse, Response
from sqlmodel import Session, select
from app.database_config import engine
from app.models.models import User, UserCreate, UserUpdate, UserRole
from app.templates.jinja_functions import templates
from typing import Annotated

router = APIRouter()


@router.get("/", response_class=HTMLResponse)
async def get_users(request: Request):
    return templates.TemplateResponse(
        request=request,
        name="engineer/data.html.j2",
        context={
            'model': UserCreate,
            'item_type': 'User',
            'form_action': '/engineer/users',
            'enum_fields': {'role': UserRole}
        }
    )

@router.get("/list", response_class=HTMLResponse)
async def get_user_list(request: Request):
    statement = select(User)
    with Session(engine) as session:
        users = session.exec(statement).all()
    return templates.TemplateResponse(
        request=request,
        name="engineer/partials/list.html.j2",
        context={"items": users, 'item_type': "user"}
    )

@router.post("/")
def create_user(form_data: Annotated[UserCreate, Form()]):
    user = User(**form_data.model_dump())
    with Session(engine) as session:
        session.add(user)
        try:
            session.commit()
            session.refresh(user)
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))
    return JSONResponse(content={'message':'User successfully created'}, status_code=201)

@router.delete("/{user_id}")
def delete_user(user_id: int):
    statement = select(User).where(User.id == user_id)
    with Session(engine) as session:
        user = session.exec(statement).one_or_none()
        if not user:
            raise HTTPException(status_code=404, detail="User not found")
        session.delete(user)
        session.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get("/{user_id}/edit", response_class=HTMLResponse)
async def get_user_for_edit(user_id: int, request: Request):
    statement = select(User).where(User.id == user_id)
    with Session(engine) as session:
        results = session.exec(statement)
        user = results.one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return templates.TemplateResponse(
        request=request,
        name="engineer/partials/data_entry_modal.html.j2",
        context={
            'model': UserUpdate,
            'enum_fields': {'role': UserRole},
            'item': user,
            'item_type': "user",
            'submit_text': 'Update',
            'form_action': '/engineer/users'
        }
    )

@router.put("/{user_id}")
def update_user(user_id: int, form_data: Annotated[UserUpdate, Form()]):
    if user_id != form_data.id:
        raise HTTPException(status_code=400, detail="Path user_id does not match form data id")
    
    statement = select(User).where(User.id == user_id)
    with Session(engine) as session:
        results = session.exec(statement)
        user = results.one_or_none()
        if not user:
            raise HTTPException(status_code=404, detail="User not found")

        user_data = form_data.model_dump(exclude_unset=True)
        for key, value in user_data.items():
            setattr(user, key, value)

        try:
            session.add(user)
            session.commit()
            session.refresh(user)
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))

    return JSONResponse(content={"message": "User updated successfully"}, status_code=202)
