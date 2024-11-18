# Vacation Photos Website

A personal website that hosts vacation photos with AI-generated captions and an interactive map.

## Features

- **AI-Generated Captions**: Uses the Anthropic Claude API to generate captions for each photo.
- **Interactive Map**: Displays photos on an interactive map based on GPS metadata.
- **Sorting and Filtering**: Allows sorting photos by date and searching by location.
- **Points of Interest**: AI extracts notable cultural and historical references from each photo.

## Local Development

### Prerequisites

- Python 3.x
- An Anthropic API key (for Claude)
- A SerpAPI key (for map generation)
- Photos with EXIF data (GPS coordinates recommended)

### Setup Instructions

1. **Clone the repository:**
   ```bash
   git clone https://github.com/halfprice06/dan_in_japan.git
   cd dan_in_japan
   ```

2. **Create a virtual environment:**
   ```bash
   python3 -m venv venv
   source venv/bin/activate  # On Windows use `venv\Scripts\activate`
   ```

3. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

4. **Set up environment variables:**

   - Copy the `.env.template` file to `.env`:
     ```bash
     cp .env.template .env
     ```
     
   - Open `.env` and fill in your API keys:
     ```env
     ANTHROPIC_API_KEY=your_anthropic_api_key
     SERP_API_KEY=your_serpapi_key
     ```

5. **Organize your photos:**

   Place your photos in the `photos` directory. You can organize them in subdirectories by photographer:
   ```
   photos/
   ├── Chuck/
   │   ├── temple.jpg
   │   └── garden.jpg
   ├── Ashley/
   │   ├── market.jpg
   │   └── shrine.jpg
   ├── dan_photo1.jpg
   ├── christina_photo2.jpg
   ```

   The name of each subdirectory will be used as the photographer's name in the captions.

   Make sure to edit the system prompt and instructions in `process_images.py` to customize the captions and metadata extraction so the AI writes captions in the style you prefer. 

6. **Process images and generate captions:**
   ```bash
   python process_images.py
   ```

   This script will:
   - Extract EXIF data (date, GPS coordinates)
   - Generate map images using SerpAPI
   - Generate captions using Claude
   - Extract points of interest
   - Copy photos to the static directory
   - Store all data in the SQLite database

7. **Run the development server:**
   ```bash
   uvicorn app:app --reload
   ```

   Visit `http://localhost:8000` to view your photo gallery.

## Project Structure

- `app.py`: The main FastAPI application.
- `process_images.py`: Script to process images and generate captions.
- `setup_database.py`: Script to set up the SQLite database.
- `templates/`: Contains the Jinja2 templates for the web pages.
- `static/`: Contains static files like CSS, JavaScript, and images.
- `photos/`: Place your photos here to be processed.
- `requirements.txt`: Python dependencies required for the project.
- `.env.template`: Template for the environment variables.
- `README.md`: Documentation and setup instructions.

## Dependencies

- **Python Packages:**
  - Python 3.x
  - FastAPI
  - Pillow (PIL)
  - `anthropic` SDK
  - `serpapi` SDK
  - `python-dotenv`
  - `instructor` library
  - `uvicorn`
  - `Jinja2`

- **JavaScript and CSS Libraries (Included via CDN):**
  - Leaflet.js and Leaflet.markercluster plugin
  - Tailwind CSS

## License

This project is licensed under the MIT License. The copyright to the photos and captions hosted online at daninjapan.net belong to their respective creators. 