from fastapi import FastAPI, Request
from fastapi.staticfiles import StaticFiles
from app.templates.jinja_functions import templates
from app.database_config import init_db
from app.router.engineer import _engineer

app = FastAPI()

# Setup static files
app.mount("/static", StaticFiles(directory="app/static"), name="static")

# Initialize database
init_db()

# Include the routers
app.include_router(_engineer.router, prefix="/engineer", tags=["engieer"])


@app.get("/")
async def root(request: Request):
    return templates.TemplateResponse(
        request=request, name="index.html")
