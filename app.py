import os
import uuid
from fastapi import FastAPI, Request, UploadFile, File, Form, Depends, HTTPException, status
from fastapi.responses import JSONResponse, RedirectResponse, FileResponse, HTMLResponse
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

app = FastAPI(
    title="CAD PDF EXTRACTOR",
    description="Find the API documentation below.",
    version="1.0.0",
    contact={
        "name": "Suman Deb",
        "email": "suman8deb@gmail.com",
    },
)

UPLOAD_FOLDER = os.path.join(os.getcwd(), "data", "pdf")
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

templates = Jinja2Templates(directory="templates")
app.mount("/static", StaticFiles(directory="static"), name="static")

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

@app.get("/", response_class=HTMLResponse)
async def upload_pdf_get(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})

@app.post("/", response_class=HTMLResponse)
async def upload_pdf_post(request: Request, pdf_file: UploadFile = File(...)):
    if not pdf_file:
        return templates.TemplateResponse('upload.html', {"request": request, "error": 'No file part'})
    if pdf_file.filename == '':
        return templates.TemplateResponse('upload.html', {"request": request, "error": 'No selected file'})
    if pdf_file.filename.lower().endswith('.pdf'):
        pdf_id = str(uuid.uuid4())
        filename = f"{pdf_id}_{pdf_file.filename}"
        pdf_path = os.path.join(UPLOAD_FOLDER, filename)
        with open(pdf_path, "wb") as f:
            f.write(await pdf_file.read())
        return RedirectResponse(url=f"/viewer/{pdf_id}", status_code=303)
    else:
        return templates.TemplateResponse('index.html', {"request": request, "error": 'Invalid file type. Please upload a PDF.'})

@app.get("/viewer/{pdf_id}", response_class=HTMLResponse)
async def index(request: Request, pdf_id: str):
    pdf_info = get_pdf_info(UPLOAD_FOLDER, pdf_id)
    if not pdf_info:
        raise HTTPException(status_code=404, detail="PDF not found")
    pdf_filename, pdf_name, page_count = pdf_info
    return templates.TemplateResponse('upload.html', {"request": request, "page_count": page_count, "pdf_name": pdf_name, "pdf_id": pdf_id})

@app.get("/get_page/{pdf_id}/{page_num}")
async def get_page(pdf_id: str, page_num: int):
    pdf_info = get_pdf_info(UPLOAD_FOLDER, pdf_id)
    if not pdf_info:
        return JSONResponse(content={'error': 'PDF not found'}, status_code=404)
    pdf_filename, pdf_name, page_count = pdf_info
    if 1 <= page_num <= page_count:
        svg_image = get_svg_page_image(pdf_filename, page_num)
        return {'svg_data': svg_image}
    else:
        return JSONResponse(content={'error': 'Page not found'}, status_code=404)

@app.post("/extract_bbox/{pdf_id}/{page_num}")
async def extract_bbox(pdf_id: str, page_num: int, bbox_data: BBoxData):
    pdf_info = get_pdf_info(UPLOAD_FOLDER, pdf_id)
    if not pdf_info:
        raise HTTPException(status_code=404, detail='PDF not found')
    pdf_filename, pdf_name, page_count = pdf_info
    if 1 <= page_num <= page_count:
        x = bbox_data.x
        y = bbox_data.y
        width = bbox_data.width
        height = bbox_data.height
        message, page_key, line_item_number = extract_bbox_content(pdf_filename, pdf_name, page_num, x, y, width, height)
        return {'message': message, 'page': page_key, 'line_item': line_item_number}
    else:
        raise HTTPException(status_code=404, detail='Page not found')

@app.get("/get_image/{pdf_name}/{filename}")
async def get_image(pdf_name: str, filename: str):
    save_directory = os.path.join(os.getcwd(), "data", "instance", pdf_name)
    file_path = os.path.join(save_directory, filename)
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

    success, response_data = perform_ocr_on_image(pdf_name, page_num, line_item, x, y, width, height)
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

    success, response_data = get_line_item_data(pdf_name, page_num, line_item)
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

    success, message = update_line_item_metadata(pdf_name, page_num, line_item, data)
    if success:
        return {'success': True, 'message': message}
    else:
        raise HTTPException(status_code=404, detail=message)

@app.delete("/delete_line_item/{pdf_id}/{page_num}/{line_item}")
async def delete_line_item(pdf_id: str, page_num: int, line_item: int):
    pdf_info = get_pdf_info(UPLOAD_FOLDER, pdf_id)
    if not pdf_info:
        raise HTTPException(status_code=404, detail='PDF not found')
    pdf_filename, pdf_name, page_count = pdf_info

    success, message = delete_line_item_data(pdf_name, page_num, line_item)
    if success:
        return {'success': True}
    else:
        raise HTTPException(status_code=404, detail=message)

@app.get("/get_extracted_items/{pdf_name}")
async def get_extracted_items(pdf_name: str):
    data = get_extracted_items_data(pdf_name)
    return data

if __name__ == '__main__':
    import uvicorn
    uvicorn.run(app, host='0.0.0.0', port=8888)
