from fastapi import APIRouter, Request, Form, HTTPException, status
from fastapi.responses import HTMLResponse, JSONResponse, Response
from sqlmodel import Session, select
from app.database_config import engine
from app.models.models import Manufacturer, ManufacturerUpdate, ManufacturerCreate
from app.templates.jinja_functions import templates
from typing import Annotated

router = APIRouter()


@router.get("/", response_class=HTMLResponse)
async def get_manufacturers(request: Request):
    return templates.TemplateResponse(
        request=request,
        name="engineer/data.html.j2",
        context={
            'model': ManufacturerCreate,
            'item_type': 'Manufacturer',
            'form_action': '/engineer/manufacturers',
        }
    )

@router.get("/list", response_class=HTMLResponse)
async def get_manufacturer_list(request: Request):
    statement = select(Manufacturer)
    with Session(engine) as session:
        manufacturers = session.exec(statement).all()
    return templates.TemplateResponse(
        request=request,
        name="engineer/partials/list.html.j2",
        context={"items": manufacturers, 'item_type': "Manufacturer"}
    )

@router.post("/")
def create_manufacturer(form_data: Annotated[ManufacturerCreate, Form()]):
    manufacturer = Manufacturer(**form_data.model_dump())
    with Session(engine) as session:
        session.add(manufacturer)
        try:
            session.commit()
            session.refresh(manufacturer)
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))
    return JSONResponse(content={'message':'manufacturer successfully created'}, status_code=201)

@router.delete("/{manufacturer_id}")
def delete_manufacturer(manufacturer_id: int):
    statement = select(Manufacturer).where(Manufacturer.id == manufacturer_id)
    with Session(engine) as session:
        manufacturer = session.exec(statement).one_or_none()
        if not manufacturer:
            raise HTTPException(status_code=404, detail="manufacturer not found")
        session.delete(manufacturer)
        session.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get("/{manufacturer_id}/edit", response_class=HTMLResponse)
async def get_manufacturer_for_edit(manufacturer_id: int, request: Request):
    statement = select(Manufacturer).where(Manufacturer.id == manufacturer_id)
    with Session(engine) as session:
        results = session.exec(statement)
        manufacturer = results.one_or_none()
    if not manufacturer:
        raise HTTPException(status_code=404, detail="manufacturer not found")
    return templates.TemplateResponse(
        request=request,
        name="engineer/partials/data_entry_modal.html.j2",
        context={
            'model': ManufacturerUpdate,
            'item': manufacturer,
            'item_type': "Manufacturer",
            'submit_text': 'Update',
            'form_action': '/engineer/manufacturers'
        }
    )

@router.put("/{manufacturer_id}")
def update_manufacturer(manufacturer_id: int, form_data: Annotated[ManufacturerUpdate, Form()]):
    if manufacturer_id != form_data.id:
        raise HTTPException(status_code=400, detail="Path manufacturer_id does not match form data id")
    
    statement = select(Manufacturer).where(Manufacturer.id == manufacturer_id)
    with Session(engine) as session:
        results = session.exec(statement)
        manufacturer = results.one_or_none()
        if not manufacturer:
            raise HTTPException(status_code=404, detail="Manufacturer not found")

        manufacturer_data = form_data.model_dump(exclude_unset=True)
        for key, value in manufacturer_data.items():
            setattr(manufacturer, key, value)

        try:
            session.add(manufacturer)
            session.commit()
            session.refresh(manufacturer)
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))

    return JSONResponse(content={"message": "Manufacturer updated successfully"}, status_code=202)
