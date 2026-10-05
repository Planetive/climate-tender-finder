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
}

interface BackendSource {
  id: string;
  name: string;
  type: string;
  url: string;
  description: string;
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
  type: "Grant" | "RFP" | "Partnership" | "Tender";
  relevance: "High" | "Medium" | "Low";
  deadline: string;
  deadlineDate: Date;
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
  
  // Infer opportunity type from title/categories
  const type = inferOpportunityType(item);
  
  // Infer relevance from keywords and content
  const relevance = inferRelevance(item);
  
  // Try to get deadline from backend field first (for paktender), otherwise extract from content
  let deadline: string;
  let deadlineDate: Date;
  
  if (item.deadline) {
    // Backend already provided deadline (e.g., from paktender)
    deadline = formatDeadlineForDisplay(item.deadline);
    deadlineDate = parseDeadlineDate(item.deadline);
  } else {
    // Try to extract deadline from content
    deadline = extractDeadline(item);
    deadlineDate = parseDeadlineDate(deadline);
  }
  
  // Use source name as funding agency
  const fundingAgency = item.source.name;
  
  // Use categories as tags
  const tags = item.categories.length > 0 ? item.categories : ['Climate', 'Funding'];
  
  // Use description or content as summary
  let summary = item.description || item.content?.substring(0, 300) || 'No description available.';
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
  
  return {
    id: item.id,
    title: item.title,
    source: item.source.name,
    country,
    region,
    type,
    relevance,
    deadline,
    deadlineDate,
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
  
  // Check for MENA countries
  const menaCountries = ['uae', 'saudi arabia', 'egypt', 'jordan', 'lebanon', 'morocco', 'tunisia', 'algeria', 'azerbaijan', 'georgia', 'turkey', 'türkiye'];
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
    'algeria', 'azerbaijan', 'georgia', 'turkey', 'türkiye', 'iraq', 'qatar',
    'bahrain', 'kuwait', 'oman', 'yemen', 'mena region',
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
 * Infer opportunity type from feed item
 */
function inferOpportunityType(item: BackendFeedItem): "Grant" | "RFP" | "Partnership" | "Tender" {
  const text = `${item.title} ${item.description}`.toLowerCase();
  const categories = item.categories.map(c => c.toLowerCase()).join(' ');
  
  if (text.includes('rfp') || text.includes('request for proposal') || text.includes('request for proposals')) {
    return 'RFP';
  }
  if (text.includes('tender') || text.includes('procurement') || text.includes('bidding')) {
    return 'Tender';
  }
  if (text.includes('partnership') || text.includes('partner') || categories.includes('partnership')) {
    return 'Partnership';
  }
  if (text.includes('grant') || text.includes('funding') || text.includes('call for')) {
    return 'Grant';
  }
  
  // Default to Grant for climate/funding content
  return 'Grant';
}

/**
 * Infer relevance from feed item
 */
function inferRelevance(item: BackendFeedItem): "High" | "Medium" | "Low" {
  const text = `${item.title} ${item.description} ${item.content}`.toLowerCase();
  
  // High relevance keywords
  const highKeywords = ['pakistan', 'mena', 'climate finance', 'esg', 'carbon market', 'mrv', 'adaptation', 'mitigation'];
  if (highKeywords.some(keyword => text.includes(keyword))) {
    return 'High';
  }
  
  // Medium relevance keywords
  const mediumKeywords = ['sustainability', 'renewable energy', 'clean energy', 'green'];
  if (mediumKeywords.some(keyword => text.includes(keyword))) {
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

/**
 * Infer required action based on opportunity type
 */
function inferRequiredAction(type: "Grant" | "RFP" | "Partnership" | "Tender"): string {
  switch (type) {
    case 'RFP':
      return 'Submit Proposal';
    case 'Tender':
      return 'Submit Bid';
    case 'Partnership':
      return 'Partner Application';
    case 'Grant':
    default:
      return 'Submit Application';
  }
}

// Frontend cache to avoid refetching on every navigation
let cachedOpportunities: { data: Opportunity[], timestamp: number, total: number } | null = null;
const FRONTEND_CACHE_TTL = 2 * 60 * 1000; // 2 minutes in milliseconds

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
    
    // Cache the full dataset
    cachedOpportunities = {
      data: allOpportunities,
      timestamp: Date.now(),
      total: data.total
    };
    
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
 * Fetch all sources from the backend
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
