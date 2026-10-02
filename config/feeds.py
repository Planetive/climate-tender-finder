"""
RSS Feed and Web Scraping Configuration
Add your RSS feed URLs and scraping URLs here
Set "type": "rss" for RSS feeds, "type": "scrape" for websites to scrape
"""

config = {
    "feeds": [
        {
            "id": "adb-blogs",
            "name": "Asian Development Bank - Blogs",
            "type": "rss",
            "url": "https://www.adb.org/rss/blogs",
            "description": "Asian Development Bank blog posts on development in Asia and the Pacific, covering climate, sustainability, energy, and regional development",
            "keywords": ["asia", "pacific", "development", "adb"]
        },
        {
            "id": "adb-news",
            "name": "ADB - News",
            "type": "rss",
            "url": "https://www.adb.org/rss/news",
            "description": "Asian Development Bank news releases on funding, projects, and initiatives related to climate, sustainability, energy, and development in Asia and the Pacific",
            "keywords": ["asia", "pacific", "development", "adb", "news", "funding", "grants"]
        },
        {
            "id": "adb-procurement",
            "name": "ADB - Procurement Notices",
            "type": "rss",
            "url": "https://www.adb.org/rss/procurement-notices",
            "description": "Asian Development Bank procurement notices, tenders, RFPs, and bidding opportunities for projects related to climate, sustainability, energy, and infrastructure development",
            "keywords": ["asia", "pacific", "development", "adb", "procurement", "tender", "rfp", "bid", "contract", "icb", "ncb"]
        },
        {
            "id": "worldbank-news",
            "name": "World Bank News",
            "type": "rss",
            "url": "https://worldbank.einnews.com/rss/h0gBn63QQVY1p0KW",
            "description": "World Bank news and updates covering development projects, funding, loans, grants, and initiatives related to climate, sustainability, energy, and global development",
            "keywords": ["world bank", "development", "funding", "loan", "grant", "project", "climate", "sustainability"]
        },
        {
            "id": "environment-news",
            "name": "Environment News",
            "type": "rss",
            "url": "https://environment.einnews.com/rss/lK_mooUKVG0hy8Z9",
            "description": "Environment news covering pollution, climate change, conservation, environmental protection, and sustainability initiatives",
            "keywords": ["environment", "pollution", "conservation", "environmental protection", "sustainability", "climate"]
        },
        {
            "id": "global-warming-news",
            "name": "Global Warming News",
            "type": "rss",
            "url": "https://globalwarming.einnews.com/rss/f0HZ3OvxRbdOOwBX",
            "description": "Global warming and climate change news covering temperature rise, greenhouse gases, climate action, and mitigation strategies",
            "keywords": ["global warming", "climate change", "greenhouse gases", "carbon emissions", "temperature", "mitigation", "adaptation"]
        },
        {
            "id": "worldbank-energy",
            "name": "World Bank - Energy",
            "type": "rss",
            "url": "https://blogs.worldbank.org/energy/feed",
            "description": "World Bank blog on energy topics covering renewable energy, energy access, energy efficiency, and sustainable energy solutions",
            "keywords": ["world bank", "energy", "renewable energy", "solar", "wind", "energy access", "energy efficiency", "clean energy"]
        },
        {
            "id": "afdb-procurement",
            "name": "African Development Bank - Procurement Notices",
            "type": "rss",
            "url": "https://www.afdb.org/en/projects-and-operations/procurement.xml",
            "description": "African Development Bank project procurement notices, tenders, RFPs, and bidding opportunities for development projects in Africa, including climate, energy, infrastructure, and sustainability initiatives",
            "keywords": ["africa", "african development bank", "afdb", "procurement", "tender", "rfp", "bid", "contract", "aao", "ami", "ppm", "spn"]
        },
        {
            "id": "afdb-news",
            "name": "African Development Bank - News and Events",
            "type": "rss",
            "url": "https://www.afdb.org/en/news-and-events/rss",
            "description": "African Development Bank news releases, press releases, speeches, and events covering funding, grants, projects, climate initiatives, energy, and development in Africa",
            "keywords": ["africa", "african development bank", "afdb", "news", "press release", "funding", "grant", "project", "climate", "energy", "solar", "renewable"]
        },
        {
            "id": "unep-news",
            "name": "UNEP - News and Stories",
            "type": "rss",
            "url": "https://www.unep.org/news-and-stories/rss.xml",
            "description": "United Nations Environment Programme news, stories, press releases, and updates on climate change, biodiversity, pollution, and environmental protection",
            "keywords": ["unep", "united nations", "environment", "climate", "biodiversity", "pollution", "sustainability", "conservation", "ecosystem", "green"]
        },
        {
            "id": "paktender",
            "name": "PakTender - Pakistan Tender Portal",
            "type": "scrape",
            "url": "https://paktender.com/tenders.php",
            "description": "Pakistan tender portal providing government and private tenders, RFPs, and procurement opportunities across Pakistan. Focuses on infrastructure, construction, and development projects.",
            "keywords": ["pakistan", "tender", "procurement", "rfp", "bid", "government", "infrastructure", "construction", "development", "civil works", "energy", "solar", "renewable", "climate", "sustainability"]
        },
        {
            "id": "ungm",
            "name": "UNGM - United Nations Global Marketplace",
            "type": "scrape",
            "url": "https://www.ungm.org/Public/Notice",
            "description": "United Nations Global Marketplace procurement notices, tenders, RFPs, and bidding opportunities. Includes climate, sustainability, energy, and development projects worldwide.",
            "keywords": ["united nations", "un", "ungm", "procurement", "tender", "rfp", "bid", "contract", "climate", "sustainability", "energy", "renewable", "environment", "development", "pakistan", "mena"]
        },
        {
            "id": "propakistani-business",
            "name": "ProPakistani - Business News",
            "type": "scrape",
            "url": "https://propakistani.pk/category/business/",
            "description": "ProPakistani business news - all articles from business category.",
            "keywords": [],
            "skip_ai_filter": True
        },
        {
            "id": "undp-pakistan-procurement",
            "name": "UNDP Pakistan - Procurement Notices",
            "type": "scrape",
            "url": "https://www.undp.org/pakistan/procurement",
            "description": "Active UNDP Pakistan procurement notices (RFQs, ICs, construction). Shows Development Area, Title, Location, Reference Number, Posted, Deadline, with direct View links. Only notices whose deadline is today or later.",
            "keywords": [],
            "skip_ai_filter": True
        },
        {
            "id": "secp-notifications",
            "name": "SECP - Laws & Notifications",
            "type": "scrape",
            "url": "https://www.secp.gov.pk/laws/notifications/",
            "description": "Securities & Exchange Commission of Pakistan - legal notifications (date, title, downloadable file).",
            "keywords": [],
            "skip_ai_filter": True
        }
    ]
}
