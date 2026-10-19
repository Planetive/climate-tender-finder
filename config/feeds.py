"""
RSS Feed and Web Scraping Configuration
Add your RSS feed URLs and scraping URLs here
Set "type": "rss" for RSS feeds, "type": "scrape" for websites to scrape

content_kind:
  - "news"         → last NEWS_LOOKBACK_DAYS by publish date; purged from DB after that window
  - "opportunity"  → grants/tenders/procurement — longer windows; not auto-deleted by news purge

Geography: Pakistan + MENA only (not India, Türkiye, etc.).
Theme (opportunities): ESG advisory — energy, climate finance/risk, ESG,
industrials (oil & gas, chemicals, paper, plastics, steel, …).
"""

# News only: rolling window (daily ingest keeps last 7 days stored).
# Grants/tenders do NOT use this — they keep their own deadline / max_posted_age rules.
NEWS_LOOKBACK_DAYS = 7

config = {
    "feeds": [
        {
            "id": "adb-blogs",
            "name": "Asian Development Bank - Blogs",
            "type": "rss",
            "content_kind": "news",
            "max_age_days": 7,
            "url": "https://feeds.feedburner.com/adb_blogs",
            "description": "Asian Development Bank blog posts on development in Asia and the Pacific, covering climate, sustainability, energy, and regional development",
            "keywords": ["asia", "pacific", "development", "adb"]
        },
        {
            "id": "adb-news",
            "name": "ADB - News",
            "type": "rss",
            "content_kind": "news",
            "max_age_days": 7,
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
            # Same filters as the All News listing page (topics + regions + Press Release).
            # Page is JS; we hit search.worldbank.org/api/v2/news with those facets.
            "type": "scrape",
            "content_kind": "news",
            "enabled": True,
            "url": (
                "https://www.worldbank.org/en/news/all"
                "?topic_exact=Energy&topic_exact=Climate+Change&topic_exact=Renewable+Energy"
                "&topic_exact=Fiscal+Policy+%26+Growth&topic_exact=Financial+Services+Sector"
                "&topic_exact=Environment&topic_exact=Energy+and+Extractives"
                "&topic_exact=Energy+Efficiency&topic_exact=Farming+and+Agribusiness"
                "&topic_exact=Energy+Access&topic_exact=Financial+Infrastructure"
                "&topic_exact=Data+and+AI&topic_exact=Investment+Climate"
                "&topic_exact=Financial+Inclusion&topic_exact=Poverty"
                "&topic_exact=Digital+and+AI&topic_exact=Trade"
                "&topic_exact=Small+and+Medium+Enterprises+Finance"
                "&displayconttype_exact=Press+Release&lang_exact=English"
                "&admreg_exact=South+Asia&admreg_exact=Europe+and+Central+Asia"
                "&admreg_exact=Middle+East%2C+North+Africa%2C+Afghanistan+%26+Pakistan"
            ),
            "description": "World Bank Press Releases filtered like the All News page (energy/climate/finance topics; South Asia, ECA, MENAAP).",
            "keywords": ["world bank", "climate", "energy", "pakistan", "sustainability"],
            "max_age_days": 7,
            "api_rows": 30,
            "skip_keyword_filter": True,
            "wb_display_type": "Press Release",
            "wb_topics": [
                "Energy",
                "Climate Change",
                "Renewable Energy",
                "Fiscal Policy & Growth",
                "Financial Services Sector",
                "Environment",
                "Energy and Extractives",
                "Energy Efficiency",
                "Farming and Agribusiness",
                "Energy Access",
                "Financial Infrastructure",
                "Data and AI",
                "Investment Climate",
                "Financial Inclusion",
                "Poverty",
                "Digital and AI",
                "Trade",
                "Small and Medium Enterprises Finance",
            ],
            # API facet spelling (comma before &) for MENAAP
            "wb_regions": [
                "South Asia",
                "Europe and Central Asia",
                "Middle East, North Africa, Afghanistan, & Pakistan",
                "Middle East and North Africa",
            ],
        },
        {
            "id": "environment-news",
            "name": "Environment News",
            # EIN News RSS expired ("This feed has expired") — replaced with Climate Home News
            "type": "rss",
            "content_kind": "news",
            "enabled": True,
            "max_age_days": 7,
            "url": "https://www.climatechangenews.com/feed/",
            "description": "Climate/environment news via Climate Home News (replaces expired EIN News). PK/MENA geo filter still applies.",
            "keywords": ["environment", "climate", "energy", "finance", "pakistan", "mena", "sustainability"],
            "skip_keyword_filter": True,
        },
        {
            "id": "global-warming-news",
            "name": "Global Warming News",
            # EIN News expired — Guardian climate-change RSS
            "type": "rss",
            "content_kind": "news",
            "enabled": True,
            "max_age_days": 7,
            "url": "https://www.theguardian.com/environment/climate-change/rss",
            "description": "Guardian Climate Change RSS (replaces expired EIN Global Warming feed). PK/MENA geo filter still applies.",
            "keywords": ["climate", "global warming", "environment", "energy", "emissions", "pakistan", "mena"],
            "skip_keyword_filter": True,
        },
        {
            "id": "worldbank-energy",
            "name": "World Bank - Energy",
            # blogs.worldbank.org/energy/feed returns 404 — use official news API (energy topics)
            "type": "scrape",
            "content_kind": "news",
            "enabled": True,
            "max_age_days": 7,
            "url": "https://www.worldbank.org/en/topic/energy",
            "description": "World Bank energy Press Releases via search API (blog RSS 404). Same region filters as World Bank News.",
            "keywords": ["world bank", "energy", "renewable", "solar", "climate", "pakistan", "mena"],
            "api_rows": 30,
            "skip_keyword_filter": True,
            "wb_display_type": "Press Release",
            "wb_topics": [
                "Energy",
                "Renewable Energy",
                "Energy and Extractives",
                "Energy Efficiency",
                "Energy Access",
                "Climate Change",
            ],
            "wb_regions": [
                "South Asia",
                "Europe and Central Asia",
                "Middle East, North Africa, Afghanistan, & Pakistan",
                "Middle East and North Africa",
            ],
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
            "max_age_days": 7,
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
            # Phase 1 expand: apply-able IsDB notices for Pakistan + UAE offices
            "id": "isdb-procurement",
            "name": "IsDB - Project Procurement (PK + UAE)",
            "type": "scrape",
            "content_kind": "opportunity",
            "url": "https://www.isdb.org/project-procurement/tenders",
            "description": "Islamic Development Bank EOIs, RFPs, and tenders for Pakistan and UAE. Consulting and climate-related notices firms can apply for.",
            "keywords": [],
            "max_pages": 5,
            "skip_ai_filter": True,
            "skip_keyword_filter": True,
        },
        {
            "id": "opec-fund-procurement",
            "name": "OPEC Fund - Procurement & Consulting",
            "type": "scrape",
            "content_kind": "opportunity",
            "url": "https://opecfund.org/work-with-us/project-procurement/current-opportunities",
            "description": "OPEC Fund project notices for Pakistan/UAE plus HQ consulting REOIs firms can apply for from PK/UAE offices.",
            "keywords": [],
            "skip_ai_filter": True,
            "skip_keyword_filter": True,
        },
        {
            "id": "undp-procurement-pk-uae",
            "name": "UNDP Procurement Notices (PK + UAE)",
            "type": "scrape",
            "content_kind": "opportunity",
            "url": "https://procurement-notices.undp.org/",
            "description": "Official UNDP procurement RSS for Pakistan and United Arab Emirates (RFPs, ICs, ITBs).",
            "keywords": [],
            "skip_ai_filter": True,
            "skip_keyword_filter": True,
        },
        {
            "id": "akrsp-grants",
            "name": "AKRSP - Grants & Funding (Pakistan)",
            "type": "scrape",
            "content_kind": "opportunity",
            "url": "https://akrsp.org.pk/grants-funding-opportunities/",
            "description": "Aga Khan Rural Support Programme open grant calls in Pakistan (climate, women/youth, community).",
            "keywords": [],
            "skip_ai_filter": True,
            "skip_keyword_filter": True,
        },
        {
            "id": "hub71-climatetech",
            "name": "Hub71+ ClimateTech (Abu Dhabi)",
            "type": "scrape",
            "content_kind": "opportunity",
            "crawler": "accelerator",
            "content_subtype": "accelerator",
            "country": "United Arab Emirates",
            "opportunity_title": "Hub71+ ClimateTech — Abu Dhabi climate startup accelerator",
            "url": "https://www.hub71.com/program/hub71-plus-climatetech",
            "description": "Hub71+ ClimateTech accelerator for sustainability startups entering the UAE/Abu Dhabi market.",
            "keywords": [],
            "skip_ai_filter": True,
            "skip_keyword_filter": True,
        },
        {
            "id": "catalyst-uae",
            "name": "Catalyst ClimateTech (Masdar City)",
            "type": "scrape",
            "content_kind": "opportunity",
            "crawler": "accelerator",
            "content_subtype": "accelerator",
            "country": "United Arab Emirates",
            "opportunity_title": "Catalyst Program — Masdar City / bp ClimateTech accelerator",
            "url": "https://catalyst.ae/apply-now",
            "description": "Catalyst ClimateTech accelerator (Masdar City & bp) for pre-seed/seed startups; UAE market access.",
            "keywords": [],
            "skip_ai_filter": True,
            "skip_keyword_filter": True,
        },
        {
            "id": "accelerate-prosperity-csi",
            "name": "Accelerate Prosperity CSI (Pakistan)",
            "type": "scrape",
            "content_kind": "opportunity",
            "crawler": "accelerator",
            "content_subtype": "accelerator",
            "country": "Pakistan",
            "opportunity_title": "Accelerate Prosperity — Certification in Sustainable Innovation (CSI)",
            "url": "https://pk.accelerateprosperity.org/certification-in-sustainable-innovation/",
            "description": "Pakistan national incubation for green / climate-conscious startups (Accelerate Prosperity).",
            "keywords": [],
            "skip_ai_filter": True,
            "skip_keyword_filter": True,
        },
        {
            "id": "clip-pakistan",
            "name": "CLIP Climate Tech Incubator (Pakistan)",
            "type": "scrape",
            "content_kind": "opportunity",
            "crawler": "accelerator",
            "content_subtype": "accelerator",
            "country": "Pakistan",
            "opportunity_title": "CLIP — Climate Tech Incubator (Pakistan)",
            "url": "https://climateinnovate.pk/",
            "description": "Climate Innovation Pakistan incubator for clean energy and climate startups (MVP to scale).",
            # Ongoing program page (cohort apply windows vary; keep visible for PK office)
            "force_open": True,
            "keywords": [],
            "skip_ai_filter": True,
            "skip_keyword_filter": True,
        },
        {
            "id": "digital-pakistan-climate-tech",
            "name": "Digital Pakistan – Climate Tech Cohort",
            "type": "scrape",
            "content_kind": "opportunity",
            "crawler": "accelerator",
            "content_subtype": "accelerator",
            "country": "Pakistan",
            "opportunity_title": "Digital Pakistan — Pakistan Climate Tech Cohort",
            "url": "https://digitalpakistan.io/programmes/pakistan-climate-tech-cohort-c58e4a99",
            "description": "Rolling-seat climate/cleantech incubation (water, energy, agri, urban sustainability).",
            "keywords": [],
            "skip_ai_filter": True,
            "skip_keyword_filter": True,
        },
        {
            "id": "nic-karachi-ignite",
            "name": "NIC Karachi / Ignite",
            "type": "scrape",
            "content_kind": "opportunity",
            "crawler": "accelerator",
            "content_subtype": "accelerator",
            "country": "Pakistan",
            "opportunity_title": "NIC Karachi (Ignite) — incubation & PKR 5M grant track",
            "url": "https://nickarachi.com/",
            "description": "Ignite-funded NIC Karachi incubator. Broader tech — climate/ESG filter applied on scrape.",
            "require_climate_theme": True,
            "force_open": True,
            "keywords": [],
            "skip_ai_filter": True,
            "skip_keyword_filter": True,
        },
        {
            "id": "cfa-pakistan",
            "name": "Climate Finance Accelerator (CFA) Pakistan",
            "type": "scrape",
            "content_kind": "opportunity",
            "crawler": "accelerator",
            "content_subtype": "accelerator",
            "country": "Pakistan",
            "opportunity_type": "Funding",
            "opportunity_title": "CFA Pakistan — Climate Finance Accelerator (UK DESNZ / DAI)",
            "url": "https://www.climatefinanceaccelerator.com/countries/pakistan",
            "description": "UK-backed Climate Finance Accelerator for investable climate projects in Pakistan. Keep listed while closed so next call is visible.",
            "keep_when_closed": True,
            "keywords": [],
            "skip_ai_filter": True,
            "skip_keyword_filter": True,
        },
        {
            "id": "propakistani-business",
            "name": "ProPakistani - Business News",
            "type": "rss",
            "content_kind": "news",
            "crawler": "business_news",
            "url": "https://propakistani.pk/category/business/feed/",
            "description": "ProPakistani business news via WordPress RSS (paginated, last 7 days). Gemini summary priority.",
            "keywords": [],
            "max_age_days": 7,
            "max_pages": 50,
            "skip_ai_filter": True,
            "skip_keyword_filter": True,
        },
        {
            "id": "arab-news-economy",
            "name": "Arab News - Economy",
            "type": "scrape",
            "content_kind": "news",
            "crawler": "business_news",
            "url": "https://www.arabnews.com/economy",
            "description": "Arab News economy/business archive (last 7 days). Same crawler as weekly example; Gemini runs first for this trio.",
            "keywords": [],
            "max_age_days": 7,
            "skip_ai_filter": True,
            "skip_keyword_filter": True,
        },
        {
            "id": "khaleej-times-business",
            "name": "Khaleej Times - Business",
            "type": "scrape",
            "content_kind": "news",
            "crawler": "business_news",
            "url": "https://www.khaleejtimes.com/business",
            "description": "Khaleej Times Business via searchadvancestories API (last 7 days). Same as weekly example; Gemini runs first for this trio.",
            "keywords": [],
            "max_age_days": 7,
            "skip_ai_filter": True,
            "skip_keyword_filter": True,
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
    """Source ids marked as news (last NEWS_LOOKBACK_DAYS)."""
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
