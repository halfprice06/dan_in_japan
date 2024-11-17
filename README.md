# Vacation Photos Website

A personal website that hosts vacation photos with AI-generated captions and an interactive map.

## Features

- **AI-Generated Captions**: Uses the Anthropic Claude API to generate captions for each photo.
- **Interactive Map**: Displays photos on an interactive map based on GPS metadata.
- **Sorting and Filtering**: Allows sorting photos by date and searching by location.
- **Responsive Design**: Accessible and user-friendly across devices.

## Setup Instructions

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

   Create a `.env` file in the project root directory:
   ```env:.env
   ANTHROPIC_API_KEY=your_anthropic_api_key
   SERPAPI_KEY=your_serpapi_key
   ```

5. **Process images:**

   - Place your images in the `photos` directory, organized in subdirectories by photographer (e.g., `photos/Chuck`, `photos/Ashley`).
   - Run the image processing script:
     ```bash
     python process_images.py
     ```

6. **Run the application:**
   ```bash
   uvicorn app:app --reload
   ```

   Access the website at `http://localhost:8000`.

## Dependencies

- Python 3.x
- FastAPI
- Pillow (PIL)
- Anthropics SDK
- SerpAPI SDK
- Leaflet.js
- HTMX
- Tailwind CSS

## License

This project is licensed under the MIT License. 