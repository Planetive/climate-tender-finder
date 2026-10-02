# OpenRouter Setup Guide

## Why OpenRouter Free Tier?

✅ **No local resource usage** - Runs in the cloud  
✅ **Free tier available** - 50 requests/day (20 requests/minute)  
✅ **Easy setup** - Just need an API key  
✅ **Multiple free models** - Access to various LLMs  
✅ **Upgrade path** - Add $10 credits for 1,000 requests/day  

## Setup Steps

### 1. Create OpenRouter Account

1. Go to [https://openrouter.ai](https://openrouter.ai)
2. Sign up for a free account
3. Navigate to your [API Keys page](https://openrouter.ai/keys)
4. Create a new API key
5. Copy the API key (starts with `sk-or-v1-...`)

### 2. Set Environment Variable

**Windows (PowerShell):**
```powershell
$env:OPENROUTER_API_KEY="sk-or-v1-your-key-here"
```

**Windows (Command Prompt):**
```cmd
set OPENROUTER_API_KEY=sk-or-v1-your-key-here
```

**Linux/Mac:**
```bash
export OPENROUTER_API_KEY="sk-or-v1-your-key-here"
```

**Or create a `.env` file:**
```env
OPENROUTER_API_KEY=sk-or-v1-your-key-here
```

### 3. Free Models Available

OpenRouter provides access to free models. Recommended for our use case:

- **Google Gemini Flash** (free tier)
- **Meta Llama 3.2** (free tier)
- **Mistral 7B** (free tier)

### 4. Rate Limits (Free Tier)

- **50 requests per day** (without credits)
- **20 requests per minute**
- **With $10 credits**: 1,000 requests/day

### 5. Cost (If You Upgrade)

- Very affordable: ~$0.10-0.50 per 1,000 opportunities processed
- Pay only for what you use
- No monthly fees

## Usage in Code

The LLM extraction service will automatically use the `OPENROUTER_API_KEY` environment variable.

## Monitoring Usage

Check your usage at: [https://openrouter.ai/activity](https://openrouter.ai/activity)

## Next Steps

After setting up your API key, the LLM extraction service will automatically use OpenRouter for:
- Classifying opportunity types (RFP, Grant, Tender, etc.)
- Extracting structured data (deadlines, amounts, eligibility)
- Scoring actionability
- Filtering for genuine opportunities
