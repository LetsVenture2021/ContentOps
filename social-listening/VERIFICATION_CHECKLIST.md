# Content Draft Generation - Verification Checklist

Use this checklist to verify the script is working correctly.

## ✅ Pre-Run Checklist

### 1. Dependencies Installed

```bash
pip install python-dotenv requests jsonschema
```

Verify installation:
```bash
python3 -c "import dotenv, requests, jsonschema; print('✓ All dependencies installed')"
```

Expected output: `✓ All dependencies installed`

---

### 2. Environment Configuration

Check `.env` file exists:
```bash
ls -la social-listening/.env
```

Verify required variables:
```bash
cd social-listening
grep -E "OPENAI_API_KEY|NOTION_TOKEN" .env
```

Should show:
```
OPENAI_API_KEY=sk-...
NOTION_TOKEN=secret_...
```

---

### 3. Notion Configuration

Verify `config/notion.json` exists:
```bash
cat social-listening/config/notion.json | python3 -m json.tool
```

Should display valid JSON with database IDs:
```json
{
  "mentions_db_id": "...",
  "content_db_id": "...",
  ...
}
```

---

### 4. Script Exists and Is Valid

Check file exists:
```bash
ls -lh social-listening/scripts/generate_content_draft.py
```

Should show: `-rw-r--r-- ... 25K ... generate_content_draft.py`

Verify Python syntax:
```bash
cd social-listening
python3 -m py_compile scripts/generate_content_draft.py && echo "✓ Syntax valid"
```

Expected output: `✓ Syntax valid`

---

### 5. Logs Directory Exists

```bash
ls -ld social-listening/logs
```

Should show: `drwxr-xr-x ... logs`

If not, create it:
```bash
mkdir -p social-listening/logs
```

---

## ✅ Run Verification

### 6. Test Run

```bash
cd social-listening
python3 scripts/generate_content_draft.py
```

**Expected behaviors:**

**If no content opportunities:**
```
[2025-12-15 22:00:00] ================================================================================
[2025-12-15 22:00:00] CONTENT DRAFT GENERATION - STARTING
[2025-12-15 22:00:00] ================================================================================
[2025-12-15 22:00:01] Fetching content opportunities with Status='Ready to Draft'...
[2025-12-15 22:00:02] No content opportunities found with Status='Ready to Draft'
[2025-12-15 22:00:02] Exiting gracefully.
```
✓ This is **normal** if no opportunities exist in Notion.

**If opportunities found:**
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
[2025-12-15 22:00:16] Updated Notion page ... with draft
```
✓ Script is working correctly!

---

### 7. Verify Log File Created

```bash
ls -lh social-listening/logs/content_generation.log
```

Should show log file with recent timestamp.

View log contents:
```bash
tail -20 social-listening/logs/content_generation.log
```

Should show execution logs with timestamps.

---

### 8. Verify Notion Updates

If opportunities were processed:

1. Open your Notion Content Database
2. Find the processed opportunity
3. Verify these properties were updated:
   - ✓ **Status** = "Draft Ready for Review" (or "Draft Failed")
   - ✓ **Draft Content** = Full markdown content
   - ✓ **Headline** = Platform-optimized title
   - ✓ **Hook** = Opening sentences
   - ✓ **SEO Title** = Meta title
   - ✓ **SEO Description** = Meta description
   - ✓ **SEO Keywords** = Array of keywords
   - ✓ **Draft Generated At** = Recent timestamp

---

## ❌ Troubleshooting Common Issues

### Issue: `ModuleNotFoundError: No module named 'dotenv'`

**Solution:**
```bash
pip install python-dotenv requests jsonschema
```

---

### Issue: `OPENAI_API_KEY missing in .env`

**Solution:**
```bash
cd social-listening
echo "OPENAI_API_KEY=your-key-here" >> .env
echo "NOTION_TOKEN=your-token-here" >> .env
```

---

### Issue: `FileNotFoundError: [Errno 2] No such file or directory: '.../config/notion.json'`

**Solution:**
Verify you're running from the correct directory:
```bash
cd social-listening
python3 scripts/generate_content_draft.py
```

---

### Issue: `No content opportunities found`

**Solution:**
This is normal if no opportunities exist. To test:

1. Open Notion Content Database
2. Create a test opportunity with:
   - **Topic**: Test topic
   - **Platform Target**: BiggerPockets
   - **Audience**: Operator
   - **Status**: Ready to Draft
   - **Key Points**: Add 3+ bullet points
3. Run script again

---

### Issue: Script runs but drafts fail validation

**Check logs:**
```bash
tail -50 social-listening/logs/content_generation.log | grep -E "ERROR|validation failed"
```

Common causes:
- OpenAI API key invalid → Check `.env`
- Rate limit exceeded → Reduce `MAX_DRAFTS_PER_RUN`
- Network timeout → Retry script

---

### Issue: `401 Unauthorized` or `403 Forbidden` (Notion API)

**Solution:**
1. Verify Notion token in `.env` is correct
2. Ensure Notion integration has access to databases
3. Check database IDs in `config/notion.json` are correct

---

## ✅ Success Criteria

All checks passed if:

- [x] Dependencies installed without errors
- [x] `.env` file exists with valid keys
- [x] `config/notion.json` exists with database IDs
- [x] Script runs without Python errors
- [x] Log file created at `logs/content_generation.log`
- [x] Notion opportunities updated with Status="Draft Ready for Review"
- [x] Draft fields populated in Notion

---

## 📊 Performance Benchmarks

**Expected performance** (per opportunity):

| Platform | Content Length | Generation Time | OpenAI Cost (gpt-4o) |
|----------|---------------|-----------------|----------------------|
| BiggerPockets | 2000-3000 words | 10-20 seconds | ~$0.05-0.10 |
| LinkedIn | 800-1200 words | 5-10 seconds | ~$0.02-0.05 |
| X (Twitter) | 8-12 tweets | 5-8 seconds | ~$0.02-0.04 |
| Substack | 2500-4000 words | 15-25 seconds | ~$0.08-0.15 |

**Note**: Times vary based on OpenAI API load. Costs are approximate.

---

## 🔍 Advanced Verification

### Test with Mock Data

Use the test suite:
```bash
cd social-listening
python3 tests/test_content_generation.py
```

Expected output:
```
test_fetch_content_opportunities_success (__main__.TestContentOpportunityFetching) ... ok
test_retrieve_source_mentions_success (__main__.TestSourceMentionRetrieval) ... ok
...
Ran 20 tests in 0.123s

OK
✓ ALL TESTS PASSED
```

---

### Verify OpenAI Integration

Quick test of OpenAI connectivity:
```bash
python3 -c "
import os
from dotenv import load_dotenv
import requests

load_dotenv()
key = os.environ.get('OPENAI_API_KEY')
r = requests.get('https://api.openai.com/v1/models', 
                 headers={'Authorization': f'Bearer {key}'})
print('✓ OpenAI API connected' if r.status_code == 200 else f'✗ Error: {r.status_code}')
"
```

Expected output: `✓ OpenAI API connected`

---

### Verify Notion Integration

Quick test of Notion connectivity:
```bash
python3 -c "
import os, json
from dotenv import load_dotenv
import requests

load_dotenv()
token = os.environ.get('NOTION_TOKEN')
with open('config/notion.json') as f:
    cfg = json.load(f)
db_id = cfg['content_db_id']
r = requests.get(f'https://api.notion.com/v1/databases/{db_id}',
                 headers={'Authorization': f'Bearer {token}', 
                         'Notion-Version': '2022-06-28'})
print('✓ Notion API connected' if r.status_code == 200 else f'✗ Error: {r.status_code}')
"
```

Expected output: `✓ Notion API connected`

---

## ✅ Final Verification

If all checks pass, the script is **ready for production use**.

For ongoing monitoring:
- Check `logs/content_generation.log` after each run
- Monitor OpenAI API usage in dashboard
- Review generated drafts in Notion before publishing
- Track success/failure rates in logs

---

## 📚 Additional Resources

- **Quick Start**: See `QUICK_START.md`
- **Detailed Usage**: See `USAGE_GUIDE.md`
- **Scripts Overview**: See `scripts/README.md`
- **Tests**: Run `python3 tests/test_content_generation.py`
