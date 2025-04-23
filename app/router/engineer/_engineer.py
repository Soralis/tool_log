from fastapi import APIRouter, Request
from app.templates.jinja_functions import templates
from app.models import User, UserCreate, UserUpdate, UserRead, UserRole, PaymentType
from app.models import Shift, ShiftCreate, ShiftUpdate, ShiftRead, ShiftFilter
from app.models import Machine, MachineCreate, MachineUpdate, MachineRead, MachineFilter
from app.models import Line, LineCreate, LineUpdate, LineRead, LineFilter
from app.models import Manufacturer, ManufacturerCreate, ManufacturerUpdate, ManufacturerRead, ManufacturerFilter
from app.models import Tool, ToolCreate, ToolUpdate, ToolRead, ToolFilter
from app.models import ToolAttribute, ToolAttributeCreate, ToolAttributeUpdate, ToolAttributeRead
from app.models import ToolOrder, ToolOrderCreate, ToolOrderUpdate, ToolOrderRead, ToolOrderFilter
from app.models import Measureable, MeasureableCreate, MeasureableUpdate, MeasureableRead
from app.models import ToolLife, ToolLifeCreate, ToolLifeUpdate, ToolLifeRead, ToolLifeFilter
from app.models import Note, NoteCreate, NoteUpdate, NoteRead
from app.models import ToolType, ToolTypeCreate, ToolTypeUpdate, ToolTypeRead, Sentiment
from app.models import ChangeReason, ChangeReasonCreate, ChangeReasonUpdate, ChangeReasonRead, ChangeReasonFilter
from app.models import ChangeOver, ChangeOverCreate, ChangeOverUpdate, ChangeOverRead, ChangeOverFilter
from app.models import Workpiece, WorkpieceCreate, WorkpieceUpdate, WorkpieceRead, WorkpieceFilter
from .generic_router import create_generic_router
from .recipes import router as recipes_router
from sqlmodel import Session
from app.database_config import engine

# Generic fixed field callback - generic function to retrieve fixed fields based on a related fixed item.
def fixed_field_callback(mapping: dict, calling_model, extra: dict = None):
    """
    A generic callback factory to supply fixed field options.
    The mapping must be of the form:
        {
            fixed_field_name: { calling_model_field: (FixedModel, fixed_field_relation) }
        }
    When a model-X (of type calling_model) has a fixed field (e.g. "tool_attributes"),
    this callback uses the model-X’s trigger field (e.g. tool_type_id) to look up model-Y (e.g. ToolType)
    and retrieves the fixed options from model-Y's attribute (e.g. "tool_attributes").
    The returned callback function expects an optional model_id parameter. If omitted,
    it will attempt to use extra["id"].
    If only one fixed field is defined in the mapping, the callback returns the list of options directly;
    otherwise, it returns a dict mapping each fixed field to its options.
    """
    def callback(model_id=None):
        if model_id is None:
            if extra and "id" in extra:
                model_id = extra["id"]
            else:
                return {}
        options = {}
        with Session(engine) as session:
            instance = session.get(calling_model, model_id)
            if not instance:
                return {}
            for fixed_field, trigger_mapping in mapping.items():
                for trigger_field, (FixedModel, fixed_relation) in trigger_mapping.items():
                    if not hasattr(instance, trigger_field):
                        continue
                    fixed_id = getattr(instance, trigger_field)
                    fixed_item = session.get(FixedModel, fixed_id)
                    if fixed_item and hasattr(fixed_item, fixed_relation):
                        fixed_fields = []
                        for attr in getattr(fixed_item, fixed_relation):
                            
                            fixed_fields.append({
                                "name": attr.name,
                                "unit": attr.unit,
                                "field_id": attr.id,
                                "value": next((sf.value for sf in getattr(instance, fixed_field) if getattr(sf, f"{fixed_field.rstrip('s')}_id") == attr.id), None),
                                "required": True
                            })
                        options[fixed_field] = fixed_fields
        return options
    return callback

router = APIRouter()

# Define a generic extra context for fixed fields.
# In a real scenario, the tool_type_id might be provided from the frontend or configuration.
generic_extra_context = {"tool_type_id": 1}  # Placeholder; adjust as needed.

# Create generic routers
users_router = create_generic_router(User, UserRead, UserCreate, UserUpdate, UserRead, "User", {"enum_fields": {"role": UserRole, "payment_type": PaymentType}})
shift_router = create_generic_router(Shift, ShiftRead, ShiftCreate, ShiftUpdate, ShiftFilter, "Shift")
machines_router = create_generic_router(Machine, MachineRead, MachineCreate, MachineUpdate, MachineFilter, "Machine")
lines_router = create_generic_router(Line, LineRead, LineCreate, LineUpdate, LineFilter, "Line")
manufacturers_router = create_generic_router(Manufacturer, ManufacturerRead, ManufacturerCreate, ManufacturerUpdate, ManufacturerFilter, "Manufacturer")
tool_fixed_mapping = {
    "tool_attributes": {"tool_type_id": (ToolType, "tool_attributes")}
}
tools_router = create_generic_router(Tool, ToolRead, ToolCreate, ToolUpdate, ToolFilter, "Tool", fixed_field_callback=fixed_field_callback(tool_fixed_mapping, Tool))
tool_attributes_router = create_generic_router(ToolAttribute, ToolAttributeRead, ToolAttributeCreate, ToolAttributeUpdate, ToolAttributeRead, "Tool_Attribute")
tool_type_router = create_generic_router(ToolType, ToolTypeRead, ToolTypeCreate, ToolTypeUpdate, ToolTypeRead, "Tool_Type", {"enum_fields": {"sentiment": Sentiment}})
tool_life_router = create_generic_router(ToolLife, ToolLifeRead, ToolLifeCreate, ToolLifeUpdate, ToolLifeFilter, "Tool_Life", {"enum_fields": {"sentiment": Sentiment}})
note_router = create_generic_router(Note, NoteRead, NoteCreate, NoteUpdate, NoteRead, "Note")
measureable_router = create_generic_router(Measureable, MeasureableRead, MeasureableCreate, MeasureableUpdate, MeasureableRead, "Measureable")
change_reason_router = create_generic_router(ChangeReason, ChangeReasonRead, ChangeReasonCreate, ChangeReasonUpdate, ChangeReasonFilter, "Change_Reason", {"enum_fields": {"sentiment": Sentiment}})
tool_orders_router = create_generic_router(ToolOrder, ToolOrderRead, ToolOrderCreate, ToolOrderUpdate, ToolOrderFilter, "Tool_Order")
change_over_router = create_generic_router(ChangeOver, ChangeOverRead, ChangeOverCreate, ChangeOverUpdate, ChangeOverFilter, "Change_Over")
workpiece_router = create_generic_router(Workpiece, WorkpieceRead, WorkpieceCreate, WorkpieceUpdate, WorkpieceFilter, "Workpiece")

# Include the generic routers
router.include_router(users_router, prefix="/users", tags=["users"])
router.include_router(shift_router, prefix="/shifts", tags=["shifts"])
router.include_router(machines_router, prefix="/machines", tags=["machines"])
router.include_router(lines_router, prefix="/lines", tags=["lines"])
router.include_router(manufacturers_router, prefix="/manufacturers", tags=["manufacturers"])
router.include_router(tools_router, prefix="/tools", tags=["tools"])
router.include_router(tool_attributes_router, prefix="/tool_attributes", tags=["tool_attributes"])
router.include_router(change_reason_router, prefix="/change_reasons", tags=["change_reasons"])
router.include_router(tool_orders_router, prefix="/tool_orders", tags=["tool_orders"])
router.include_router(tool_life_router, prefix="/tool_lifes", tags=["tool_lifes"])
router.include_router(note_router, prefix="/notes", tags=["notes"])
router.include_router(tool_type_router, prefix="/tool_types", tags=["tool_types"])
router.include_router(measureable_router, prefix="/measureable", tags=["measureable"])
router.include_router(change_over_router, prefix="/change_overs", tags=["change_overs"])
router.include_router(workpiece_router, prefix="/workpieces", tags=["workpieces"])

router.include_router(recipes_router, prefix="/recipes", tags=["recipes"])

@router.get("/")
async def root(request: Request):
    return templates.TemplateResponse(
        request=request,
        name="engineer/index.html.j2",
        context={
            'item_type': 'Device',
        }
    )
