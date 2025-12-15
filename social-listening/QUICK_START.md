# Quick Start - Run Content Draft Generation NOW

## ⚡ 3-Step Setup

### Step 1: Install Dependencies (30 seconds)

```bash
pip install python-dotenv requests jsonschema
```

### Step 2: Create .env File (1 minute)

Create `social-listening/.env` with your credentials:

```bash
OPENAI_API_KEY=sk-your-openai-key-here
NOTION_TOKEN=secret_your-notion-token-here
```

Optional settings (use defaults if not specified):
```bash
OPENAI_MODEL_CONTENT=gpt-4o
CONTENT_GENERATION_ENABLED=true
MAX_DRAFTS_PER_RUN=5
```

### Step 3: Run the Script (immediate)

```bash
cd social-listening
python3 scripts/generate_content_draft.py
```

## ✅ What You'll See

```
[2025-12-15 22:00:00] ================================================================================
[2025-12-15 22:00:00] CONTENT DRAFT GENERATION - STARTING
[2025-12-15 22:00:00] ================================================================================
[2025-12-15 22:00:01] Fetching content opportunities with Status='Ready to Draft'...
[2025-12-15 22:00:02] Found 3 content opportunities
[2025-12-15 22:00:03] --- Processing opportunity 1/3 ---
[2025-12-15 22:00:03] Topic: How to Underwrite DSCR Loans in 15 Minutes
[2025-12-15 22:00:03] Platform: BiggerPockets | Audience: Operator | Priority: 2
[2025-12-15 22:00:04] Retrieved 2 source mentions
[2025-12-15 22:00:04] Generating draft with gpt-4o...
[2025-12-15 22:00:15] ✓ Draft validation passed
[2025-12-15 22:00:15] ✓ Draft generated | length: 2547 words | model: gpt-4o
[2025-12-15 22:00:16] Updated Notion page with draft
...
[2025-12-15 22:01:30] ================================================================================
[2025-12-15 22:01:30] CONTENT DRAFT GENERATION - COMPLETED
[2025-12-15 22:01:30] ================================================================================
```

## 📊 Results in Notion

After running, check your Notion Content Database. Opportunities that were `Status = "Ready to Draft"` will now be:

- **Status**: "Draft Ready for Review" ✅
- **Draft Content**: Full markdown content populated
- **Headline**: Platform-optimized title
- **Hook**: Compelling opening
- **SEO Title**: Optimized meta title
- **SEO Description**: Meta description
- **SEO Keywords**: Keyword array
- **Draft Generated At**: Timestamp

## 🔍 Check Logs

View detailed execution logs:

```bash
cat logs/content_generation.log
```

## 🚨 Troubleshooting

| Problem | Solution |
|---------|----------|
| `ModuleNotFoundError: No module named 'dotenv'` | Run: `pip install python-dotenv requests jsonschema` |
| `OPENAI_API_KEY missing in .env` | Create `.env` file with your API key |
| `NOTION_TOKEN missing in .env` | Add your Notion integration token to `.env` |
| `No content opportunities found` | Add opportunities to Notion with `Status = "Ready to Draft"` |
| Script exits immediately | Set `CONTENT_GENERATION_ENABLED=true` in `.env` |

## 📝 Supported Platforms & Audiences

**Platforms:**
- BiggerPockets (2000-3000 words)
- LinkedIn (800-1200 words)  
- X/Twitter (8-12 tweets)
- Substack (2500-4000 words)

**Audiences:**
- CashBuyer (ROI-focused, practical)
- Operator (technical, systems-thinking)
- HNWI/LP (conservative, compliance-aware)

## ⚙️ Configuration Files

- **Environment**: `social-listening/.env`
- **Notion IDs**: `social-listening/config/notion.json`
- **Logs**: `social-listening/logs/content_generation.log`

## 🎯 That's It!

The script is **production-ready** and has been tested. Just add your credentials and run.

For detailed documentation, see `USAGE_GUIDE.md`.
