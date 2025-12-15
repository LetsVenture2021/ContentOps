# Social Listening Scripts

This directory contains the core automation scripts for the ContentOps social listening pipeline.

## Available Scripts

### 1. `generate_content_draft.py` 📝

**Purpose**: Automatically generates platform-optimized content drafts from content opportunities.

**Usage**:
```bash
python3 scripts/generate_content_draft.py
```

**What it does**:
- Queries Notion for content opportunities (Status = "Ready to Draft")
- Fetches related social mentions for context
- Generates drafts using OpenAI with platform-specific guidelines
- Validates output for length, structure, and compliance
- Updates Notion with generated content
- Sets status to "Draft Ready for Review"

**Platforms**: BiggerPockets, LinkedIn, X (Twitter), Substack  
**Audiences**: CashBuyer, Operator, HNWI/LP

**Documentation**: See [`../QUICK_START.md`](../QUICK_START.md) and [`../USAGE_GUIDE.md`](../USAGE_GUIDE.md)

---

### 2. `classify_and_route.py` 🔀

**Purpose**: Triages and routes social mentions to appropriate queues.

**Usage**:
```bash
python3 scripts/classify_and_route.py
```

**What it does**:
- Fetches unclassified mentions from Notion
- Classifies sentiment, priority, and routes using OpenAI
- Creates queue items in Leads, Reputation, or Content databases
- Updates mention properties with classification results
- Uses two-tier model approach (triage → escalation if needed)

**Queues**: Leads, Reputation Management, Content Opportunities

---

### 3. `daily_synthesis.py` 📊

**Purpose**: Synthesizes daily insights from social listening mentions.

**Usage**:
```bash
python3 scripts/daily_synthesis.py
```

**What it does**:
- Aggregates mentions from the last 24 hours (configurable)
- Identifies trending topics and themes
- Generates content topic suggestions
- Creates structured daily reports
- Provides actionable insights for content strategy

---

### 4. `ingest_mentions.py` 📥

**Purpose**: Ingests social mentions into the Notion database.

**Usage**:
```bash
python3 scripts/ingest_mentions.py
```

**What it does**:
- Collects social mentions from various platforms
- Validates and normalizes mention data
- Creates new entries in Notion Mentions database
- Handles duplicates and data quality checks

---

### 5. `eval_classifier.py` 🧪

**Purpose**: Regression testing for the classification system.

**Usage**:
```bash
# Quick test (10 examples)
MAX_EXAMPLES=10 python3 scripts/eval_classifier.py

# Full test (100 examples)
MAX_EXAMPLES=100 python3 scripts/eval_classifier.py
```

**What it does**:
- Tests classifier accuracy against labeled examples
- Validates routing decisions, entity extraction, priority scoring
- Generates performance metrics and reports
- Used for quality assurance before deploying changes

**Test Data**: Uses `../tests/pv_labeled_examples_pack.jsonl`

---

### 6. `notion_smoke_test.py` 🔍

**Purpose**: Verifies Notion API connectivity and database access.

**Usage**:
```bash
python3 scripts/notion_smoke_test.py
```

**What it does**:
- Tests connection to Notion API
- Validates database IDs in configuration
- Checks read/write permissions
- Useful for debugging connectivity issues

---

## Common Requirements

All scripts require:

1. **Environment variables** (`.env` file):
   ```bash
   OPENAI_API_KEY=your-key
   NOTION_TOKEN=your-token
   ```

2. **Configuration** (`config/notion.json`):
   ```json
   {
     "mentions_db_id": "...",
     "leads_db_id": "...",
     "reputation_db_id": "...",
     "content_db_id": "..."
   }
   ```

3. **Dependencies**:
   ```bash
   pip install python-dotenv requests jsonschema
   ```

## Pipeline Flow

```
Social Platforms
      ↓
[ingest_mentions.py] → Notion Mentions DB
      ↓
[classify_and_route.py] → Leads/Reputation/Content DBs
      ↓
[generate_content_draft.py] → Draft Content
      ↓
[daily_synthesis.py] → Daily Reports
```

## Logs

All scripts log to:
- `../logs/content_generation.log` (generate_content_draft.py)
- Standard output for other scripts

## Testing

- **Unit tests**: `../tests/test_content_generation.py`
- **Integration tests**: Use `eval_classifier.py`
- **Smoke tests**: Use `notion_smoke_test.py`

## Troubleshooting

| Issue | Solution |
|-------|----------|
| ModuleNotFoundError | Install dependencies: `pip install python-dotenv requests jsonschema` |
| API key errors | Check `.env` file has correct credentials |
| Notion connection issues | Run `notion_smoke_test.py` to diagnose |
| Classification accuracy | Run `eval_classifier.py` to measure performance |

## Scheduling

For automated execution, use cron or GitHub Actions:

```bash
# Daily at 6 AM
0 6 * * * cd /path/to/ContentOps/social-listening && python3 scripts/daily_synthesis.py

# Every 2 hours
0 */2 * * * cd /path/to/ContentOps/social-listening && python3 scripts/classify_and_route.py

# Once daily at 8 AM
0 8 * * * cd /path/to/ContentOps/social-listening && python3 scripts/generate_content_draft.py
```

## Support

For issues or questions:
- Check individual script documentation
- Review logs in `../logs/`
- Run smoke tests to verify configuration
- See `../USAGE_GUIDE.md` for detailed troubleshooting
