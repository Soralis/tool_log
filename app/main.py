from fastapi import FastAPI, Request, Depends, status
from fastapi.responses import JSONResponse, Response, RedirectResponse
from fastapi.exceptions import HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from sqlmodel import Session
from app.templates.jinja_functions import templates
from app.database_config import init_db, get_db
from app.router import base
from app.router.engineer import _engineer
from app.router.operator import _operator
from app.router import device
from app.models.all_models import UserRole
from auth import authenticate_or_create_device, authenticate_operator, require_role

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
app.include_router(base.router, dependencies=[Depends(require_role(UserRole.OPERATOR))])
app.include_router(_engineer.router, prefix="/engineer", tags=["engineer"], dependencies=[Depends(require_role(UserRole.ENGINEER))])
app.include_router(_operator.rrouter, prefix="/operator", tags=['operator'], dependencies=[Depends(require_role(UserRole.OPERATOR))])
app.include_router(device.router, prefix="/device", tags=["device-info"], dependencies=[Depends(require_role(UserRole.SUPERVISOR))])


@app.get("/health")
async def health():
    return {"status": "healthy"}


@app.get('/deviceRegistration')
async def register_log_device(request: Request):
    return templates.TemplateResponse("device_registration.html.j2", {"request": request})


@app.get("/login")
async def login_page(request: Request):
    return templates.TemplateResponse("operator_login.html.j2", {"request": request})  

@app.get("/logout")
async def logout(request: Request, response: Response):
    response = RedirectResponse(url='/login', status_code=status.HTTP_307_TEMPORARY_REDIRECT)
    response.delete_cookie("operator_token")
    return response


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


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000, reload=True)
