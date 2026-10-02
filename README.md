# News Tracker - RSS Feed & Web Scraping Backend (FastAPI)

Backend API for fetching and filtering content from RSS feeds and web scraping related to climate, sustainability, and energy funding opportunities (focused on Pakistan and MENA region).

## Features

- ✅ Fetch multiple RSS feeds in parallel (async)
- ✅ Web scraping using Crawl4ai for websites without RSS feeds
- ✅ **LLM-based extraction** (Google Gemini) - Extract structured data, classify opportunities, score actionability
- ✅ **AI-based content filtering** (Google Gemini) - Ensures content is only related to specific climate/sustainability topics
- ✅ Automatic keyword filtering for climate/sustainability/energy content
- ✅ Support for Pakistan and MENA region keywords
- ✅ RESTful API endpoints with FastAPI
- ✅ CORS enabled for frontend integration
- ✅ Pagination support
- ✅ Automatic API documentation (Swagger UI)

## Setup

1. **Create a virtual environment (recommended):**
   ```bash
   python -m venv venv
   
   # On Windows:
   venv\Scripts\activate
   
   # On macOS/Linux:
   source venv/bin/activate
   ```

2. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

3. **Setup Crawl4ai (for web scraping):**
   After installing dependencies, you need to set up browser binaries for Crawl4ai:
   ```bash
   crawl4ai-setup
   ```
   
   This will download browser binaries (~200-300MB). Verify installation:
   ```bash
   crawl4ai-doctor
   ```
   
   See `CRAWL4AI_SETUP.md` for detailed setup instructions.

4. **Setup Google Gemini API Key (Required for AI filtering):**
   
   **Easiest Method:** Edit the startup script (`start_backend.bat` or `start_backend.ps1`) and replace the API key with your actual Gemini API key.
   
   **Alternative Methods:**
   ```bash
   # Windows PowerShell
   $env:GEMINI_API_KEY="your-gemini-api-key-here"
   
   # Windows Command Prompt
   set GEMINI_API_KEY=your-gemini-api-key-here
   
   # Linux/Mac
   export GEMINI_API_KEY="your-gemini-api-key-here"
   ```
   
   **AI Filtering Configuration (Optional):**
   ```bash
   # Enable/disable AI filtering (default: true)
   $env:ENABLE_AI_FILTERING="true"  # or "false" to disable
   
   # Choose AI model (default: gemini-2.5-flash)
   $env:AI_FILTER_MODEL="gemini-2.5-flash"  # or "gemini-2.0-flash"
   
   # Batch size for processing (default: 5)
   $env:AI_FILTER_BATCH_SIZE="5"  # Process 5 items concurrently
   ```
   
   📖 Get your free Gemini API key at: [Google AI Studio](https://aistudio.google.com/apikey)

5. **Configure RSS feeds and scraping sources:**
   - Open `config/feeds.py`
   - Add your RSS feed URLs (with `"type": "rss"`)
   - Add websites to scrape (with `"type": "scrape"`)

6. **Start the server:**
   ```bash
      start_backend.bat
        start_frontend.bat
   ```
   
   Or using uvicorn directly:
   ```bash
   uvicorn main:app --reload --port 3001
   ```

7. **Server runs on:** `http://localhost:3001`
   - **API Documentation:** `http://localhost:3001/docs` (Swagger UI)
   - **Alternative Docs:** `http://localhost:3001/redoc`

## API Endpoints

### GET `/api/health`
Health check endpoint.

**Response:**
```json
{
  "status": "ok",
  "message": "RSS Feed API is running"
}
```

### GET `/api/feeds`
Get all filtered RSS feed items.

**Query Parameters:**
- `limit` (optional): Number of items to return (default: 50, max: 200)
- `offset` (optional): Number of items to skip (default: 0)

**Example:** `/api/feeds?limit=20&offset=0`

**Response:**
```json
{
  "success": true,
  "total": 150,
  "count": 20,
  "offset": 0,
  "limit": 20,
  "data": [
    {
      "id": "unique-item-id",
      "title": "Climate Grant Opportunity",
      "link": "https://example.com/grant",
      "description": "Funding available for...",
      "content": "Full content...",
      "pubDate": "2024-01-15T10:00:00",
      "author": "Source Name",
      "categories": ["climate", "funding"],
      "source": {
        "id": "source-1",
        "name": "Source Name",
        "url": "https://source.com/feed.xml"
      },
      "image": "https://example.com/image.jpg"
    }
  ]
}
```

### GET `/api/feeds/source/{source_id}`
Get feeds from a specific source.

**Example:** `/api/feeds/source/example-1`

**Response:**
```json
{
  "success": true,
  "source": "Example Climate News",
  "count": 10,
  "data": [...]
}
```

### GET `/api/sources`
Get list of all configured RSS feed sources.

**Response:**
```json
{
  "success": true,
  "count": 3,
  "data": [
    {
      "id": "example-1",
      "name": "Example Climate News",
      "url": "https://example.com/rss-feed.xml",
      "description": "Example RSS feed for climate news"
    }
  ]
}
```

## Adding RSS Feeds and Scraping Sources

Edit `config/feeds.py` and add your feed configurations:

**For RSS Feeds:**
```python
{
    "id": "unique-source-id",
    "name": "Source Display Name",
    "type": "rss",  # RSS feed
    "url": "https://source.com/rss-feed.xml",
    "description": "Description of the source",
    "keywords": ["optional", "specific", "keywords"]  # Additional keywords for this source
}
```

**For Web Scraping:**
```python
{
    "id": "unique-scrape-id",
    "name": "Website to Scrape",
    "type": "scrape",  # Web scraping
    "url": "https://example.com/news",
    "description": "Website to scrape for climate news",
    "keywords": ["climate", "sustainability", "funding"]
}
```

## Content Filtering

The system uses a two-stage filtering process:

### 1. Keyword Filtering (First Stage)
Initial filtering based on keywords related to:
- Climate change and environment
- Sustainability
- Energy (renewable, clean energy, etc.)
- Funding opportunities (grants, tenders, RFPs)
- Pakistan and MENA region

You can add source-specific keywords in the feed configuration.

### 2. AI Filtering (Second Stage - Optional)
After keyword filtering, content is further filtered using AI (Google Gemini) to ensure it's **only** related to these specific topics:

- Climate change
- Sustainability
- Sustainable development
- Decarbonization
- Carbon emissions
- Climate resilience
- Environmental impact
- Green transition
- Renewable energy
- Solar power
- Wind energy
- Clean energy
- Energy transition
- Power generation
- ESG
- Sustainable finance
- Green finance
- Climate finance
- Impact investing
- Carbon credits

**AI Filtering Benefits:**
- ✅ More accurate filtering - understands context, not just keywords
- ✅ Filters out tangentially related content
- ✅ Only keeps content directly related to climate/sustainability topics
- ✅ Uses Google Gemini free tier (generous free limits)

**To enable AI filtering:**
1. Set `GEMINI_API_KEY` environment variable
2. AI filtering is enabled by default when API key is set
3. To disable: set `ENABLE_AI_FILTERING=false`

**Note:** If AI filtering is disabled or API key is not set, the system falls back to keyword filtering only.

## Frontend Integration

The API is CORS-enabled, so you can call it from any frontend:

```javascript
// Fetch all feeds
const response = await fetch('http://localhost:3001/api/feeds?limit=20');
const data = await response.json();

// Fetch from specific source
const response = await fetch('http://localhost:3001/api/feeds/source/example-1');
const data = await response.json();

// Get available sources
const response = await fetch('http://localhost:3001/api/sources');
const data = await response.json();
```

## API Documentation

FastAPI automatically generates interactive API documentation:
- **Swagger UI:** http://localhost:3001/docs
- **ReDoc:** http://localhost:3001/redoc

## Technologies

- Python 3.8+
- FastAPI
- feedparser (for RSS feeds)
- Crawl4ai (for web scraping)
- BeautifulSoup4 (for HTML parsing)
- uvicorn
- asyncio (for concurrent fetching)

## Project Structure

```
.
├── main.py                 # FastAPI application and routes
├── requirements.txt        # Python dependencies
├── CRAWL4AI_SETUP.md      # Crawl4ai setup instructions
├── config/
│   └── feeds.py           # RSS feed and scraping source configuration
├── services/
│   ├── rss_service.py        # RSS fetching and parsing logic
│   ├── scraper_service.py    # Web scraping using Crawl4ai
│   ├── unified_service.py    # Unified service for RSS + scraping + AI filtering
│   ├── content_filter.py    # Keyword-based content filtering logic
│   └── ai_content_filter.py # AI-based content filtering using Google Gemini
└── README.md
```
