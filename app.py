import os
import uuid
import json
from fastapi import FastAPI, Request, UploadFile, File, HTTPException
from fastapi.responses import RedirectResponse, HTMLResponse, JSONResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel
from utils.main import get_pdf_info, get_svg_page_image, extract_bbox_content, perform_ocr_on_image, get_line_item_data, update_line_item_metadata, delete_line_item_data, get_extracted_items_data

app = FastAPI(
    title="CAD PDF EXTRACTOR",
    description="Find the API documentation below.",
    version="1.0.0",
    contact={"name": "Suman Deb", "email": "suman8deb@gmail.com"}
)

# Define upload folder and ensure it exists
UPLOAD_FOLDER = os.path.join(os.getcwd(), "data", "project2")
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

templates = Jinja2Templates(directory="templates")
app.mount("/static", StaticFiles(directory="static"), name="static")

# JSON file to store the pdf_mapping
PDF_MAPPING_FILE = os.path.join(os.getcwd(), "pdf_mapping.json")

# Function to save pdf_mapping to JSON with the new structure
def save_pdf_mapping():
    with open(PDF_MAPPING_FILE, 'w') as f:
        json.dump(pdf_mapping, f, indent=4)

# Function to load pdf_mapping from JSON with the new structure
def load_pdf_mapping():
    if os.path.exists(PDF_MAPPING_FILE):
        with open(PDF_MAPPING_FILE, 'r') as f:
            return json.load(f)
    return {}

# Load pdf_mapping from JSON on startup
pdf_mapping = load_pdf_mapping()

# Pydantic models
class BBoxData(BaseModel):
    x: float
    y: float
    width: float
    height: float

class PerformOCRData(BaseModel):
    pdfName: str
    pageNum: int
    lineItem: int
    x: float
    y: float
    width: float
    height: float

class GetLineItemData(BaseModel):
    pdfName: str
    pageNum: int
    lineItem: int

# Routes
@app.get("/", response_class=HTMLResponse)
async def upload_pdf_get(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})

@app.post("/", response_class=HTMLResponse)
async def upload_pdf_post(request: Request, pdf_file: UploadFile = File(...)):
    # Check for PDF file extension
    if not pdf_file.filename.lower().endswith('.pdf'):
        return templates.TemplateResponse('index.html', {"request": request, "error": 'Invalid file type. Please upload a PDF.'})
    
    # Save the PDF file
    pdf_path = os.path.join(UPLOAD_FOLDER, pdf_file.filename)
    with open(pdf_path, "wb") as f:
        f.write(await pdf_file.read())
    
    # Generate a unique ID for the PDF
    pdf_id = str(uuid.uuid4())
    
    # Update the pdf_mapping to use the new structure
    project_name = "project1"
    pdf_mapping[project_name] = {
        "project_path": UPLOAD_FOLDER,
        "pdf_name": pdf_file.filename,
        "pdf_id": pdf_id
    }
    
    save_pdf_mapping()  # Save the updated pdf_mapping to JSON
    
    return RedirectResponse(url=f"/viewer/{pdf_id}", status_code=303)

@app.get("/viewer/{pdf_id}", response_class=HTMLResponse)
async def index(request: Request, pdf_id: str):
    # Retrieve the project and PDF info using pdf_id
    project = next((p for p in pdf_mapping.values() if p['pdf_id'] == pdf_id), None)
    
    if not project:
        raise HTTPException(status_code=404, detail="PDF not found")
    
    # Get the PDF info
    pdf_info = get_pdf_info(project["project_path"], project["pdf_name"])
    if not pdf_info:
        raise HTTPException(status_code=404, detail="PDF info not found")
    
    # Extract information about the PDF
    pdf_filename, pdf_name, page_count, pdf_input = pdf_info
    return templates.TemplateResponse('upload.html', {"request": request, "page_count": page_count, "pdf_name": pdf_name, "pdf_id": pdf_id})

@app.get("/get_page/{pdf_id}/{page_num}")
async def get_page(pdf_id: str, page_num: int):
    # Retrieve the project and PDF info using pdf_id
    project = next((p for p in pdf_mapping.values() if p['pdf_id'] == pdf_id), None)
    
    if not project:
        return JSONResponse(content={'error': 'PDF not found'}, status_code=404)
    
    # Get the PDF info
    pdf_info = get_pdf_info(project["project_path"], project["pdf_name"])
    if not pdf_info:
        return JSONResponse(content={'error': 'PDF not found'}, status_code=404)

    pdf_filename, pdf_name, page_count, pdf_input = pdf_info
    if 1 <= page_num <= page_count:
        svg_image = get_svg_page_image(pdf_input, page_num)
        return {'svg_data': svg_image}
    else:
        return JSONResponse(content={'error': 'Page not found'}, status_code=404)

@app.post("/extract_bbox/{pdf_id}/{page_num}")
async def extract_bbox(pdf_id: str, page_num: int, bbox_data: BBoxData):
    # Retrieve the project and PDF info using pdf_id
    project = next((p for p in pdf_mapping.values() if p['pdf_id'] == pdf_id), None)
    
    if not project:
        raise HTTPException(status_code=404, detail='PDF not found')

    # Get the PDF info
    pdf_info = get_pdf_info(project["project_path"], project["pdf_name"])
    if not pdf_info:
        raise HTTPException(status_code=404, detail='PDF info not found')
    
    pdf_filename, pdf_name, page_count, pdf_input = pdf_info
    if 1 <= page_num <= page_count:
        x = bbox_data.x
        y = bbox_data.y
        width = bbox_data.width
        height = bbox_data.height
        message, page_key, line_item_number = extract_bbox_content(project["project_path"], pdf_input, pdf_filename, pdf_name, page_num, x, y, width, height)
        return {'message': message, 'page': page_key, 'line_item': line_item_number}
    else:
        raise HTTPException(status_code=404, detail='Page not found')

@app.get("/get_image/{pdf_name}/{filename}")
async def get_image(pdf_name: str, filename: str):
    file_path = os.path.join(UPLOAD_FOLDER, "images", filename)

    if not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail="Image not found")
    
    return FileResponse(file_path)

@app.post("/perform_ocr")
async def perform_ocr(data: PerformOCRData):
    try:
        pdf_name = data.pdfName
        page_num = data.pageNum
        line_item = data.lineItem
        x = int(data.x)
        y = int(data.y)
        width = int(data.width)
        height = int(data.height)
    except (TypeError, ValueError):
        return {'success': False, 'message': 'Invalid input parameters'}, 400

    success, response_data = perform_ocr_on_image(UPLOAD_FOLDER, pdf_name, page_num, line_item, x, y, width, height)
    if success:
        return {'success': True, 'ocr_text': response_data}
    else:
        raise HTTPException(status_code=404, detail=response_data)

@app.post("/get_line_item")
async def get_line_item(data: GetLineItemData):
    try:
        pdf_name = data.pdfName
        page_num = data.pageNum
        line_item = data.lineItem
    except (TypeError, ValueError):
        return {'success': False, 'message': 'Invalid page number or line item'}, 400

    success, response_data = get_line_item_data(UPLOAD_FOLDER, pdf_name, page_num, line_item)
    if success:
        return {'success': True, 'line_item_data': response_data, 'pdf_name': pdf_name}
    else:
        raise HTTPException(status_code=404, detail=response_data)

@app.post("/submit_metadata")
async def submit_metadata(data: dict):
    try:
        pdf_name = data.get('pdfName')
        page_num = int(data.get('pageNum'))
        line_item = int(data.get('lineItem'))
    except (TypeError, ValueError):
        return {'success': False, 'message': 'Invalid page number or line item'}, 400

    success, message = update_line_item_metadata(UPLOAD_FOLDER, pdf_name, page_num, line_item, data)
    if success:
        return {'success': True, 'message': message}
    else:
        raise HTTPException(status_code=404, detail=message)

@app.delete("/delete_line_item/{pdf_id}/{page_num}/{line_item}")
async def delete_line_item(pdf_id: str, page_num: int, line_item: int):
    # Retrieve the project and PDF info using pdf_id
    project = next((p for p in pdf_mapping.values() if p['pdf_id'] == pdf_id), None)
    
    if not project:
        raise HTTPException(status_code=404, detail='PDF not found')

    pdf_info = get_pdf_info(project["project_path"], project["pdf_name"])
    if not pdf_info:
        raise HTTPException(status_code=404, detail='PDF info not found')

    pdf_filename, pdf_name, page_count, pdf_input = pdf_info
    success, message = delete_line_item_data(project["project_path"], pdf_name, page_num, line_item)
    if success:
        return {'success': True}
    else:
        raise HTTPException(status_code=404, detail=message)

@app.get("/get_extracted_items/{pdf_name}")
async def get_extracted_items(pdf_name: str):
    data = get_extracted_items_data(UPLOAD_FOLDER, pdf_name)
    return data

# Run the app with Uvicorn if executed directly
if __name__ == '__main__':
    import uvicorn
    uvicorn.run(app, host='0.0.0.0', port=8888)
