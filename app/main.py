from fastapi import FastAPI, Request, Depends, status
from fastapi.responses import JSONResponse, Response, RedirectResponse
from fastapi.exceptions import HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from sqlmodel import Session, select
from app.templates.jinja_functions import templates
from app.database_config import init_db, get_session
from app.router import base
from app.router.engineer import _engineer
from app.router.operator import _operator
from app.router import device
from app.router import monitoring
from app.models import UserRole, ServiceMetrics
from auth import authenticate_or_create_device, authenticate_operator, require_role
from starlette.middleware.base import BaseHTTPMiddleware
from datetime import datetime

app = FastAPI()

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"]
)

# Custom middleware to bypass authentication for monitoring routes
class MonitoringBypassMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        if request.url.path.startswith("/monitoring"):
            return await call_next(request)
        return await call_next(request)

app.add_middleware(MonitoringBypassMiddleware)

# Setup static files
app.mount("/static", StaticFiles(directory="app/static"), name="static")

# Initialize database
init_db()

# Add monitoring middleware
@app.middleware("http")
async def monitoring_middleware(request: Request, call_next):
    if not request.url.path.startswith("/static"):  # Skip static files
        db = next(get_session())
        try:
            return await monitoring.log_request(request, call_next, db)
        finally:
            db.close()
    return await call_next(request)

# Store server start time
SERVER_START_TIME = datetime.now()

# Initialize service metrics on startup
@app.on_event("startup")
async def initialize_metrics():
    db = next(get_session())
    try:
        # Delete any existing metrics to ensure a fresh start
        statement = select(ServiceMetrics)
        existing_metrics = db.exec(statement).first()
        if existing_metrics:
            db.delete(existing_metrics)
            db.commit()
        
        # Create new metrics with server start time
        metrics = ServiceMetrics(
            start_time=SERVER_START_TIME,
            total_requests=0,
            total_errors=0,
            avg_response_time=0,
            last_updated=datetime.now()
        )
        db.add(metrics)
        db.commit()
    finally:
        db.close()

# Include monitoring router first without authentication
app.include_router(monitoring.router)

# Include the authenticated routers with path prefixes that don't conflict with monitoring
app.include_router(base.router, dependencies=[Depends(require_role(UserRole.OPERATOR))])
app.include_router(_engineer.router, prefix="/engineer", tags=["engineer"], dependencies=[Depends(require_role(UserRole.SUPERVISOR))])
app.include_router(_operator.router, prefix="/operator", tags=['operator'], dependencies=[Depends(require_role(UserRole.OPERATOR))])
app.include_router(device.router, prefix="/device", tags=["device-info"], dependencies=[Depends(require_role(UserRole.SUPERVISOR))])

# Public routes
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
async def authenticate_device(request: Request, db: Session = Depends(get_session)):
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

@app.get("/monitoring-dashboard")
async def monitoring_dashboard(request: Request):
    return templates.TemplateResponse("monitoring.html.j2", {"request": request})

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000, reload=True)
