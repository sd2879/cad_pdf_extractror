import os
import uuid
import json
from fastapi import FastAPI, Request, UploadFile, File, HTTPException, Body
from fastapi.responses import RedirectResponse, HTMLResponse, JSONResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel
from utils.main import (
    get_pdf_info,
    get_svg_page_image,
    extract_bbox_content,
    perform_ocr_on_image,
    get_line_item_data,
    update_line_item_metadata,
    delete_line_item_data,
    get_extracted_items_data
)

# Initialize the FastAPI app with metadata like title, description, and version
app = FastAPI(
    title="CAD PDF EXTRACTOR",
    description="Find the API documentation below.",
    version="1.0.0",
    contact={"name": "Suman Deb", "email": "suman8deb@gmail.com"}
)

# Global variables to manage the upload folder and PDF mapping
UPLOAD_FOLDER = None
project_name_ui = None
PDF_MAPPING_FILE = None
pdf_mapping = {}

# Set up Jinja2 templates and static files directories
templates = Jinja2Templates(directory="templates")
app.mount("/static", StaticFiles(directory="static"), name="static")

# Pydantic models to handle data in API requests
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

# Favicon route (standard, no need to document in the API schema)
@app.get("/favicon.ico", include_in_schema=False)
async def favicon():
    return FileResponse(os.path.join("static", "favicon.ico"))

# Helper function to save PDF mapping to a JSON file
def save_pdf_mapping():
    with open(PDF_MAPPING_FILE, 'w') as f:
        json.dump(pdf_mapping, f, indent=4)

# Helper function to load PDF mapping from the JSON file
def load_pdf_mapping():
    global pdf_mapping
    if os.path.exists(PDF_MAPPING_FILE):
        with open(PDF_MAPPING_FILE, 'r') as f:
            pdf_mapping = json.load(f)
    else:
        pdf_mapping = {}

# Route to set the upload folder dynamically and load existing PDF mappings
@app.post("/set_project_path")
async def set_project_path(data: dict = Body(...)):
    global UPLOAD_FOLDER, project_name_ui, PDF_MAPPING_FILE
    project_path = data.get('project_path')
    if not project_path:
        return JSONResponse(content={'error': 'Please provide project_path in the JSON body.'}, status_code=400)
    UPLOAD_FOLDER = os.path.abspath(project_path)
    os.makedirs(UPLOAD_FOLDER, exist_ok=True)
    project_name_ui = os.path.basename(UPLOAD_FOLDER)
    PDF_MAPPING_FILE = os.path.join(UPLOAD_FOLDER, "companies_mapping.json")
    load_pdf_mapping()  # Load PDF mappings from the JSON file

    # Generate or retrieve the pdf_id
    pdf_files = [f for f in os.listdir(UPLOAD_FOLDER) if f.lower().endswith('.pdf')]
    if pdf_files:
        pdf_file = pdf_files[0]
        pdf_id = next((p['pdf_id'] for p in pdf_mapping.values() if p['pdf_name'] == pdf_file), None)
        if not pdf_id:
            pdf_id = str(uuid.uuid4())
            project_name = project_name_ui
            pdf_mapping[project_name] = {
                "project_path": UPLOAD_FOLDER,
                "pdf_name": pdf_file,
                "pdf_id": pdf_id
            }
            save_pdf_mapping()
    else:
        pdf_id = None  # No PDF files found

    return JSONResponse(content={'pdf_id': pdf_id}, status_code=200)


# Route to render the main page or redirect to the PDF viewer if a PDF already exists
@app.get("/", response_class=HTMLResponse)
async def upload_pdf_get(request: Request):
    global UPLOAD_FOLDER, project_name_ui
    if UPLOAD_FOLDER is None:
        return HTMLResponse("UPLOAD_FOLDER not set. Please set it first.", status_code=400)
    
    # Check if any PDF files are already uploaded
    pdf_files = [f for f in os.listdir(UPLOAD_FOLDER) if f.lower().endswith('.pdf')]
    
    if pdf_files:
        pdf_file = pdf_files[0]
        pdf_id = next((p['pdf_id'] for p in pdf_mapping.values() if p['pdf_name'] == pdf_file), None)

        # If the PDF is already mapped, redirect to its viewer; otherwise, create a new mapping
        if pdf_id:
            return RedirectResponse(url=f"/viewer/{pdf_id}", status_code=303)
        else:
            pdf_id = str(uuid.uuid4())
            project_name = project_name_ui
            pdf_mapping[project_name] = {
                "project_path": UPLOAD_FOLDER,
                "pdf_name": pdf_file,
                "pdf_id": pdf_id
            }
            save_pdf_mapping()
            return RedirectResponse(url=f"/viewer/{pdf_id}", status_code=303)
    
    # If no PDF exists, render the index.html page for uploading a new PDF
    return templates.TemplateResponse("index.html", {"request": request})

# Route to handle the PDF upload via POST request
@app.post("/", response_class=HTMLResponse)
async def upload_pdf_post(request: Request, pdf_file: UploadFile = File(...)):
    global UPLOAD_FOLDER, project_name_ui
    if UPLOAD_FOLDER is None:
        return HTMLResponse("UPLOAD_FOLDER not set. Please go to /set_upload_folder?upload_folder=YOUR_PATH", status_code=400)
    
    # Validate file extension to ensure it's a PDF
    if not pdf_file.filename.lower().endswith('.pdf'):
        return templates.TemplateResponse('index.html', {"request": request, "error": 'Invalid file type. Please upload a PDF.'})
    
    # Save the PDF to the specified upload folder
    pdf_path = os.path.join(UPLOAD_FOLDER, pdf_file.filename)
    with open(pdf_path, "wb") as f:
        f.write(await pdf_file.read())
    
    # Generate a unique ID for the uploaded PDF and update the mapping
    pdf_id = str(uuid.uuid4())
    project_name = project_name_ui
    pdf_mapping[project_name] = {
        "project_path": UPLOAD_FOLDER,
        "pdf_name": pdf_file.filename,
        "pdf_id": pdf_id
    }
    
    save_pdf_mapping()  # Save the mapping after uploading
    return RedirectResponse(url=f"/viewer/{pdf_id}", status_code=303)

# Viewer page for displaying the PDF information
@app.get("/viewer/{pdf_id}", response_class=HTMLResponse)
async def index(request: Request, pdf_id: str):
    if UPLOAD_FOLDER is None:
        return HTMLResponse("UPLOAD_FOLDER not set. Please set it first.", status_code=400)
    
    # Retrieve the PDF info based on the provided pdf_id
    project = next((p for p in pdf_mapping.values() if p['pdf_id'] == pdf_id), None)
    
    if not project:
        raise HTTPException(status_code=404, detail="PDF not found")
    
    pdf_info = get_pdf_info(project["project_path"], project["pdf_name"])
    if not pdf_info:
        raise HTTPException(status_code=404, detail="PDF info not found")
    
    pdf_filename, pdf_name, page_count, pdf_input = pdf_info
    return templates.TemplateResponse('upload.html', {"request": request, "page_count": page_count, "pdf_name": pdf_name, "pdf_id": pdf_id})

# Route to get an SVG image of a specific page from the PDF
@app.get("/get_page/{pdf_id}/{page_num}")
async def get_page(pdf_id: str, page_num: int):
    if UPLOAD_FOLDER is None:
        return JSONResponse(content={'error': 'UPLOAD_FOLDER not set. Please set it first.'}, status_code=400)
    
    # Retrieve the PDF info based on the provided pdf_id
    project = next((p for p in pdf_mapping.values() if p['pdf_id'] == pdf_id), None)
    
    if not project:
        return JSONResponse(content={'error': 'PDF not found'}, status_code=404)

    pdf_info = get_pdf_info(project["project_path"], project["pdf_name"])
    if not pdf_info:
        return JSONResponse(content={'error': 'PDF not found'}, status_code=404)

    pdf_filename, pdf_name, page_count, pdf_input = pdf_info
    # Check if the requested page number is within the valid range
    if 1 <= page_num <= page_count:
        svg_image = get_svg_page_image(pdf_input, page_num)
        return {'svg_data': svg_image}
    else:
        return JSONResponse(content={'error': 'Page not found'}, status_code=404)

# Route to extract content from a specific bounding box on a PDF page
@app.post("/extract_bbox/{pdf_id}/{page_num}")
async def extract_bbox(pdf_id: str, page_num: int, bbox_data: BBoxData):
    if UPLOAD_FOLDER is None:
        raise HTTPException(status_code=400, detail='UPLOAD_FOLDER not set. Please set it first.')
    
    # Retrieve the PDF info based on the provided pdf_id
    project = next((p for p in pdf_mapping.values() if p['pdf_id'] == pdf_id), None)
    
    if not project:
        raise HTTPException(status_code=404, detail='PDF not found')

    pdf_info = get_pdf_info(project["project_path"], project["pdf_name"])
    if not pdf_info:
        raise HTTPException(status_code=404, detail='PDF info not found')
    
    pdf_filename, pdf_name, page_count, pdf_input = pdf_info
    # Validate the page number and extract bounding box content
    if 1 <= page_num <= page_count:
        x = bbox_data.x
        y = bbox_data.y
        width = bbox_data.width
        height = bbox_data.height
        message, page_key, line_item_number = extract_bbox_content(project["project_path"], pdf_input, pdf_filename, pdf_name, page_num, x, y, width, height)
        return {'message': message, 'page': page_key, 'line_item': line_item_number}
    else:
        raise HTTPException(status_code=404, detail='Page not found')

# Route to serve images extracted from PDF content
@app.get("/get_image/{pdf_name}/{filename}")
async def get_image(pdf_name: str, filename: str):
    if UPLOAD_FOLDER is None:
        raise HTTPException(status_code=400, detail='UPLOAD_FOLDER not set. Please set it first.')
    
    # Construct the file path and serve the image if it exists
    file_path = os.path.join(UPLOAD_FOLDER, "images", filename)

    if not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail="Image not found")
    
    return FileResponse(file_path)

# Route to perform OCR on a specific region of a PDF page
@app.post("/perform_ocr")
async def perform_ocr(data: PerformOCRData):
    if UPLOAD_FOLDER is None:
        raise HTTPException(status_code=400, detail='UPLOAD_FOLDER not set. Please set it first.')
    
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

    # Perform OCR and return the extracted text
    success, response_data = perform_ocr_on_image(UPLOAD_FOLDER, pdf_name, page_num, line_item, x, y, width, height)
    if success:
        return {'success': True, 'ocr_text': response_data}
    else:
        raise HTTPException(status_code=404, detail=response_data)

# Route to retrieve line item data from a specific page in the PDF
@app.post("/get_line_item")
async def get_line_item(data: GetLineItemData):
    if UPLOAD_FOLDER is None:
        raise HTTPException(status_code=400, detail='UPLOAD_FOLDER not set. Please set it first.')
    
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

# Route to update metadata for a specific line item
@app.post("/submit_metadata")
async def submit_metadata(data: dict):
    if UPLOAD_FOLDER is None:
        raise HTTPException(status_code=400, detail='UPLOAD_FOLDER not set. Please set it first.')
    
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

# Route to delete a specific line item from the PDF content
@app.delete("/delete_line_item/{pdf_id}/{page_num}/{line_item}")
async def delete_line_item(pdf_id: str, page_num: int, line_item: int):
    if UPLOAD_FOLDER is None:
        raise HTTPException(status_code=400, detail='UPLOAD_FOLDER not set. Please set it first.')
    
    # Retrieve the PDF info based on the provided pdf_id
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

# Route to retrieve all extracted items from a PDF
@app.get("/get_extracted_items/{pdf_name}")
async def get_extracted_items(pdf_name: str):
    if UPLOAD_FOLDER is None:
        raise HTTPException(status_code=400, detail='UPLOAD_FOLDER not set. Please set it first.')
    
    # Retrieve all the extracted items from the PDF
    data = get_extracted_items_data(UPLOAD_FOLDER, pdf_name)
    return data

# Run the app using Uvicorn when executed directly
if __name__ == '__main__':
    import uvicorn
    uvicorn.run(app, host='0.0.0.0', port=8888)