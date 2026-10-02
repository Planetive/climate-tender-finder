# LLM Integration Plan for Funding & Tenders Tracker

## Recommended Approach: Hybrid (LLM-Free + LLM-Based)

### Phase 1: Current State (LLM-Free)
✅ **What we have:**
- Basic web scraping with Crawl4AI
- Keyword-based filtering
- RSS feed aggregation

### Phase 2: Enhanced with LLM (Recommended)

#### Why LLM is Needed:
1. **Intelligent Classification**: Distinguish between RFP, Grant, Tender, Partnership, etc.
2. **Structured Extraction**: Extract deadlines, amounts, eligibility criteria automatically
3. **Actionability Assessment**: Determine if opportunity is genuine, active, and relevant
4. **Context Understanding**: Filter out expired, region-specific, or irrelevant opportunities

#### LLM Options (from Crawl4AI docs):

**Option A: OpenAI/Anthropic (Cloud)**
- **Pros**: High quality, reliable, fast
- **Cons**: API costs, requires internet
- **Best for**: Production, high-volume processing

**Option B: OpenRouter (Multi-Provider)**
- **Pros**: Access to multiple models, competitive pricing
- **Cons**: Requires API key management
- **Best for**: Cost optimization, model comparison

**Option C: Ollama (Local)**
- **Pros**: Free, private, no API costs
- **Cons**: Requires local setup, slower, needs GPU
- **Best for**: Privacy-sensitive, low-volume, development

#### Recommended: Use OpenRouter Free Tier (No Local Resources Needed)

## Implementation Strategy

### Step 1: Enhanced Content Extraction
Use Crawl4AI's LLM extraction strategies to:
- Extract structured opportunity data
- Classify opportunity types
- Score actionability

### Step 2: Schema-Based Extraction
Define a schema for opportunities:
```python
{
    "type": "RFP|Grant|Tender|Partnership|Program",
    "title": "...",
    "deadline": "YYYY-MM-DD",
    "amount": "$X or range",
    "eligibility": "...",
    "contact": "...",
    "actionability_score": 0-100,
    "relevance_to_planative": "high|medium|low"
}
```

### Step 3: Filtering Pipeline
1. **Basic Filter** (LLM-free): Keyword matching (current)
2. **LLM Filter**: Semantic understanding, actionability assessment
3. **Final Filter**: Business rules (region, amount thresholds, etc.)

## Cost Considerations

### OpenRouter Free Tier
- **Setup**: Just API key (no local installation)
- **Cost**: Free (50 requests/day, 20 requests/minute)
- **Speed**: Fast (cloud-based)
- **Privacy**: Data sent to API
- **Upgrade**: $10 credits = 1,000 requests/day
- **Production Cost**: ~$0.10-0.50 per 1,000 opportunities

### Ollama (Local - Not Recommended)
- **Setup**: Install Ollama, download model (~4-7GB)
- **Cost**: $0 but heavy on resources
- **Speed**: Slower, requires 8GB+ RAM
- **Privacy**: 100% local
- **Issue**: Can slow down your system significantly

## Recommendation

**Use OpenRouter Free Tier** (Recommended):
- ✅ No local resource usage
- ✅ Free tier sufficient for development/testing
- ✅ Easy setup (just API key)
- ✅ Fast and reliable
- ✅ Easy to upgrade when needed

## Next Steps

1. ✅ Set up OpenRouter API key (see `OPENROUTER_SETUP.md`)
2. ✅ LLM extraction service created (`services/llm_extraction_service.py`)
3. ✅ Opportunity schema defined
4. Integrate LLM extraction into scraping pipeline
5. Test with real opportunities
6. Monitor API usage and optimize
7. Upgrade to paid tier if needed (1,000 requests/day)
