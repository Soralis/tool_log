from fastapi.templating import Jinja2Templates
from typing import get_origin, get_args, Union
import datetime

templates = Jinja2Templates(directory="app/templates")


def field_types(thing):
    # Extract inner type from Optional or Union
    if get_origin(thing) is Union:
        args = get_args(thing)
        # Handle Optional[X] which is Union[X, None]
        if type(None) in args:
            thing = args[0]

    # Handle List type
    if get_origin(thing) is list:
        return "select"

    # Map Python types to HTML input types
    type_mapping = {
        str: "text",
        int: "number",
        float: "number",
        bool: "checkbox",
        list: "select",
        dict: "select",
        datetime.date: "date",  # For date input
        datetime.datetime: "date",  # For datetime input
        # Add more types as needed
    }

    return type_mapping.get(thing, "text")  # Default to "text" if the type is not found



templates.env.filters['field_types'] = field_types