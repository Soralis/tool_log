from fastapi import APIRouter, Request, File, UploadFile
from fastapi.responses import HTMLResponse

from sqlmodel import Session, select
from sqlalchemy.dialects.postgresql import insert
import io
import openpyxl
import pandas as pd

from app.models import OrderCompletion, User, Workpiece

from app.database_config import engine
from app.templates.jinja_functions import templates

router = APIRouter()

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
    # Process the tool consumption file here
    return {"filename": file.filename, "type": "tool_consumption"}

@router.post("/upload/parts-produced")
async def upload_parts_produced(file: UploadFile = File(...)):
    """Handle parts production file upload"""
    print(f'Processing parts production file: {file.filename}')

    if file.filename.lower().endswith('.xlsx'):
        # Read it, 'f' type is bytes
        f = await file.read()
        xlsx = io.BytesIO(f)
        wb = openpyxl.load_workbook(xlsx)
        ws = wb['Sheet1']

        df = pd.DataFrame(ws.values)
        df.columns = df.iloc[0]
        df = df[2:]
        
        with Session(engine) as session:
            # users = session.exec(select(User)).all()
            workpieces = session.exec(select(Workpiece)).all()
            workpieces = {workpiece.material: workpiece.id for workpiece in workpieces}
            
            # Prepare all valid records
            records = []
            for _, row in df.iterrows():
                if row['Document Date'] is None:
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
            
            # Insert all records in a single operation, ignoring duplicates
            stmt = insert(OrderCompletion).values(records)
            stmt = stmt.on_conflict_do_nothing(index_elements=['document_number'])
            session.exec(stmt)
            session.commit()
    else:
        return {"filename": file.filename, "type": "parts_produced", "error": "Unsupported file type"}

    return {"filename": file.filename, "type": "parts_produced"}
