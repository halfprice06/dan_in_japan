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

   Create a `.env` file in the project root directory. You'll need three key variables:
   ```env
   ANTHROPIC_API_KEY=your_anthropic_api_key
   SERP_API_KEY=your_serpapi_key
   SYSTEM_PROMPT=your_customized_prompt
   ```

   The SYSTEM_PROMPT is crucial for getting good captions. It should include:
   - Context about the people in the photos
   - Details about the trip/vacation
   - Any specific instructions for the AI
   - The special placeholder {photographer} which gets replaced with the name of the folder containing each photo

   Example SYSTEM_PROMPT:
   ```
   You are reviewing vacation photos taken during our family trip to Japan. The group includes [describe people]. This photo was taken by {photographer}. Write a caption that describes what you see and provides relevant cultural or historical context. The trip took place in [time period] and we visited [locations]. Keep descriptions concise but informative.
   ```

   The {photographer} placeholder is automatically replaced with the name of the subfolder containing each photo. For example:
   - Photos in `/photos/Chuck/` will have "Chuck" as the photographer
   - Photos in `/photos/Ashley/` will have "Ashley" as the photographer

5. **Organize your photos:**

   - Create subdirectories in the `photos` directory for each photographer
   - The name of each subdirectory will be used as the photographer's name
   - Example structure:
     ```
     photos/
     ├── Chuck/
     │   ├── temple.jpg
     │   └── garden.jpg
     ├── Ashley/
     │   ├── market.jpg
     │   └── shrine.jpg
     ```

6. **Process images:**
   ```bash
   python process_images.py
   ```

7. **Run the application:**
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