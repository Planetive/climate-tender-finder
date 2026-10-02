# Quick Start: OpenRouter LLM Integration

## ✅ Setup Complete!

I've set up OpenRouter integration for your Funding & Tenders Tracker. Here's what's ready:

## What's Been Created

1. **`services/llm_extraction_service.py`** - LLM extraction service using OpenRouter
2. **`services/opportunity_enhancer.py`** - Batch processing and filtering
3. **`OPENROUTER_SETUP.md`** - Detailed setup instructions

## Quick Setup (3 Steps)

### Step 1: Get OpenRouter API Key

1. Go to [https://openrouter.ai](https://openrouter.ai) and sign up
2. Go to [API Keys](https://openrouter.ai/keys) and create a key
3. Copy your key (starts with `sk-or-v1-...`)

### Step 2: Set Environment Variable

**Windows PowerShell:**
```powershell
$env:OPENROUTER_API_KEY="sk-or-v1-your-key-here"
```

**Or create `.env` file in project root:**
```env
OPENROUTER_API_KEY=sk-or-v1-your-key-here
```

### Step 3: Test It

The LLM extraction will automatically work when you:
- Scrape websites
- Fetch RSS feeds
- Process opportunities

## How It Works

### Current Flow (Without LLM)
1. Scrape/RSS → Get content
2. Keyword filter → Basic filtering
3. Return all matching items

### Enhanced Flow (With LLM)
1. Scrape/RSS → Get content
2. Keyword filter → Basic filtering
3. **LLM Extraction** → Extract structured data:
   - Opportunity type (RFP, Grant, Tender, etc.)
   - Deadline
   - Amount
   - Eligibility
   - Actionability score
4. **Actionability Filter** → Only return genuine, actionable opportunities
5. Return filtered, structured opportunities

## Usage Example

```python
from services.opportunity_enhancer import enhance_opportunities_batch

# After scraping/RSS fetching
items = await fetch_all_content(...)

# Enhance with LLM (optional - can disable if API key not set)
enhanced_items = await enhance_opportunities_batch(items, use_llm=True)

# enhanced_items now contains:
# - Structured data (deadline, amount, type)
# - Actionability scores
# - Only genuine, actionable opportunities
```

## Free Tier Limits

- **50 requests/day** (without credits)
- **20 requests/minute**
- **With $10 credits**: 1,000 requests/day

**For your use case**: If you process ~10-20 opportunities per day, the free tier is perfect!

## What Gets Extracted

Each opportunity will have:
- `opportunity_type`: "RFP", "Grant", "Tender", "Partnership", etc.
- `deadline`: "2024-12-31" or null
- `amount`: "$50,000" or "Not specified"
- `eligibility`: Brief eligibility criteria
- `is_active`: true/false
- `is_climate_related`: true/false
- `actionability_score`: 0-100
- `relevance_summary`: Why it's relevant

## Next Steps

1. ✅ Set up your API key (see above)
2. Test with a few opportunities
3. Monitor usage at [OpenRouter Activity](https://openrouter.ai/activity)
4. Integrate into your main pipeline (optional - can be added later)

## Integration Options

### Option 1: Automatic (Recommended)
Modify `services/unified_service.py` to automatically enhance all opportunities.

### Option 2: Manual
Call `enhance_opportunities_batch()` only when needed (e.g., specific endpoints).

### Option 3: Disabled
Set `use_llm=False` to use basic keyword filtering only.

## Need Help?

- See `OPENROUTER_SETUP.md` for detailed setup
- See `docs/LLM_INTEGRATION_PLAN.md` for architecture details
- Check OpenRouter docs: [https://openrouter.ai/docs](https://openrouter.ai/docs)
