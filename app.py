from fastapi import FastAPI, Request, Query
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.templating import Jinja2Templates
from fastapi.middleware.gzip import GZipMiddleware
import sqlite3
from datetime import datetime
import json
import random

app = FastAPI()

# Mount the static files directory
app.mount("/static", StaticFiles(directory="static"), name="static")

# Set up templates directory
templates = Jinja2Templates(directory="templates")

# Add compression middleware
app.add_middleware(GZipMiddleware, minimum_size=1000)

class DateTimeEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, datetime):
            return obj.strftime('%Y-%m-%d %H:%M:%S')
        return super().default(obj)

def serialize_photos(photos):
    """Convert photos to JSON-serializable format"""
    return json.loads(json.dumps(photos, cls=DateTimeEncoder))

# Database connection function
def get_db_connection():
    conn = sqlite3.connect('photos.db')
    
    def dict_factory(cursor, row):
        d = {}
        for idx, col in enumerate(cursor.description):
            value = row[idx]
            if col[0] == 'date_taken' and value:
                try:
                    d[col[0]] = datetime.strptime(value, '%Y:%m:%d %H:%M:%S')
                except ValueError:
                    d[col[0]] = None
            else:
                d[col[0]] = value
        return d
    
    conn.row_factory = dict_factory
    return conn

# Main page
@app.get("/", response_class=HTMLResponse)
async def read_root(request: Request, sort_by: str = Query('date-asc'), location: str = Query(None)):
    conn = get_db_connection()
    query = 'SELECT * FROM photo'
    filters = []
    params = []

    if location:
        filters.append('location_name LIKE ?')
        params.append(f'%{location}%')

    if filters:
        query += ' WHERE ' + ' AND '.join(filters)

    if sort_by == 'date-asc':
        query += ' ORDER BY date_taken ASC NULLS LAST'
    elif sort_by == 'location':
        query += ' ORDER BY location_name NULLS LAST'
    else:
        query += ' ORDER BY date_taken DESC NULLS LAST'

    photos = conn.execute(query, params).fetchall()
    conn.close()

    # Get unique locations for the filter dropdown
    unique_locations = list(set(photo['location_name'] for photo in photos if photo['location_name']))
    
    # Get 3 random photos for the featured section
    random_photos = random.sample(photos, min(3, len(photos)))
    
    # Serialize photos for JavaScript
    serialized_photos = serialize_photos(photos)
    
    return templates.TemplateResponse(
        "index.html", 
        {
            "request": request, 
            "photos": photos,
            "featured_photos": random_photos,
            "serialized_photos": serialized_photos,
            "unique_locations": unique_locations
        }
    )

# Add API endpoint for lazy loading
@app.get("/api/photos")
async def get_photos(
    page: int = Query(1, ge=1),
    per_page: int = Query(12, ge=1, le=50),
    location: str = None,
    sort_by: str = None
):
    offset = (page - 1) * per_page
    
    query = 'SELECT * FROM photo'
    params = []
    
    if location:
        query += ' WHERE location_name = ?'
        params.append(location)
        
    if sort_by == 'date-asc':
        query += ' ORDER BY date_taken ASC'
    elif sort_by == 'date-desc':
        query += ' ORDER BY date_taken DESC'
        
    query += ' LIMIT ? OFFSET ?'
    params.extend([per_page, offset])
    
    conn = get_db_connection()
    photos = conn.execute(query, params).fetchall()
    conn.close()
    
    return JSONResponse(content={"photos": photos}) 