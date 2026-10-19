/**
 * API Service for connecting to the News Tracker backend
 * 
 * This service handles all API calls to the FastAPI backend running on port 3001.
 * It transforms backend data into the format expected by the frontend components.
 */

// Base URL for the backend API.
// - Local Vite (`npm run dev`): talk to FastAPI on port 3001
// - Vercel production: same-origin `/api` (routed to the `app` service)
// - Optional override: set VITE_API_URL (e.g. AWS EC2) at build time
const API_BASE_URL =
  import.meta.env.VITE_API_URL ||
  (import.meta.env.PROD ? '/api' : 'http://localhost:3001/api');


/**
 * Backend API response types
 */
interface BackendFeedItem {
  id: string;
  title: string;
  link: string;
  description: string;
  content: string;
  pubDate: string;
  author: string;
  categories: string[];
  source: {
    id: string;
    name: string;
    url: string;
  };
  image?: string;
  deadline?: string; // Deadline field from backend (for paktender and other sources)
  development_area?: string;
  location?: string;
  country?: string; // Structured country when source provides it (e.g. ADB Countries:)
  reference_number?: string;
  posted?: string;
  deadline_display?: string;
  attachments?: { name: string; url: string }[];
  opportunity_type?: string;
  content_kind?: string;
  relevance?: string;
  /** Gemini summary for priority business-news sources (stored in extra) */
  ai_summary?: string;
}

interface BackendSource {
  id: string;
  name: string;
  type: string;
  url: string;
  description: string;
  content_kind?: string;
  category?: string;
  enabled?: boolean;
  status?: string;
  opportunities_found?: number;
  last_sync?: string | null;
  health?: {
    status?: string | null;
    items_kept?: number | null;
    items_raw?: number | null;
    last_error?: string | null;
    message?: string | null;
    last_success_at?: string | null;
  };
}

interface BackendFeedsResponse {
  success: boolean;
  total: number;
  count: number;
  offset: number;
  limit: number;
  data: BackendFeedItem[];
}

interface BackendSourcesResponse {
  success: boolean;
  count: number;
  data: BackendSource[];
}

/**
 * Frontend Opportunity type (matches the frontend's expected format)
 */
export interface Opportunity {
  id: string;
  title: string;
  source: string;
  country: string;
  region: string;
  type: "Grant" | "RFP" | "Partnership" | "Tender" | "Accelerator" | "Funding" | "News";
  /** news = articles/updates; opportunity = grants/tenders/procurement */
  contentKind: "news" | "opportunity";
  relevance: "High" | "Medium" | "Low";
  deadline: string;
  deadlineDate: Date;
  /** ISO or display-friendly published/posted date when we have one */
  published: string;
  /** Parsed published/posted date for KPI math (invalid → epoch) */
  publishedDate: Date;
  /** What the list/detail date field means */
  dateLabel: "Deadline" | "Published" | "Posted";
  /** Best date to show the user (deadline if present, else published) */
  dateDisplay: string;
  fundingAgency: string;
  tags: string[];
  summary: string;
  requiredAction: string;
  documents: { name: string; url: string }[];
  // Link to the original source/article (used in cards, detail page, etc.)
  link?: string;
}

/**
 * Transform backend feed item to frontend opportunity format
 * 
 * This function maps the backend's data structure to what the frontend expects.
 * Since the backend doesn't have all fields (like deadline, type, relevance),
 * we infer or set defaults where needed.
 */
function transformFeedToOpportunity(item: BackendFeedItem): Opportunity {
  // Extract country/region from categories or content
  const country = extractCountry(item);
  const region = extractRegion(item, country);
  
  // Prefer backend labels (set during ingest); fall back to local heuristics
  const type = inferOpportunityType(item);
  const relevance =
    item.relevance === "High" || item.relevance === "Medium" || item.relevance === "Low"
      ? item.relevance
      : inferRelevance(item);
  
  // Deadline (tenders/grants) and/or published date (news, many grants)
  let deadline: string;
  let deadlineDate: Date;

  if (item.deadline) {
    deadline = formatDeadlineForDisplay(item.deadline);
    deadlineDate = parseDeadlineDate(item.deadline);
  } else {
    deadline = extractDeadline(item);
    deadlineDate = parseDeadlineDate(deadline);
  }

  const publishedRaw = item.posted || item.pubDate || "";
  const published = publishedRaw ? formatPubDateForDisplay(publishedRaw) : "";
  // Real calendar date for "new this week" KPIs — never invent a far-future date
  const publishedDate = parsePublishedDate(publishedRaw);

  const hasRealDeadline =
    Boolean(item.deadline) ||
    (deadline && deadline !== "Not specified" && !/^not specified$/i.test(deadline));

  let dateLabel: "Deadline" | "Published" | "Posted" = "Deadline";
  let dateDisplay = deadline;
  if (hasRealDeadline) {
    dateLabel = "Deadline";
    dateDisplay = deadline;
  } else if (published) {
    dateLabel = item.posted ? "Posted" : "Published";
    dateDisplay = published;
    // Keep deadlineDate aligned to published for sorting when no deadline
    deadlineDate = publishedDate.getTime() > 0 ? publishedDate : parseDeadlineDate(published);
  } else {
    dateLabel = "Published";
    dateDisplay = "Not specified";
  }

  // Use source name as funding agency
  const fundingAgency = item.source.name;
  
  // Use categories as tags
  const tags = item.categories.length > 0 ? item.categories : ['Climate', 'Funding'];
  
  // Prefer Gemini summary when present (priority business-news sources)
  const aiSummary = (item.ai_summary || "").trim();
  let summary =
    (aiSummary && !aiSummary.toLowerCase().startsWith("summary error")
      ? aiSummary
      : null) ||
    item.description ||
    item.content?.substring(0, 300) ||
    "No description available.";
  // Prefer structured UNDP fields in summary when present
  if (item.reference_number || item.development_area) {
    summary = [
      item.development_area ? `Development Area: ${item.development_area}` : null,
      item.location ? `Location: ${item.location}` : null,
      item.reference_number ? `Reference Number: ${item.reference_number}` : null,
      item.posted ? `Posted: ${item.posted}` : null,
      item.deadline_display || item.deadline ? `Deadline: ${item.deadline_display || item.deadline}` : null,
      item.description || null,
    ].filter(Boolean).join('\n');
  }
  
  // Default required action
  const requiredAction = inferRequiredAction(type);
  
  // Extract attachments if available (for paktender tenders)
  const documents: { name: string; url: string }[] = [];
  if (item.attachments && Array.isArray(item.attachments)) {
    documents.push(...item.attachments);
  }
  // Always add the main link as "View" / "View Details" (notice page, not listing)
  if (item.link && !documents.some((d) => d.url === item.link)) {
    documents.push({ name: item.reference_number ? 'View' : 'View Details', url: item.link });
  }
  
  const contentKind: "news" | "opportunity" =
    item.content_kind === "news" ? "news" : "opportunity";

  return {
    id: item.id,
    title: item.title,
    source: item.source.name,
    country,
    region,
    type,
    contentKind,
    relevance,
    deadline: hasRealDeadline ? deadline : "Not specified",
    deadlineDate,
    published: published || "Not specified",
    publishedDate,
    dateLabel,
    dateDisplay,
    fundingAgency,
    tags,
    summary,
    requiredAction,
    documents,
    link: item.link,
  };
}

/**
 * Extract country from feed item
 */
function extractCountry(item: BackendFeedItem): string {
  // Prefer structured country from backend (ADB Countries: field, etc.)
  const structured = (item.country || item.location || "").trim();
  if (structured) {
    if (/^regional$/i.test(structured)) return "Regional";
    return structured;
  }

  if (item.source?.id === 'undp-pakistan-procurement' || item.source?.name?.toLowerCase().includes('undp pakistan')) {
    return 'Pakistan';
  }

  // ADB category blobs sometimes land in categories before backend parse (legacy)
  for (const cat of item.categories || []) {
    const match = cat.match(/Countries:\s*([^|]+)/i);
    if (match) {
      const value = match[1].trim();
      if (value) return value;
    }
  }

  const text = `${item.title} ${item.description} ${item.content} ${item.location || ''}`.toLowerCase();
  
  // Check for specific countries
  if (text.includes('pakistan')) return 'Pakistan';
  if (text.includes('india')) return 'India';
  if (text.includes('bangladesh')) return 'Bangladesh';
  if (text.includes('sri lanka')) return 'Sri Lanka';
  if (text.includes('nepal')) return 'Nepal';
  if (text.includes('afghanistan')) return 'Afghanistan';
  
  // MENA only (Türkiye / Azerbaijan / Georgia are out of scope for this product)
  const menaCountries = [
    'uae', 'saudi arabia', 'egypt', 'jordan', 'lebanon', 'morocco', 'tunisia',
    'algeria', 'iraq', 'qatar', 'bahrain', 'kuwait', 'oman', 'yemen',
  ];
  for (const country of menaCountries) {
    if (text.includes(country)) {
      return country.split(' ').map(w => w.charAt(0).toUpperCase() + w.slice(1)).join(' ');
    }
  }
  
  // Check categories for region hints
  if (item.categories.some(cat => cat.toLowerCase().includes('south asia'))) {
    return 'South Asia';
  }
  if (item.categories.some(cat => cat.toLowerCase().includes('mena'))) {
    return 'MENA Region';
  }
  
  return 'Global';
}

/**
 * Extract region from feed item
 */
function extractRegion(item: BackendFeedItem, country: string): string {
  const c = country.toLowerCase();

  if (c === 'pakistan' || ['india', 'bangladesh', 'sri lanka', 'nepal', 'afghanistan'].includes(c)) {
    return 'South Asia';
  }

  const mena = [
    'uae', 'saudi arabia', 'egypt', 'jordan', 'lebanon', 'morocco', 'tunisia',
    'algeria', 'iraq', 'qatar', 'bahrain', 'kuwait', 'oman', 'yemen', 'mena region',
  ];
  if (c.includes('mena') || mena.includes(c)) {
    return 'Middle East & North Africa';
  }

  if (c === 'regional') {
    return 'Regional';
  }

  if (country === 'Global' || country === 'South Asia') {
    return country;
  }

  // Multi-country strings from ADB (e.g. "Micronesia, Federated States of") stay Global unless matched
  if (c.includes('pakistan')) return 'South Asia';

  return 'Global';
}

/**
 * Infer opportunity type from feed item.
 * Prefer backend opportunity_type / source, so tenders are not mislabeled as Grant.
 */
type OppType = "Grant" | "RFP" | "Partnership" | "Tender" | "Accelerator" | "Funding" | "News";

function inferOpportunityType(item: BackendFeedItem): OppType {
  const mapType = (raw: string): OppType | null => {
    const t = raw.toLowerCase();
    if (t === "news" || t.includes("news")) {
      return "News";
    }
    if (t.includes("accelerat") || t.includes("incubator")) {
      return "Accelerator";
    }
    if (
      t.includes("rfp") ||
      t.includes("request for proposal") ||
      t.includes("rfq") ||
      t.includes("negotiation") ||
      t.includes("expression of interest") ||
      t.includes("eoi")
    ) {
      return "RFP";
    }
    if (t.includes("tender") || t.includes("procurement") || t.includes("bid") || t.includes("invitation for bid")) {
      return "Tender";
    }
    if (t.includes("partner")) {
      return "Partnership";
    }
    if (t.includes("startup funding") || t.includes("seed fund") || t === "funding") {
      return "Funding";
    }
    if (t.includes("grant") || t.includes("funding") || t.includes("call for")) {
      return "Grant";
    }
    return null;
  };

  if (item.content_kind === "news") {
    return "News";
  }

  if (item.opportunity_type) {
    const mapped = mapType(item.opportunity_type);
    if (mapped) return mapped;
  }

  // Source-based defaults (procurement portals)
  const sourceId = (item.source?.id || "").toLowerCase();
  const tenderSources = [
    "paktender",
    "ungm",
    "undp-pakistan-procurement",
    "gcf-negotiations",
    "adb-invitation-for-bids",
    "adb-advanced-notices",
    "adb-csrn",
    "afdb-procurement",
    "isdb-procurement",
  ];
  if (tenderSources.includes(sourceId)) {
    const text = `${item.title} ${item.description}`.toLowerCase();
    if (text.includes("expression of interest") || text.includes("eoi") || text.includes("rfp")) {
      return "RFP";
    }
    return "Tender";
  }

  const text = `${item.title} ${item.description}`.toLowerCase();
  const categories = (item.categories || []).map((c) => c.toLowerCase()).join(" ");
  const fromText = mapType(`${text} ${categories}`);
  if (fromText) return fromText;

  // News / blogs without clear funding language — still Grant only as last resort
  return "Grant";
}

/**
 * Infer relevance from feed item
 */
function inferRelevance(item: BackendFeedItem): "High" | "Medium" | "Low" {
  const text = `${item.title} ${item.description} ${item.content}`.toLowerCase();
  
  // Office / facilities buys are never High (photocopiers, elevators, …)
  const noise = [
    'photocopier', 'photocopy', 'copier', 'elevator', 'stationery', 'furniture',
    'traditional craft', 'handicraft', 'toner', 'laptop',
  ];
  if (noise.some((n) => text.includes(n))) {
    return 'Low';
  }

  // High = real ESG / climate / industrial themes (geo alone is not enough)
  const highKeywords = [
    'climate finance', 'climate risk', 'esg', 'carbon market', 'mrv', 'net zero',
    'energy transition', 'petroleum', 'oil and gas', 'chemical', 'steel', 'cement',
    'plastic', 'decarbon', 'sustainable finance', 'green finance', 'renewable',
  ];
  if (highKeywords.some((keyword) => text.includes(keyword))) {
    return 'High';
  }

  const mediumKeywords = [
    'sustainability', 'clean energy', 'climate', 'energy', 'carbon',
    'adaptation', 'mitigation', 'emission', 'solar', 'wind',
  ];
  if (mediumKeywords.some((keyword) => text.includes(keyword))) {
    return 'Medium';
  }

  return 'Low';
}

/**
 * Extract deadline from feed item content
 */
function extractDeadline(item: BackendFeedItem): string {
  // Try to find deadline in content
  const text = `${item.description} ${item.content}`;
  const deadlineMatch = text.match(/(?:deadline|due date|closing date|submission deadline)[\s:]+([A-Za-z]+\s+\d{1,2},?\s+\d{4})/i);
  if (deadlineMatch) {
    return deadlineMatch[1];
  }
  
  // If no deadline found, use "Not specified"
  return 'Not specified';
}

/**
 * Format pubDate (ISO datetime or date) for display
 */
function formatPubDateForDisplay(raw: string): string {
  if (!raw || raw === "Not specified") return "";
  try {
    const trimmed = raw.trim();
    // Prefer date part of ISO timestamps
    const datePart = trimmed.match(/^(\d{4}-\d{2}-\d{2})/)?.[1];
    if (datePart) {
      return formatDeadlineForDisplay(datePart);
    }
    const date = new Date(trimmed);
    if (!isNaN(date.getTime())) {
      const months = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"];
      return `${months[date.getMonth()]} ${date.getDate()}, ${date.getFullYear()}`;
    }
  } catch {
    // fall through
  }
  return raw.slice(0, 32);
}

/**
 * Format deadline from ISO format (YYYY-MM-DD) to display format
 */
function formatDeadlineForDisplay(isoDate: string): string {
  try {
    // Parse ISO date (YYYY-MM-DD)
    const date = new Date(isoDate + 'T00:00:00'); // Add time to avoid timezone issues
    if (!isNaN(date.getTime())) {
      // Format as "Jan 28, 2026"
      const months = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'];
      const month = months[date.getMonth()];
      const day = date.getDate();
      const year = date.getFullYear();
      return `${month} ${day}, ${year}`;
    }
  } catch (e) {
    // If parsing fails, return as is
  }
  return isoDate;
}

/**
 * Parse deadline string to Date object
 */
function parseDeadlineDate(deadline: string): Date {
  if (deadline === 'Not specified') {
    // Return a date far in the future
    return new Date('2099-12-31');
  }
  
  try {
    // Try parsing ISO format first (YYYY-MM-DD)
    if (deadline.match(/^\d{4}-\d{2}-\d{2}$/)) {
      const date = new Date(deadline + 'T00:00:00');
      if (!isNaN(date.getTime())) {
        return date;
      }
    }
    
    // Try parsing other formats
    const date = new Date(deadline);
    if (!isNaN(date.getTime())) {
      return date;
    }
  } catch (e) {
    // If parsing fails, return far future date
  }
  
  return new Date('2099-12-31');
}

/** Parse posted/pubDate for KPI "new this week" — returns Invalid Date epoch if unknown */
function parsePublishedDate(raw: string): Date {
  if (!raw || /^not specified$/i.test(raw.trim())) {
    return new Date(0);
  }
  try {
    const iso = raw.match(/^(\d{4}-\d{2}-\d{2})/);
    if (iso) {
      const d = new Date(iso[1] + "T00:00:00");
      if (!isNaN(d.getTime())) return d;
    }
    const d = new Date(raw);
    if (!isNaN(d.getTime())) return d;
  } catch {
    // fall through
  }
  return new Date(0);
}

/**
 * Infer required action based on opportunity type
 */
function inferRequiredAction(type: OppType): string {
  switch (type) {
    case "RFP":
      return "Submit Proposal";
    case "Tender":
      return "Submit Bid";
    case "Partnership":
      return "Partner Application";
    case "Accelerator":
      return "Apply to Program";
    case "Funding":
      return "Submit Funding Application";
    case "Grant":
    default:
      return "Submit Application";
  }
}

// Frontend cache to avoid refetching on every navigation
let cachedOpportunities: { data: Opportunity[], timestamp: number, total: number } | null = null;
const FRONTEND_CACHE_TTL = 2 * 60 * 1000; // 2 minutes in milliseconds
const SESSION_CACHE_KEY = "ft_opportunities_by_id_v1";

/** Store items so detail pages open instantly without another API call */
export function cacheOpportunitiesById(opps: Opportunity[]): void {
  try {
    const map: Record<string, Opportunity> = {};
    // Keep any previous session entries
    const prev = sessionStorage.getItem(SESSION_CACHE_KEY);
    if (prev) {
      Object.assign(map, JSON.parse(prev));
    }
    for (const opp of opps) {
      if (opp?.id) map[opp.id] = opp;
    }
    sessionStorage.setItem(SESSION_CACHE_KEY, JSON.stringify(map));
  } catch (e) {
    console.warn("Could not cache opportunities in sessionStorage", e);
  }
}

/** Instant lookup from memory or session (no network) */
export function getCachedOpportunity(id: string): Opportunity | null {
  if (cachedOpportunities?.data) {
    const hit = cachedOpportunities.data.find((o) => o.id === id);
    if (hit) return hit;
  }
  try {
    const raw = sessionStorage.getItem(SESSION_CACHE_KEY);
    if (!raw) return null;
    const map = JSON.parse(raw) as Record<string, Opportunity>;
    const hit = map[id];
    if (!hit) return null;
    // Revive Date if it was serialized
    if (hit.deadlineDate && typeof hit.deadlineDate === "string") {
      hit.deadlineDate = new Date(hit.deadlineDate);
    }
    if (hit.publishedDate && typeof hit.publishedDate === "string") {
      hit.publishedDate = new Date(hit.publishedDate);
    }
    return hit;
  } catch {
    return null;
  }
}

/**
 * Fetch all opportunities from the backend
 * Uses frontend caching to avoid unnecessary API calls
 */
export async function fetchOpportunities(limit: number = 500, offset: number = 0, forceRefresh: boolean = false): Promise<Opportunity[]> {
  try {
    // Check frontend cache first (unless force refresh)
    if (!forceRefresh && cachedOpportunities) {
      const cacheAge = Date.now() - cachedOpportunities.timestamp;
      if (cacheAge < FRONTEND_CACHE_TTL) {
        // Return cached data (still apply limit/offset)
        const cached = cachedOpportunities.data;
        return cached.slice(offset, offset + limit);
      }
    }
    
    // Fetch a large batch so all sources are included (backend max 2000)
    const fetchLimit = Math.min(Math.max(limit, 500), 2000);
    const response = await fetch(`${API_BASE_URL}/feeds?limit=${fetchLimit}&offset=0&refresh=${forceRefresh}`);
    
    if (!response.ok) {
      throw new Error(`Failed to fetch opportunities: ${response.statusText}`);
    }
    
    const data: BackendFeedsResponse = await response.json();
    
    if (!data.success) {
      throw new Error('API returned unsuccessful response');
    }
    
    // Transform backend data to frontend format
    const allOpportunities = data.data.map(transformFeedToOpportunity);

    // Cache for list + detail (memory + session)
    cachedOpportunities = {
      data: allOpportunities,
      timestamp: Date.now(),
      total: data.total
    };
    cacheOpportunitiesById(allOpportunities);
    
    // Return the requested slice
    return allOpportunities.slice(offset, offset + limit);
  } catch (error) {
    console.error('Error fetching opportunities:', error);
    // Return cached data if available, even if expired
    if (cachedOpportunities) {
      console.log('Using expired cache due to error');
      return cachedOpportunities.data.slice(offset, offset + limit);
    }
    // Return empty array on error (fail-safe design)
    return [];
  }
}

/**
 * Resolve one opportunity for the detail page.
 * Order: memory/session cache first (instant), then DB by id — never re-scrapes.
 */
export async function fetchOpportunityById(id: string): Promise<Opportunity | null> {
  const cached = getCachedOpportunity(id);
  if (cached) {
    return cached;
  }

  try {
    const response = await fetch(`${API_BASE_URL}/feeds/item/${encodeURIComponent(id)}`);

    if (response.status === 404) {
      return null;
    }

    if (!response.ok) {
      throw new Error(`Failed to fetch opportunity: ${response.statusText}`);
    }

    const data = await response.json();
    if (!data.success || !data.data) {
      return null;
    }

    const opp = transformFeedToOpportunity(data.data as BackendFeedItem);
    cacheOpportunitiesById([opp]);
    return opp;
  } catch (error) {
    console.error('Error fetching opportunity by id:', error);
    throw error;
  }
}

/**
 * Fetch opportunities from a specific source
 */
export async function fetchOpportunitiesBySource(sourceId: string): Promise<Opportunity[]> {
  try {
    const response = await fetch(`${API_BASE_URL}/feeds/source/${sourceId}`);
    
    if (!response.ok) {
      throw new Error(`Failed to fetch opportunities from source: ${response.statusText}`);
    }
    
    const data = await response.json();
    
    if (!data.success) {
      throw new Error('API returned unsuccessful response');
    }
    
    // Transform backend data to frontend format
    return data.data.map(transformFeedToOpportunity);
  } catch (error) {
    console.error('Error fetching opportunities by source:', error);
    return [];
  }
}

/**
 * Fetch all sources from the backend (fast — no live scrape)
 */
export async function fetchSources(): Promise<BackendSource[]> {
  try {
    const response = await fetch(`${API_BASE_URL}/sources`);
    
    if (!response.ok) {
      throw new Error(`Failed to fetch sources: ${response.statusText}`);
    }
    
    const data: BackendSourcesResponse = await response.json();
    
    if (!data.success) {
      throw new Error('API returned unsuccessful response');
    }
    
    return data.data;
  } catch (error) {
    console.error('Error fetching sources:', error);
    return [];
  }
}

/**
 * Turn a source on/off for daily + Re-run ingest
 */
export async function toggleSourceEnabled(sourceId: string, enabled: boolean): Promise<BackendSource | null> {
  const response = await fetch(
    `${API_BASE_URL}/sources/${encodeURIComponent(sourceId)}/toggle?enabled=${enabled}`,
    { method: 'POST' }
  );
  if (!response.ok) {
    throw new Error(`Failed to update source: ${response.statusText}`);
  }
  const data = await response.json();
  if (!data.success) {
    throw new Error('API returned unsuccessful response');
  }
  return data;
}

/**
 * Health check - verify backend is running
 */
export async function checkBackendHealth(): Promise<boolean> {
  try {
    const response = await fetch(`${API_BASE_URL}/health`);
    const data = await response.json();
    return data.status === 'ok';
  } catch (error) {
    console.error('Backend health check failed:', error);
    return false;
  }
}

/** One source’s result from a full ingest run */
export interface IngestSourceResult {
  id?: string;
  name?: string;
  status?: "ok" | "error" | string;
  items?: number;
  items_raw?: number;
  error?: string;
}

export interface IngestResult {
  success: boolean;
  trigger?: string;
  items?: number;
  items_raw?: number;
  upserted?: number;
  news_deleted?: number;
  sources_run?: number;
  sources_ok?: number;
  sources_error?: number;
  sources_skipped?: number;
  /** Per-source outcomes from the last full run */
  sources?: IngestSourceResult[];
  source_id?: string;
  source_name?: string;
  message?: string;
  warning?: string;
  running?: boolean;
  error?: string;
}

export interface IngestStatusResponse {
  success: boolean;
  last_ingest?: IngestResult & { finished_at?: string; started_at?: string };
  seconds_until_next_7am_pkt?: number;
  missed_todays_7am_pkt?: boolean;
  timezone?: string;
  hint?: string;
}

export async function fetchIngestStatus(): Promise<IngestStatusResponse | null> {
  try {
    const response = await fetch(`${API_BASE_URL}/feeds/ingest-status`);
    if (!response.ok) return null;
    return await response.json();
  } catch {
    return null;
  }
}

/**
 * Manually re-run scrape/RSS (same job as the daily 07:00 PKT schedule).
 * Can take several minutes — show a loading state in the UI.
 */
export async function triggerFeedRefresh(): Promise<IngestResult> {
  // Clear frontend cache so the next list load sees fresh DB rows
  cachedOpportunities = null;

  const response = await fetch(`${API_BASE_URL}/feeds/refresh`, {
    method: 'POST',
  });

  const data = await response.json().catch(() => ({}));

  if (response.status === 409) {
    return {
      success: false,
      running: true,
      message: data?.message || data?.detail?.message || 'Ingest already running',
    };
  }

  if (!response.ok) {
    throw new Error(
      data?.detail?.error || data?.error || data?.message || `Refresh failed (${response.status})`
    );
  }

  return data as IngestResult;
}

/**
 * Scrape one source immediately (after turning it on).
 * Can take 1–few minutes depending on the source.
 */
export async function scrapeOneSource(sourceId: string): Promise<IngestResult> {
  cachedOpportunities = null;

  const response = await fetch(
    `${API_BASE_URL}/sources/${encodeURIComponent(sourceId)}/scrape`,
    { method: "POST" }
  );

  const data = await response.json().catch(() => ({}));
  const detail = data?.detail && typeof data.detail === "object" ? data.detail : data;

  if (response.status === 409) {
    return {
      success: false,
      running: true,
      message: detail?.message || "Ingest already running",
      source_id: sourceId,
    };
  }

  if (!response.ok) {
    if (response.status === 404) {
      throw new Error(
        "Scrape endpoint missing — restart the local backend (python main.py) to load the latest code."
      );
    }
    throw new Error(
      detail?.error || detail?.message || data?.error || `Scrape failed (${response.status})`
    );
  }

  return data as IngestResult;
}
