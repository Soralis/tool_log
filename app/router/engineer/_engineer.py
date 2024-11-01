from fastapi import APIRouter, Request
from app.templates.jinja_functions import templates
from app.models import User, UserCreate, UserUpdate, UserRole
from app.models import Machine, MachineCreate, MachineUpdate
from app.models import Manufacturer, ManufacturerCreate, ManufacturerUpdate
from app.models import Tool, ToolCreate, ToolUpdate
from app.models import ToolAttribute, ToolAttributeCreate, ToolAttributeUpdate
from app.models import ToolSettings, ToolSettingsCreate, ToolSettingsUpdate
from app.models import ToolOrder, ToolOrderCreate, ToolOrderUpdate
# from app.models import Recipe, RecipeCreate, RecipeUpdate
from app.models import ToolLife, ToolLifeCreate, ToolLifeUpdate
from app.models import ToolType, ToolTypeCreate, ToolTypeUpdate
from app.models import ChangeReason, ChangeReasonCreate, ChangeReasonUpdate
from app.models import ChangeOver, ChangeOverCreate, ChangeOverUpdate
from app.models import Workpiece, WorkpieceCreate, WorkpieceUpdate
from .generic_router import create_generic_router
from .recipes import router as recipes_router

router = APIRouter()

# Create generic routers
users_router = create_generic_router(User, UserCreate, UserUpdate, "User", {"enum_fields": {"role": UserRole}})
machines_router = create_generic_router(Machine, MachineCreate, MachineUpdate, "Machine")
manufacturers_router = create_generic_router(Manufacturer, ManufacturerCreate, ManufacturerUpdate, "Manufacturer")
tools_router = create_generic_router(Tool, ToolCreate, ToolUpdate, "Tool")
tool_attributes_router = create_generic_router(ToolAttribute, ToolAttributeCreate, ToolAttributeUpdate, "Tool_Attribute")
tool_settings_router = create_generic_router(ToolSettings, ToolSettingsCreate, ToolSettingsUpdate, "Tool_Settings")
tool_type_router = create_generic_router(ToolType, ToolTypeCreate, ToolTypeUpdate, "Tool_Type")
tool_life_router = create_generic_router(ToolLife, ToolLifeCreate, ToolLifeUpdate, "Tool_Life")
change_reason_router = create_generic_router(ChangeReason, ChangeReasonCreate, ChangeReasonUpdate, "Change_Reason")
tool_orders_router = create_generic_router(ToolOrder, ToolOrderCreate, ToolOrderUpdate, "Tool_Order")
# recipe_router = create_generic_router(Recipe, RecipeCreate, RecipeUpdate, "Recipe")
change_over_router = create_generic_router(ChangeOver, ChangeOverCreate, ChangeOverUpdate, "Change_Over")
workpiece_router = create_generic_router(Workpiece, WorkpieceCreate, WorkpieceUpdate, "Workpiece")


# Include the generic routers
router.include_router(users_router, prefix="/users", tags=["users"])
router.include_router(machines_router, prefix="/machines", tags=["machines"])
router.include_router(manufacturers_router, prefix="/manufacturers", tags=["manufacturers"])
router.include_router(tools_router, prefix="/tools", tags=["tools"])
router.include_router(tool_attributes_router, prefix="/tool_attributes", tags=["tool_attributes"])
router.include_router(tool_settings_router, prefix="/tool_settings", tags=["tool_settings"])
router.include_router(change_reason_router, prefix="/change_reasons", tags=["change_reasons"])
router.include_router(tool_orders_router, prefix="/tool_orders", tags=["tool_orders"])
# router.include_router(recipe_router, prefix="/recipes", tags=["recipes"])
router.include_router(tool_life_router, prefix="/tool_lifes", tags=["tool_lifes"])
router.include_router(tool_type_router, prefix="/tool_types", tags=["tool_types"])
router.include_router(change_over_router, prefix="/change_overs", tags=["change_overs"])
router.include_router(workpiece_router, prefix="/workpieces", tags=["workpieces"])

router.include_router(recipes_router, prefix="/recipes", tags=["recipes"])


@router.get("/")
async def root(request: Request):
    return templates.TemplateResponse(
        request=request,
        name="engineer/index.html.j2",
        context= {
            'item_type': 'Device',
        }
    )



        