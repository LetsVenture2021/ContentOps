import os, json, requests
from datetime import datetime, timezone
from dotenv import load_dotenv

load_dotenv(os.path.expanduser("~/ContentOps/social-listening/.env"))

NOTION_TOKEN = os.environ.get("NOTION_TOKEN")
if not NOTION_TOKEN:
    raise SystemExit("NOTION_TOKEN not set in .env")

with open(os.path.expanduser("~/ContentOps/social-listening/config/notion.json")) as f:
    cfg = json.load(f)

MENTIONS_DB_ID = cfg["mentions_db_id"]
now = datetime.now(timezone.utc).isoformat()

payload = {
  "parent": {"database_id": MENTIONS_DB_ID},
  "properties": {
    "Mention": {"title": [{"text": {"content": "Smoke Test — Reddit — user123"}}]},
    "Platform": {"select": {"name": "Reddit"}},
    "URL": {"url": "https://example.com/post"},
    "Source Text": {"rich_text": [{"text": {"content": "Anyone recommend a hard money lender in Houston? Need 30 day close."}}]},
    "Author": {"rich_text": [{"text": {"content": "user123"}}]},
    "Post Created At": {"date": {"start": "2025-12-15T10:00:00Z"}},
    "Detected At": {"date": {"start": now}},
    "Source Query": {"rich_text": [{"text": {"content": "hard money + houston"}}]},
    "Fingerprint": {"rich_text": [{"text": {"content": "Reddit|https://example.com/post"}}]}
  }
}

r = requests.post(
  "https://api.notion.com/v1/pages",
  headers={
    "Authorization": f"Bearer {NOTION_TOKEN}",
    "Content-Type": "application/json",
    "Notion-Version": "2022-06-28"
  },
  json=payload,
  timeout=60
)

print("Status:", r.status_code)
print(r.text)
r.raise_for_status()
print("OK: created a Mentions row")
