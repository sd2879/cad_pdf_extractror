from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates

app = FastAPI()  # Renamed from app_combined to app

templates = Jinja2Templates(directory="templates")

@app.get("/", response_class=HTMLResponse)
async def get_upload_folder(request: Request):
    return templates.TemplateResponse("combined.html", {"request": request})
