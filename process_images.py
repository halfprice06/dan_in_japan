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

dotenv.load_dotenv()

def get_exif_data(image_path):
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
    except AttributeError:
        pass  # Images might not have EXIF data
    return exif_data

def get_lat_lon(gps_info):
    if not gps_info:
        return None, None

    def convert_to_degrees(value):
        d = value[0].numerator / value[0].denominator
        m = value[1].numerator / value[1].denominator
        s = value[2].numerator / value[2].denominator
        return d + (m / 60.0) + (s / 3600.0)

    lat = convert_to_degrees(gps_info['GPSLatitude'])
    lon = convert_to_degrees(gps_info['GPSLongitude'])

    if gps_info['GPSLatitudeRef'] != 'N':
        lat = -lat
    if gps_info['GPSLongitudeRef'] != 'E':
        lon = -lon

    return lat, lon

def generate_caption(image_path, photographer, map_image_path=None):
    # Use the Anthropic Claude API to generate a caption
    # Initialize the Anthropic client
    anthropic_client = Anthropic(api_key=os.environ['ANTHROPIC_API_KEY'])

    system_prompt = f"""
    You are reviewing vacation photos to create captions for a website about the vacation recently taken by Chuck, Ashley, Daniel, and Christina. Chuck and Ashley are married, Daniel and Christina are married.  
    This photo was taken by {photographer}. Write the caption from a third person perspective referencing the photographer by name. Add some charm and personality to the caption to make it interesting from the reader's perspective and help contexualize what they are looking at. You can provide some context about the location, history, people, anything that's relevant to the photo. Don't hallucinate. Don't make up things that are not in the photo or details about the photographer's life. Don't make assumptions about anything you see in the photos. 

    Keep your answer to about one or two sentences. 

    """

    messages_content = []

    # Include the map image if available
    if map_image_path is not None:
        try:
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
            # Handle errors if necessary
            pass

    # Process the input image
    try:
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
        # Handle errors if necessary
        pass

    # Prepare the message with all images and texts
    messages = [
        {
            'role': 'user',
            'content': messages_content
        }
    ]

    # Send the request to Claude's API
    response = anthropic_client.messages.create(
        model='claude-3-5-sonnet-20241022',  # Use the appropriate model
        messages=messages,
        system=system_prompt,
        max_tokens=500,
        temperature=0
    )

    # Extract the caption from the response
    caption = ' '.join(block.text for block in response.content if block.type == 'text').strip()
    return caption

def get_location_name(lat, lon):
    url = 'https://nominatim.openstreetmap.org/reverse'
    params = {
        'lat': lat,
        'lon': lon,
        'format': 'jsonv2'
    }
    response = requests.get(url, params=params)
    if response.status_code == 200:
        data = response.json()
        return data.get('display_name')
    else:
        return None

def generate_map_image(lat, lon, filename):
    if lat is None or lon is None:
        return None

    params = {
        "api_key": os.environ['SERP_API_KEY'],  # Retrieved from environment variables
        "engine": "google",
        "q": f"{lat}, {lon}",
        "location": "Austin, Texas, United States",
        "google_domain": "google.com",
        "gl": "us",
        "hl": "en"
    }

    search = GoogleSearch(params)
    results = search.get_dict()

    local_map = results.get("local_map")
    if not local_map or "image" not in local_map:
        return None

    image_url = local_map["image"]
    response = requests.get(image_url)
    if response.status_code == 200:
        map_filename = f'map_{filename}.jpg'
        map_filepath = os.path.join('maps', map_filename)
        # Ensure the 'maps' directory exists
        os.makedirs(os.path.dirname(map_filepath), exist_ok=True)
        with open(map_filepath, 'wb') as f:
            f.write(response.content)
        return map_filepath
    else:
        return None

def process_images():
    if not os.path.exists('photos.db'):
        setup_database.setup_database()

    conn = sqlite3.connect('photos.db')
    cursor = conn.cursor()

    for root, dirs, files in os.walk('photos'):
        for filename in files:
            if filename.lower().endswith(('.jpg', '.jpeg', '.png')):
                # Get the full path to the image
                file_path = os.path.join(root, filename)
                # Adjust the relative path if necessary
                relative_path = os.path.relpath(file_path, 'static')

                # Determine who took the photo based on the subdirectory name
                photographer = os.path.basename(root)

                absolute_path = file_path

                exif_data = get_exif_data(absolute_path)
                date_taken = exif_data.get('DateTimeOriginal')

                gps_info = exif_data.get('GPSInfo')
                latitude, longitude = get_lat_lon(gps_info) if gps_info else (None, None)

                # Generate a map image based on latitude and longitude
                map_image_path = generate_map_image(latitude, longitude, filename)

                # Pass photographer and map image to generate_caption
                caption = generate_caption(absolute_path, photographer, map_image_path)

                # Insert data into the database, including the photographer
                cursor.execute('''
                    INSERT INTO photo (file_path, caption, date_taken, latitude, longitude, exif_data, photographer)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                ''', (relative_path, caption, date_taken, latitude, longitude, str(exif_data), photographer))

    conn.commit()
    conn.close()

if __name__ == '__main__':
    process_images() 