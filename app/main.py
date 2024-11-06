from fastapi import FastAPI, Request, Depends
from app.models import LogDevice, Machine
from sqlmodel import Session, select
from app.templates.jinja_functions import templates
from auth import get_current_device
from fastapi.staticfiles import StaticFiles
from fastapi.responses import JSONResponse
from fastapi.exceptions import HTTPException
from app.models.all_models import User, UserRole
from fastapi.middleware.cors import CORSMiddleware
from app.database_config import init_db, get_db, get_session
from app.router.engineer import _engineer
from app.router.operator import _operator
from app.router import device
from auth import authenticate_or_create_device, authenticate_operator, get_current_operator, require_role

app = FastAPI()

# Add this right after creating the FastAPI app instance
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allows all origins
    allow_credentials=True,
    allow_methods=["*"],  # Allows all methods
    allow_headers=["*"],  # Allows all headers
)

# Setup static files
app.mount("/static", StaticFiles(directory="app/static"), name="static")

# Initialize database
init_db()

# Include the routers
app.include_router(_engineer.router, prefix="/engineer", tags=["engineer"], dependencies=[Depends(require_role(UserRole.ENGINEER))])
app.include_router(_operator.router, prefix="/operator", tags=['operator'])
app.include_router(device.router, prefix="/device", tags=["device-info"], dependencies=[Depends(require_role(UserRole.SUPERVISOR))])


@app.get("/")
async def root(request: Request, device: LogDevice = Depends(get_current_device), session: Session = Depends(get_session)):
    machines = session.exec(select(Machine).where((Machine.log_device_id == device.id), Machine.active)).all()
    return templates.TemplateResponse(
            request=request,
            name="index.html.j2",
            context={'machines': machines}
        )


@app.get("/login")
async def login_page(request: Request):
    return templates.TemplateResponse("operator_login.html.j2", {"request": request})


@app.post("/authenticateDevice")
async def authenticate_device(request: Request, db: Session = Depends(get_db)):
    body = await request.json()
    device_name = body.get("device_name")
    if not device_name:
        raise HTTPException(status_code=400, detail="Device name is required")
    try:
        return await authenticate_or_create_device(device_name, db)
    except Exception as e:
        return JSONResponse(content={"error": str(e.detail)}, status_code=e.status_code)


@app.post("/authenticateOperator")
async def authenticate_operator_route(request: Request):
    form_data = await request.form()
    initials = form_data.get("initials")
    pin = form_data.get("pin")
    if not initials or not pin:
        raise HTTPException(status_code=400, detail="Initials and PIN are required")
    try:
        return await authenticate_operator(initials, pin)
    except HTTPException as e:
        return JSONResponse(content={"error": str(e.detail)}, status_code=e.status_code)


@app.get("/checkOperatorAuth")
async def check_operator_auth(request: Request, operator: User = Depends(get_current_operator)):  
    return {"message": f"Hello, operator {operator.initials}"}  


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000, reload=True)
