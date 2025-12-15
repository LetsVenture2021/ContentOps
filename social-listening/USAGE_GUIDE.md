# Content Draft Generation - Usage Guide

## Overview

The `generate_content_draft.py` script automatically generates platform-optimized content drafts from content opportunities identified by the social listening system.

## Prerequisites

### 1. Install Dependencies

```bash
pip install python-dotenv requests jsonschema
```

### 2. Configure Environment

Create a `.env` file in the `social-listening/` directory with your credentials:

```bash
# Required
OPENAI_API_KEY=your-openai-api-key-here
NOTION_TOKEN=your-notion-integration-token-here

# Optional (defaults shown)
OPENAI_MODEL_CONTENT=gpt-4o
CONTENT_GENERATION_ENABLED=true
MAX_DRAFTS_PER_RUN=5
```

### 3. Verify Configuration

Ensure `config/notion.json` contains your Notion database IDs:

```json
{
  "mentions_db_id": "your-mentions-database-id",
  "content_db_id": "your-content-database-id",
  ...
}
```

## Running the Script

### Basic Usage

```bash
cd social-listening
python3 scripts/generate_content_draft.py
```

### What It Does

1. **Queries Notion** for content opportunities with `Status = "Ready to Draft"`
2. **Fetches source mentions** to provide context for content generation
3. **Generates drafts** using OpenAI with platform-specific guidelines
4. **Validates drafts** for length, structure, and compliance
5. **Updates Notion** with generated content and metadata
6. **Sets status** to "Draft Ready for Review" (or "Draft Failed" on error)

### Supported Platforms

- **BiggerPockets**: 2000-3000 word educational forum posts
- **LinkedIn**: 800-1200 word thought leadership articles
- **X (Twitter)**: 8-12 tweet threads
- **Substack**: 2500-4000 word newsletters

### Supported Audiences

- **CashBuyer**: ROI-focused, practical, numbers-driven
- **Operator**: Technical, process-oriented, systems-thinking
- **HNWI/LP**: Conservative, compliance-aware, relationship-focused

## Output

### Logs

All activity is logged to `logs/content_generation.log` with timestamps:

```
[2025-12-15 22:00:00] CONTENT DRAFT GENERATION - STARTING
[2025-12-15 22:00:01] Fetching content opportunities with Status='Ready to Draft'...
[2025-12-15 22:00:02] Found 3 content opportunities
[2025-12-15 22:00:03] --- Processing opportunity 1/3 ---
[2025-12-15 22:00:03] Topic: How to Underwrite DSCR Loans in 15 Minutes
[2025-12-15 22:00:03] Platform: BiggerPockets | Audience: Operator | Priority: 2
[2025-12-15 22:00:04] Retrieved 2 source mentions
[2025-12-15 22:00:04] Generating draft with gpt-4o...
[2025-12-15 22:00:15] ✓ Draft validation passed
[2025-12-15 22:00:15] ✓ Draft generated | length: 2547 words | model: gpt-4o
[2025-12-15 22:00:16] Updated Notion page test-content-001 with draft
```

### Notion Updates

For each successfully generated draft, the following Notion properties are updated:

- **Draft Content**: Full markdown body
- **Headline**: Platform-optimized title
- **Hook**: Opening 2-3 sentences
- **SEO Title**: 50-60 character SEO title
- **SEO Description**: 150-160 character meta description
- **SEO Keywords**: Array of keywords
- **Image Placeholders**: Descriptions for visual content
- **Status**: Changed to "Draft Ready for Review"
- **Draft Generated At**: Timestamp of generation
- **Content Structure Notes**: Explanation of content structure

## Error Handling

### Retry Logic

- OpenAI API calls retry up to 3 times
- Uses exponential backoff: 1s, 2s, 4s
- Continues processing other opportunities if one fails

### Failure States

If draft generation fails:
- Status set to "Draft Failed"
- Error message logged to file and Notion
- Other opportunities continue processing

## Rate Limiting

- 2-second delay between processing opportunities
- Configure `MAX_DRAFTS_PER_RUN` to limit processing volume
- OpenAI API timeout set to 120 seconds

## Validation Rules

### Length Validation

- **BiggerPockets**: 1800-3300 words (±10%)
- **LinkedIn**: 720-1320 words (±10%)
- **X**: 7-13 tweets (±1)
- **Substack**: 2250-4400 words (±10%)

### Compliance Validation (HNWI/LP Audience)

Prohibited terms that trigger validation failure:
- "guaranteed returns"
- "guaranteed profit"
- "legal advice"
- "tax advice"
- "investment advice"
- "promise", "assure you will", "you will make"

### Structure Validation

- Headline minimum 10 characters
- Hook minimum 20 characters
- At least 3 key points required

## Troubleshooting

### "No content opportunities found"

- Verify Notion database has opportunities with `Status = "Ready to Draft"`
- Check `config/notion.json` has correct `content_db_id`
- Verify Notion integration has access to the database

### "OPENAI_API_KEY missing"

- Create `.env` file in `social-listening/` directory
- Add your OpenAI API key

### "ModuleNotFoundError: No module named 'dotenv'"

- Install dependencies: `pip install python-dotenv requests jsonschema`

### "Rate limit exceeded"

- Reduce `MAX_DRAFTS_PER_RUN` in `.env`
- Wait and retry later
- Upgrade OpenAI API tier if needed

## Testing

Run the test suite to verify functionality:

```bash
cd social-listening
python3 tests/test_content_generation.py
```

## Disabling Content Generation

Set in `.env`:

```bash
CONTENT_GENERATION_ENABLED=false
```

The script will exit gracefully without processing any opportunities.

## Best Practices

1. **Start small**: Set `MAX_DRAFTS_PER_RUN=1` for first run
2. **Monitor logs**: Check `logs/content_generation.log` for issues
3. **Review drafts**: Always review "Draft Ready for Review" items before publishing
4. **Schedule runs**: Use cron or GitHub Actions for automated execution
5. **Track costs**: Monitor OpenAI API usage, especially with gpt-4o

## Support

For issues or questions:
- Check logs in `logs/content_generation.log`
- Review test suite in `tests/test_content_generation.py`
- Verify configuration in `config/notion.json` and `.env`
