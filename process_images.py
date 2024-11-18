import os
import sqlite3
from PIL import Image
from PIL.ExifTags import TAGS, GPSTAGS
import requests
from anthropic import Anthropic, APIError
import base64
from serpapi import GoogleSearch
import dotenv
import setup_database
from io import BytesIO
import sys
import shutil
import instructor
from pydantic import BaseModel
from typing import List
import json
import time

dotenv.load_dotenv()

class PointOfInterest(BaseModel):
    name: str
    description: str

class PhotoAnalysis(BaseModel):
    caption: str
    points_of_interest: List[PointOfInterest]

def ensure_directories():
    """Create necessary directories if they don't exist"""
    directories = ['static/photos', 'maps']
    for directory in directories:
        os.makedirs(directory, exist_ok=True)
        print(f"Ensured directory exists: {directory}")

def check_required_env_vars():
    """Check for required env vars and format system prompt if needed"""
    required_vars = ['ANTHROPIC_API_KEY', 'SERP_API_KEY']
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

def get_processed_files():
    """Get list of already processed files from database"""
    conn = sqlite3.connect('photos.db')
    cursor = conn.cursor()
    cursor.execute('SELECT file_path FROM photo')
    processed = {row[0] for row in cursor.fetchall()}
    conn.close()
    return processed

def generate_caption(image_path, photographer, map_image_path=None, location_name=None):
    """Modified to include retry logic"""
    max_retries = 3
    base_delay = 5  # seconds
    
    for attempt in range(max_retries):
        try:
            print(f"Generating caption and points of interest for {image_path}...")
            # Initialize Anthropic client with Instructor
            anthropic_client = instructor.from_anthropic(
                Anthropic(api_key=os.environ['ANTHROPIC_API_KEY'])
            )

            system_prompt = """Don't worry about formalities.

            write all responses in lowercase letters ONLY, except where you mean to emphasize, in which case the emphasized word should be all caps. Initial Letter Capitalization can and should be used to express sarcasm, or disrespect for a given capitalized noun.

            """

            # Get EXIF data for date/time
            exif_data = get_exif_data(image_path)
            date_taken = exif_data.get('DateTimeOriginal', 'unknown date/time')

            # Add location context to the instruction text
            location_context = f" The photo was taken in {location_name}." if location_name else ""

            # Create the instruction text that was previously in system prompt
            instruction_text = f"""
            You are creating captions for a travel blog called 'Dan in Japan' about a vacation 
            taken by two couples in October 2024. Write natural, conversational captions in all 
            lowercase that avoid clichés and overwrought emotional descriptions.

            You are being given a photo from the trip along with a screenshot of a map showing 
            where the photo was taken using the serpAPI from the photo coordinates. The items identified in the map are for context only, it doesn't mean that the photo is exactly of something shown in the map.

           The photographer was {photographer} and the date it was taken was {date_taken} at {location_context}.

           If Chuck took the photo, then it's him and his wife Ashley. If Daniel took the photo, then it's him and his wife Christina, and vice-versa.

            Trip details:
            - First time in Japan
            - 10 days during second half of October 2024, October 19 through Nov. 1. 
            - Visited Tokyo, Osaka, and Kyoto
            - Stayed in:
            - Tokyo (Airbnb)
            - Osaka (traditional Japanese house)
            - Kyoto (western hotel)
            - Any photos you see taken outside of Tokyo, Osaka, or Kyoto are probably on the bullet train.

            Caption guidelines:
            - Always identify the people in the photo by name
            - Write as if texting a friend - casual and genuine
            - Avoid cliché travel writing phrases like "capturing the moment" or "radiating excitement"
            - No exclamation points unless absolutely necessary
            - Skip obvious details (we can see they're smiling/happy/etc)
            - Keep it to 1-2 short sentences
            - For US photos (pre/post trip), mention that it's from before/after the Japan trip

            Don't:
            - Use flowery or emotional language
            - Describe obvious visual elements
            - Add fictional details
            - Assume activities from map locations

            Your Points of Interest should be notable locations, cultural elements, or historical references that warrant further explanation in a modal window. 

            Skip mundane points of interest.

            Each point of interest you generate is going to be clickable and its going to open a google search for the phrase you pick, so choose things that can be googled and are japan related. 

            Here are the images to analyze:
            """

            print(instruction_text)

            messages_content = [{'type': 'text', 'text': instruction_text}]

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
                return "Error generating caption", []

            print("Sending request to Claude API...")
            response = anthropic_client.messages.create(
                model='claude-3-5-sonnet-latest',
                max_tokens=1000,
                messages=[{
                    'role': 'user',
                    'content': messages_content
                }],
                system=system_prompt,
                response_model=PhotoAnalysis,
                temperature=0
            )

            return response.caption, json.dumps([poi.model_dump() for poi in response.points_of_interest])
            
        except APIError as e:
            if e.status_code == 429:  # Rate limit error
                if attempt < max_retries - 1:
                    delay = base_delay * (2 ** attempt)  # Exponential backoff
                    print(f"Rate limited. Waiting {delay} seconds before retry {attempt + 1}/{max_retries}")
                    time.sleep(delay)
                    continue
            print(f"API error after {attempt + 1} attempts: {str(e)}")
            raise
        except Exception as e:
            print(f"Error generating caption and points of interest: {str(e)}")
            return "Error generating caption", "[]"

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
    
    print("Setting up database...")
    setup_database.setup_database()
    
    # Get already processed files
    processed_files = get_processed_files()
    print(f"Found {len(processed_files)} already processed files")

    conn = sqlite3.connect('photos.db')
    cursor = conn.cursor()

    total_images = 0
    processed_images = 0

    # Count only unprocessed images
    for root, dirs, files in os.walk('photos'):
        for filename in files:
            if filename.lower().endswith(('.jpg', '.jpeg', '.png')):
                relative_path = os.path.relpath(os.path.join(root, filename), 'photos')
                if relative_path not in processed_files:
                    total_images += 1

    print(f"Found {total_images} new images to process")

    try:
        for root, dirs, files in os.walk('photos'):
            for filename in files:
                if filename.lower().endswith(('.jpg', '.jpeg', '.png')):
                    file_path = os.path.join(root, filename)
                    relative_path = os.path.relpath(file_path, 'photos')
                    
                    # Skip if already processed
                    if relative_path in processed_files:
                        print(f"Skipping already processed image: {filename}")
                        continue
                        
                    processed_images += 1
                    print(f"\nProcessing image {processed_images}/{total_images}: {filename}")
                    
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

                    location_name = get_location_name(latitude, longitude) if latitude and longitude else None
                    map_image_path = generate_map_image(latitude, longitude, filename)

                    try:
                        caption, points_of_interest_json = generate_caption(
                            absolute_path, 
                            photographer, 
                            map_image_path,
                            location_name
                        )
                        location_name = get_location_name(latitude, longitude) if latitude and longitude else None
                        
                        # First insert the photo
                        cursor.execute('''
                            INSERT INTO photo (
                                file_path, caption, date_taken, 
                                latitude, longitude, location_name, exif_data, photographer
                            )
                            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                        ''', (
                            relative_path, caption, date_taken, 
                            latitude, longitude, location_name, str(exif_data), photographer
                        ))
                        
                        # Get the photo_id of the just-inserted photo
                        photo_id = cursor.lastrowid
                        
                        # Parse the points of interest JSON and insert each point
                        points_of_interest = json.loads(points_of_interest_json)
                        for poi in points_of_interest:
                            cursor.execute('''
                                INSERT INTO point_of_interest (
                                    photo_id, name, description
                                )
                                VALUES (?, ?, ?)
                            ''', (
                                photo_id, poi['name'], poi['description']
                            ))
                        
                        print("Database entries created successfully")
                    except sqlite3.Error as e:
                        print(f"Error inserting into database: {str(e)}")

                    conn.commit()  # Commit after each successful image
                    
    except Exception as e:
        print(f"Error during processing: {str(e)}")
        conn.commit()  # Ensure we save progress even on error
        raise
    finally:
        conn.close()
        print("\nImage processing completed!")

if __name__ == '__main__':
    process_images() 