from fastapi import APIRouter, Request, File, UploadFile
from fastapi.responses import HTMLResponse

from sqlmodel import Session, select
from sqlalchemy.dialects.postgresql import insert
import io
import openpyxl
import pandas as pd
from datetime import datetime, timedelta

from app.models import OrderCompletion, User, Workpiece, ToolConsumption, Tool, Machine, Manufacturer, ToolType

from app.database_config import engine
from app.templates.jinja_functions import templates

router = APIRouter()


async def read_excel(file: UploadFile, key_column: str, sheet_name: str = 'Sheet1'):
    """Read an Excel file and return a DataFrame"""
    # Read it, 'f' type is bytes
    if not file.filename.lower().endswith('.xlsx'):
        return None
    
    f = await file.read()
    xlsx = io.BytesIO(f)
    wb = openpyxl.load_workbook(xlsx)
    ws = wb[sheet_name]

    df = pd.DataFrame(ws.values)

    for idx, row in df.iterrows():
        try: 
            if key_column in row.values:
                print('found row:', idx)
                print(row)
                break
        except KeyError:
            continue

    df.columns = df.iloc[idx]
    df = df[idx+1:]

    df.dropna(axis=1, thresh=3, inplace=True)

    return df

async def write_to_db(records: list, model, session: Session, result: dict):
    stmt = insert(model).values(records)
    stmt = stmt.on_conflict_do_nothing()
    stmt = stmt.returning(model.id)

    inserted_rows = session.exec(stmt).fetchall()
    num_conflicts = len(records) - len(inserted_rows)
    session.commit()    

    result['total_records'] += len(records)
    result['inserted'] += len(inserted_rows)
    result['conflicts'] += num_conflicts

    return result

@router.get("/upload", response_class=HTMLResponse)
async def upload_page(request: Request):
    """Render the file upload page"""
    return templates.TemplateResponse(
        "dashboard/upload.html.j2",
        {"request": request}
    )

@router.post("/upload/tool-consumption")
async def upload_tool_consumption(file: UploadFile = File(...)):
    """Handle tool consumption file upload"""
    print(f'Processing tool consumption file: {file.filename}')

    key_column = 'Trans Date'
    df = await read_excel(file, key_column, 'Results')

    with Session(engine) as session:
        users = session.exec(select(User)).all()
        users = {user.name.lower(): user.id for user in users}

        machines = session.exec(select(Machine)).all()
        machines = {machine.description: machine for machine in machines}

        tools = session.exec(select(Tool)).all()
        tools = {tool.number: tool.id for tool in tools}

        workpieces = session.exec(select(Workpiece)).all()
        workpieces = {workpiece.description: workpiece.id for workpiece in workpieces}
        
        manufacturer = session.exec(select(Manufacturer).where(Manufacturer.name=='Undefined')).first()
        tool_type = session.exec(select(ToolType).where(ToolType.name=='Undefined')).first()

        # Prepare all valid records
        records = []
        result = {'total_records': 0, 'inserted': 0, 'conflicts': 0}
        for _, row in df.iterrows():
            if row[key_column] is None:
                continue
            try:
                user_id = None
                if row['Employee Name']:
                    username = row['Employee Name'].split(', ')
                    username = f'{username[1].lower()} {username[0].lower()}' if len(username) >= 1 else False
                    user_id = users.get(username, None)
                
                machine, machine_id = None, None
                if row['Machine']:
                    machine = machines.get(row['Machine'].split('-', 1)[1], None)
                    machine_id = machine.id if machine else None

                tool_id = tools.get(row['Item'], None)
                if tool_id is None:
                    new_tool = Tool(
                        number=row['Item'],
                        manufacturer_name=row['Description'],
                        name=row['Description2'] if row['Description2'] is not None else row['Description'],
                        manufacturer_id=manufacturer.id,
                        tool_type_id=tool_type.id
                    )
                    session.add(new_tool)
                    session.commit()
                    session.refresh(new_tool)
                    tool_id = new_tool.id
                    tools[row['Item']] = tool_id
                                        
                workpiece_id = None
                if row['Product']:
                    workpiece_id = workpieces.get(row['Product'], None)

                recipe_id, tool_position_id = None, None

                if machine and tool_id and workpiece_id:
                    for recipe in machine.recipes:
                        if recipe.workpiece_id == workpiece_id:
                            recipe_id = recipe.id
                            for tool_position in recipe.tool_positions:
                                if tool_position.tool_id == tool_id:
                                    tool_position_id = tool_position.id
                                    break
                            if recipe_id:
                                break
                
                date = row['Trans Date']
                time = datetime.strptime(row['Trans Time'], "%I:%M%p").time()
                item_datetime = date + timedelta(hours=time.hour, minutes=time.minute)

                records.append({
                    'datetime': item_datetime,
                    'number': row['Trans Number'],
                    'consumption_type': row['Type Desc'],
                    'quantity': row['Qty'],
                    'value': row['Extension'],
                    'price': row['Price'],
                    'user_id': user_id,
                    'machine_id': machine_id,
                    'tool_id': tool_id,
                    'recipe_id': recipe_id,
                    'tool_position_id': tool_position_id,
                    'workpiece_id': workpiece_id,
                })
            except Exception as e:
                print(e)

            if len(records) > 100:
                result = await write_to_db(records, ToolConsumption, session, result)
                records = []
        
        # Insert all records in a single operation, ignoring duplicates
        if records:
            result = await write_to_db(records, ToolConsumption, session, result)

    return {"filename": file.filename, "type": "tool_consumption", 'result': result}


@router.post("/upload/parts-produced")
async def upload_parts_produced(file: UploadFile = File(...)):
    """Handle parts production file upload"""
    print(f'Processing parts production file: {file.filename}')

    key_column = 'Posting Date'
    df = await read_excel(file, key_column)

    if df is None:
        return {"filename": file.filename, "type": "parts_produced", "error": "Unsupported file type"}
        
    with Session(engine) as session:
        # users = session.exec(select(User)).all()
        workpieces = session.exec(select(Workpiece)).all()
        workpieces = {workpiece.material: workpiece.id for workpiece in workpieces}
        
        # Prepare all valid records
        records = []
        result = {'total_records': 0, 'inserted': 0, 'conflicts': 0}
        for _, row in df.iterrows():
            if row[key_column] is None:
                continue
            try:
                records.append({
                    'quantity': row['Qty in unit of entry'],
                    'vendor': row['Vendor'],
                    'batch': row['Batch'],
                    'customer': row['Customer'],
                    'order': row['Order'],
                    'document_number': row['Material Document'],
                    'date': row['Document Date'],
                    'time': row['Time of Entry'],
                    'value': row['Amt.in loc.cur.'],
                    'workpiece_id': workpieces[row['Material']],
                })
            except Exception as e:
                print(e)

            if len(records) > 100:
                result = await write_to_db(records, OrderCompletion, session, result)
                records = []
        
        # Insert all records in a single operation, ignoring duplicates
        if records:
            result = await write_to_db(records, OrderCompletion, session, result)

    return {"filename": file.filename, "type": "parts_produced", 'result': result}
