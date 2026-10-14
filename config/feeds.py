"""
RSS Feed and Web Scraping Configuration
Add your RSS feed URLs and scraping URLs here
Set "type": "rss" for RSS feeds, "type": "scrape" for websites to scrape

content_kind:
  - "news"         → kept 7 days, then deleted by the daily job
  - "opportunity"  → grants/tenders/procurement — kept (not auto-deleted)

Geography: Pakistan + MENA only (not India, Türkiye, etc.).
Theme (opportunities): ESG advisory — energy, climate finance/risk, ESG,
industrials (oil & gas, chemicals, paper, plastics, steel, …).
"""

config = {
    "feeds": [
        {
            "id": "adb-blogs",
            "name": "Asian Development Bank - Blogs",
            "type": "rss",
            "content_kind": "news",
            "url": "https://feeds.feedburner.com/adb_blogs",
            "description": "Asian Development Bank blog posts on development in Asia and the Pacific, covering climate, sustainability, energy, and regional development",
            "keywords": ["asia", "pacific", "development", "adb"]
        },
        {
            "id": "adb-news",
            "name": "ADB - News",
            "type": "rss",
            "content_kind": "news",
            "url": "https://feeds.feedburner.com/adb_news",
            "description": "Asian Development Bank news releases on funding, projects, and initiatives related to climate, sustainability, energy, and development in Asia and the Pacific",
            "keywords": ["asia", "pacific", "development", "adb", "news", "funding", "grants"]
        },
        {
            "id": "adb-invitation-for-bids",
            "name": "ADB - Invitation for Bids",
            "type": "rss",
            "content_kind": "opportunity",
            # Drop notices posted > 1 year ago unless they still have an open bid deadline
            "max_posted_age_days": 365,
            "url": "https://feeds.feedburner.com/adb-invitation-for-bids",
            "description": "Active ADB invitation-for-bids / tender notices (works, goods, and related procurement) with project, country, sector, and status metadata",
            "keywords": ["asia", "pacific", "adb", "tender", "invitation for bids", "procurement", "bid", "icb", "ncb", "energy", "climate", "water", "infrastructure"]
        },
        {
            "id": "adb-advanced-notices",
            "name": "ADB - Advance Contracting Notices",
            "type": "rss",
            "content_kind": "opportunity",
            # ADB leaves Status: Active for years; 6 months without a deadline = not actionable
            "max_posted_age_days": 180,
            "url": "https://feeds.feedburner.com/adb-advanced-notices",
            "description": "ADB advance contracting and early market engagement notices for upcoming projects and procurements",
            "keywords": ["asia", "pacific", "adb", "advance notice", "early market engagement", "procurement", "tender", "contracting"]
        },
        {
            "id": "adb-csrn",
            "name": "ADB - Consulting Services Recruitment Notices",
            "type": "rss",
            "content_kind": "opportunity",
            "max_posted_age_days": 365,
            "url": "https://feeds.feedburner.com/adb-csrn",
            "description": "ADB consulting services recruitment notices (CSRN) for individual consultants and firms on ADB-financed projects",
            "keywords": ["asia", "pacific", "adb", "csrn", "consultant", "consulting", "recruitment", "procurement", "energy", "climate", "environment"]
        },
        {
            "id": "worldbank-news",
            "name": "World Bank News",
            "type": "rss",
            "content_kind": "news",
            # einnews feed often expired/blocked — off by default; enable when URL works
            "enabled": False,
            "url": "https://worldbank.einnews.com/rss/h0gBn63QQVY1p0KW",
            "description": "World Bank news and updates covering development projects, funding, loans, grants, and initiatives related to climate, sustainability, energy, and global development",
            "keywords": ["world bank", "development", "funding", "loan", "grant", "project", "climate", "sustainability"]
        },
        {
            "id": "environment-news",
            "name": "Environment News",
            "type": "rss",
            "content_kind": "news",
            "enabled": False,
            "url": "https://environment.einnews.com/rss/lK_mooUKVG0hy8Z9",
            "description": "Environment news covering pollution, climate change, conservation, environmental protection, and sustainability initiatives",
            "keywords": ["environment", "pollution", "conservation", "environmental protection", "sustainability", "climate"]
        },
        {
            "id": "global-warming-news",
            "name": "Global Warming News",
            "type": "rss",
            "content_kind": "news",
            "enabled": False,
            "url": "https://globalwarming.einnews.com/rss/f0HZ3OvxRbdOOwBX",
            "description": "Global warming and climate change news covering temperature rise, greenhouse gases, climate action, and mitigation strategies",
            "keywords": ["global warming", "climate change", "greenhouse gases", "carbon emissions", "temperature", "mitigation", "adaptation"]
        },
        {
            "id": "worldbank-energy",
            "name": "World Bank - Energy",
            "type": "rss",
            "content_kind": "news",
            "enabled": False,
            "url": "https://blogs.worldbank.org/energy/feed",
            "description": "World Bank blog on energy topics covering renewable energy, energy access, energy efficiency, and sustainable energy solutions",
            "keywords": ["world bank", "energy", "renewable energy", "solar", "wind", "energy access", "energy efficiency", "clean energy"]
        },
        {
            "id": "afdb-procurement",
            "name": "African Development Bank - Procurement Notices",
            "type": "rss",
            "content_kind": "opportunity",
            # Often Cloudflare-blocked — off by default
            "enabled": False,
            "url": "https://www.afdb.org/en/projects-and-operations/procurement.xml",
            "description": "African Development Bank project procurement notices, tenders, RFPs, and bidding opportunities for development projects in Africa, including climate, energy, infrastructure, and sustainability initiatives",
            "keywords": ["africa", "african development bank", "afdb", "procurement", "tender", "rfp", "bid", "contract", "aao", "ami", "ppm", "spn"]
        },
        {
            "id": "afdb-news",
            "name": "African Development Bank - News and Events",
            "type": "rss",
            "content_kind": "news",
            "enabled": False,
            "url": "https://www.afdb.org/en/news-and-events/rss",
            "description": "African Development Bank news releases, press releases, speeches, and events covering funding, grants, projects, climate initiatives, energy, and development in Africa",
            "keywords": ["africa", "african development bank", "afdb", "news", "press release", "funding", "grant", "project", "climate", "energy", "solar", "renewable"]
        },
        {
            "id": "unep-news",
            "name": "UNEP - News and Stories",
            "type": "rss",
            "content_kind": "news",
            "url": "https://www.unep.org/news-and-stories/rss.xml",
            "description": "United Nations Environment Programme news, stories, press releases, and updates on climate change, biodiversity, pollution, and environmental protection",
            "keywords": ["unep", "united nations", "environment", "climate", "biodiversity", "pollution", "sustainability", "conservation", "ecosystem", "green"]
        },
        {
            "id": "paktender",
            "name": "PakTender - Pakistan Tender Portal",
            "type": "scrape",
            "content_kind": "opportunity",
            "url": "https://paktender.com/tenders.php",
            "description": "Pakistan tender portal providing government and private tenders, RFPs, and procurement opportunities across Pakistan. Focuses on infrastructure, construction, and development projects.",
            "keywords": [],
            "skip_ai_filter": True,
            "skip_keyword_filter": True
        },
        {
            "id": "ungm",
            "name": "UNGM - United Nations Global Marketplace",
            "type": "scrape",
            "content_kind": "opportunity",
            "url": "https://www.ungm.org/Public/Notice",
            "description": "United Nations Global Marketplace procurement notices, tenders, RFPs, and bidding opportunities. Includes climate, sustainability, energy, and development projects worldwide.",
            "keywords": ["climate", "energy", "environment", "sustainability", "renewable", "solar", "carbon", "pakistan", "mena"],
            "skip_ai_filter": True,
            "skip_keyword_filter": False
        },
        {
            "id": "propakistani-business",
            "name": "ProPakistani - Business News",
            "type": "rss",
            "content_kind": "news",
            "url": "https://propakistani.pk/category/business/feed/",
            "description": "ProPakistani business news via WordPress RSS (paginated). Business news is allowed; stored for 7 days.",
            "keywords": [],
            "max_age_days": 7,
            "max_pages": 20,
            "skip_ai_filter": True,
            "skip_keyword_filter": True
        },
        {
            "id": "undp-pakistan-procurement",
            "name": "UNDP Pakistan - Procurement Notices",
            "type": "scrape",
            "content_kind": "opportunity",
            "url": "https://www.undp.org/pakistan/procurement",
            "description": "Active UNDP Pakistan procurement notices (RFQs, ICs, construction). Shows Development Area, Title, Location, Reference Number, Posted, Deadline, with direct View links. Only notices whose deadline is today or later.",
            "keywords": [],
            "skip_ai_filter": True
        },
        {
            "id": "gcf-negotiations",
            "name": "Green Climate Fund - Procurement Negotiations",
            "type": "scrape",
            "content_kind": "opportunity",
            "url": "https://iaayou.fa.ocs.oraclecloud.com/fscmUI/faces/NegotiationAbstracts?prcBuId=300000003621906",
            "description": "GCF public procurement / negotiation abstracts (RFP, RFQ). Uses browser scroll to load all rows. Keeps only Status=Active with Close Date today or later.",
            "keywords": [],
            "skip_ai_filter": True,
            "skip_keyword_filter": True
        },
        {
            "id": "secp-notifications",
            "name": "SECP - Laws & Notifications",
            "type": "scrape",
            "content_kind": "opportunity",
            "url": "https://www.secp.gov.pk/laws/notifications/",
            "description": "Securities & Exchange Commission of Pakistan - legal notifications (date, title, downloadable file). Requires Playwright/Chromium on the server (Cloudflare blocks plain HTTP).",
            "keywords": [],
            "skip_ai_filter": True,
            "skip_keyword_filter": True
        }
    ]
}


def news_source_ids() -> list:
    """Source ids marked as news (7-day retention)."""
    return [f["id"] for f in config["feeds"] if f.get("content_kind") == "news"]


def stamp_content_kind(items: list, source_configs: list = None) -> list:
    """Attach content_kind from feed config onto each item (for DB retention)."""
    configs = source_configs if source_configs is not None else config["feeds"]
    by_id = {f["id"]: f.get("content_kind", "opportunity") for f in configs}
    for item in items:
        source = item.get("source") or {}
        sid = source.get("id") if isinstance(source, dict) else None
        item["content_kind"] = by_id.get(sid, item.get("content_kind") or "opportunity")
    return items
