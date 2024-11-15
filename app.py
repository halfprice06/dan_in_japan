from fastapi import FastAPI, Request, Query
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
import sqlite3

app = FastAPI()

# Mount the static files directory (e.g., images, CSS)
app.mount("/static", StaticFiles(directory="static"), name="static")

# Set up templates directory
templates = Jinja2Templates(directory="templates")

# Database connection function
def get_db_connection():
    conn = sqlite3.connect('photos.db')
    conn.row_factory = sqlite3.Row
    return conn

# Main page
@app.get("/", response_class=HTMLResponse)
async def read_root(request: Request, sort_by: str = Query(None), location: str = Query(None)):
    conn = get_db_connection()
    query = 'SELECT * FROM photo'
    filters = []
    params = []

    if location:
        filters.append('location_name LIKE ?')
        params.append(f'%{location}%')
    if sort_by == 'date':
        query += ' ORDER BY date_taken'

    if filters:
        query += ' WHERE ' + ' AND '.join(filters)

    photos = conn.execute(query, params).fetchall()
    conn.close()
    return templates.TemplateResponse("index.html", {"request": request, "photos": photos}) 