from fastapi.templating import Jinja2Templates
from typing import get_origin, get_args, Union, List
import datetime
import enum

templates = Jinja2Templates(directory="app/templates")


def field_types(thing):
    # Extract inner type from Optional or Union
    if get_origin(thing) is Union:
        args = get_args(thing)
        # Handle Optional[X] which is Union[X, None]
        if type(None) in args:
            thing = args[0]

    # Handle List type
    if get_origin(thing) is List:
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

def getattr_filter(obj, attr):
    result = getattr(obj, attr,'')
    while not isinstance(result, str):
        result = getattr(result, 'name','')
    return result

def get_fked(obj):
    for key in obj:
        print(type(obj[key]), isinstance(obj[key], enum.Enum))
    fked = {key: obj[key].name if isinstance(obj[key], enum.Enum) else obj[key] for key in obj}    
    return fked

templates.env.filters['field_types'] = field_types
templates.env.filters['getattr_filter'] = getattr_filter
templates.env.filters['get_fked'] = get_fked