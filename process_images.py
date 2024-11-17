import os
import sqlite3
from PIL import Image
from PIL.ExifTags import TAGS, GPSTAGS
import requests
from anthropic import Anthropic
import base64
from serpapi import GoogleSearch
import dotenv
import setup_database
from io import BytesIO
import sys
import shutil

dotenv.load_dotenv()

def ensure_directories():
    """Create necessary directories if they don't exist"""
    directories = ['static/photos', 'maps']
    for directory in directories:
        os.makedirs(directory, exist_ok=True)
        print(f"Ensured directory exists: {directory}")

def check_required_env_vars():
    required_vars = ['ANTHROPIC_API_KEY', 'SERP_API_KEY', 'SYSTEM_PROMPT']
    missing_vars = [var for var in required_vars if var not in os.environ]
    
    if missing_vars:
        print("Error: Missing required environment variables:")
        for var in missing_vars:
            print(f"- {var}")
        print("\nPlease make sure these variables are set in your .env file")
        sys.exit(1)

def get_exif_data(image_path):
    print(f"Extracting EXIF data from {image_path}...")
    image = Image.open(image_path)
    exif_data = {}
    try:
        info = image._getexif()
        if info:
            for tag, value in info.items():
                tag_name = TAGS.get(tag, tag)
                if tag_name == 'GPSInfo':
                    gps_data = {}
                    for key in value.keys():
                        decode = GPSTAGS.get(key, key)
                        gps_data[decode] = value[key]
                    exif_data['GPSInfo'] = gps_data
                else:
                    exif_data[tag_name] = value
    except AttributeError as e:
        print(f"Warning: Could not extract EXIF data from {image_path}: {str(e)}")
    return exif_data

def get_lat_lon(gps_info):
    if not gps_info:
        return None, None

    def convert_to_degrees(value):
        d = value[0].numerator / value[0].denominator
        m = value[1].numerator / value[1].denominator
        s = value[2].numerator / value[2].denominator
        return d + (m / 60.0) + (s / 3600.0)

    try:
        lat = convert_to_degrees(gps_info['GPSLatitude'])
        lon = convert_to_degrees(gps_info['GPSLongitude'])

        if gps_info['GPSLatitudeRef'] != 'N':
            lat = -lat
        if gps_info['GPSLongitudeRef'] != 'E':
            lon = -lon

        return lat, lon
    except KeyError as e:
        print(f"Warning: Missing GPS data component: {str(e)}")
        return None, None
    except Exception as e:
        print(f"Error converting GPS coordinates: {str(e)}")
        return None, None

def generate_caption(image_path, photographer, map_image_path=None):
    print(f"Generating caption for {image_path}...")
    try:
        anthropic_client = Anthropic(api_key=os.environ['ANTHROPIC_API_KEY'])

        system_prompt = os.environ['SYSTEM_PROMPT'].format(photographer=photographer)

        messages_content = []

        if map_image_path is not None:
            try:
                print("Processing map image...")
                with Image.open(map_image_path) as img:
                    buffer = BytesIO()
                    img.convert('RGB').save(buffer, format='JPEG')
                    map_image_base64 = base64.b64encode(buffer.getvalue()).decode('utf-8')
                messages_content.append({
                    'type': 'image',
                    'source': {
                        'type': 'base64',
                        'media_type': 'image/jpeg',
                        'data': map_image_base64
                    }
                })
            except Exception as e:
                print(f"Warning: Failed to process map image: {str(e)}")

        try:
            print("Processing main image...")
            with Image.open(image_path) as img:
                buffer = BytesIO()
                img.convert('RGB').save(buffer, format='JPEG')
                image_base64 = base64.b64encode(buffer.getvalue()).decode('utf-8')
            messages_content.append({
                'type': 'image',
                'source': {
                    'type': 'base64',
                    'media_type': 'image/jpeg',
                    'data': image_base64
                }
            })
        except Exception as e:
            print(f"Error: Failed to process main image: {str(e)}")
            return "Error generating caption"

        messages = [
            {
                'role': 'user',
                'content': messages_content
            }
        ]

        print("Sending request to Claude API...")
        response = anthropic_client.messages.create(
            model='claude-3-5-sonnet-20241022',
            messages=messages,
            system=system_prompt,
            max_tokens=500,
            temperature=0
        )

        caption = ' '.join(block.text for block in response.content if block.type == 'text').strip()
        print("Caption generated successfully")
        return caption
    except Exception as e:
        print(f"Error generating caption: {str(e)}")
        return "Error generating caption"

def get_location_name(lat, lon):
    print(f"Getting location name for coordinates: {lat}, {lon}")
    try:
        url = 'https://nominatim.openstreetmap.org/reverse'
        params = {
            'lat': lat,
            'lon': lon,
            'format': 'jsonv2',
            'accept-language': 'en'  # Request English names
        }
        headers = {
            'Accept-Language': 'en'  # Additional header to ensure English response
        }
        response = requests.get(url, params=params, headers=headers)
        if response.status_code == 200:
            data = response.json()
            # Try to get the most relevant location name
            address = data.get('address', {})
            location = (
                address.get('city') or 
                address.get('town') or 
                address.get('village') or 
                address.get('suburb') or 
                address.get('district')
            )
            # If we got a location, also get the state/prefecture for context
            if location:
                state = address.get('state') or address.get('province')
                if state and state != location:
                    location = f"{location}, {state}"
                print(f"Location found: {location}")
                return location
            return None
        else:
            print(f"Error getting location name: HTTP {response.status_code}")
            return None
    except Exception as e:
        print(f"Error getting location name: {str(e)}")
        return None

def generate_map_image(lat, lon, filename):
    if lat is None or lon is None:
        print("Skipping map generation - no coordinates provided")
        return None

    print(f"Generating map image for coordinates: {lat}, {lon}")
    try:
        params = {
            "api_key": os.environ['SERP_API_KEY'],
            "engine": "google",
            "q": f"{lat}, {lon}",
            "location": "Austin, Texas, United States",
            "google_domain": "google.com",
            "gl": "us",
            "hl": "en"
        }

        print("Querying Google Maps via SerpAPI...")
        search = GoogleSearch(params)
        results = search.get_dict()

        local_map = results.get("local_map")
        if not local_map or "image" not in local_map:
            print("No map image found in API response")
            return None

        image_url = local_map["image"]
        print("Downloading map image...")
        response = requests.get(image_url)
        if response.status_code == 200:
            map_filename = f'map_{filename}.jpg'
            map_filepath = os.path.join('maps', map_filename)
            os.makedirs(os.path.dirname(map_filepath), exist_ok=True)
            with open(map_filepath, 'wb') as f:
                f.write(response.content)
            print(f"Map image saved to {map_filepath}")
            return map_filepath
        else:
            print(f"Failed to download map image: HTTP {response.status_code}")
            return None
    except Exception as e:
        print(f"Error generating map image: {str(e)}")
        return None

def process_images():
    print("Starting image processing...")
    check_required_env_vars()
    ensure_directories()
    
    if not os.path.exists('photos.db'):
        print("Database not found, creating new database...")
        setup_database.setup_database()

    conn = sqlite3.connect('photos.db')
    cursor = conn.cursor()

    total_images = 0
    processed_images = 0

    # First count total images
    for root, dirs, files in os.walk('photos'):
        for filename in files:
            if filename.lower().endswith(('.jpg', '.jpeg', '.png')):
                total_images += 1

    print(f"Found {total_images} images to process")

    for root, dirs, files in os.walk('photos'):
        for filename in files:
            if filename.lower().endswith(('.jpg', '.jpeg', '.png')):
                processed_images += 1
                print(f"\nProcessing image {processed_images}/{total_images}: {filename}")
                
                file_path = os.path.join(root, filename)
                relative_path = os.path.relpath(file_path, 'photos')
                photographer = os.path.basename(root)
                absolute_path = file_path

                # Copy the image to static/photos directory
                static_photos_path = os.path.join('static/photos', relative_path)
                os.makedirs(os.path.dirname(static_photos_path), exist_ok=True)
                shutil.copy2(absolute_path, static_photos_path)
                print(f"Copied image to {static_photos_path}")

                print("Extracting image metadata...")
                exif_data = get_exif_data(absolute_path)
                date_taken = exif_data.get('DateTimeOriginal')
                if date_taken:
                    print(f"Photo taken on: {date_taken}")

                gps_info = exif_data.get('GPSInfo')
                latitude, longitude = get_lat_lon(gps_info) if gps_info else (None, None)
                if latitude and longitude:
                    print(f"GPS coordinates: {latitude}, {longitude}")

                map_image_path = generate_map_image(latitude, longitude, filename)

                caption = generate_caption(absolute_path, photographer, map_image_path)

                location_name = get_location_name(latitude, longitude) if latitude and longitude else None

                try:
                    cursor.execute('''
                        INSERT INTO photo (file_path, caption, date_taken, latitude, longitude, location_name, exif_data, photographer)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                    ''', (relative_path, caption, date_taken, latitude, longitude, location_name, str(exif_data), photographer))
                    print("Database entry created successfully")
                except sqlite3.Error as e:
                    print(f"Error inserting into database: {str(e)}")

    conn.commit()
    conn.close()
    print("\nImage processing completed successfully!")

if __name__ == '__main__':
    process_images() 