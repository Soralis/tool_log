from fastapi import APIRouter, Request
from app.templates.jinja_functions import templates
from app.models.models import User, UserCreate, UserUpdate, UserRole
from app.models.models import Machine, MachineCreate, MachineUpdate
from app.models.models import Manufacturer, ManufacturerCreate, ManufacturerUpdate
from app.models.models import Tool, ToolCreate, ToolUpdate, ToolType
from app.models.models import ToolOrder, ToolOrderCreate, ToolOrderUpdate
from app.models.models import Recipe, RecipeCreate, RecipeUpdate
from app.models.models import ToolLife, ToolLifeCreate, ChangeReasons
from app.models.models import ChangeOver, ChangeOverCreate
from .generic_router import create_generic_router

router = APIRouter()

# Create generic routers
users_router = create_generic_router(User, UserCreate, UserUpdate, "User", {"enum_fields": {"role": UserRole}})
machines_router = create_generic_router(Machine, MachineCreate, MachineUpdate, "Machine")
manufacturers_router = create_generic_router(Manufacturer, ManufacturerCreate, ManufacturerUpdate, "Manufacturer")
tools_router = create_generic_router(Tool, ToolCreate, ToolUpdate, "Tool", {"enum_fields": {"tool_type": ToolType}})
tool_orders_router = create_generic_router(ToolOrder, ToolOrderCreate, ToolOrderUpdate, "Tool_Order")
recipe_router = create_generic_router(Recipe, RecipeCreate, RecipeUpdate, "Recipe")
tool_life_router = create_generic_router(ToolLife, ToolLifeCreate, None, "Tool_Life", {"enum_fields": {"reason": ChangeReasons}})
change_over_router = create_generic_router(ChangeOver, ChangeOverCreate, None, "Change_Over")


# Include the generic routers
router.include_router(users_router, prefix="/users", tags=["users"])
router.include_router(machines_router, prefix="/machines", tags=["machines"])
router.include_router(manufacturers_router, prefix="/manufacturers", tags=["manufacturers"])
router.include_router(tools_router, prefix="/tools", tags=["tools"])
router.include_router(tool_orders_router, prefix="/tool_orders", tags=["tool_orders"])
router.include_router(recipe_router, prefix="/recipes", tags=["recipes"])
router.include_router(tool_life_router, prefix="/tool_lifes", tags=["tool_lifes"])
router.include_router(change_over_router, prefix="/change_overs", tags=["change_overs"])


@router.get("/")
async def root(request: Request):
    device_name = request.headers.get("x-device-name", None)
    return templates.TemplateResponse(
        request=request,
        name="engineer/index.html.j2",
        context= {
            'item_type': 'Device',
        },
        device_name=device_name
    )



        