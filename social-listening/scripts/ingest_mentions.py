import os, json, glob, shutil, requests
from datetime import datetime, timezone
from dotenv import load_dotenv
from jsonschema import validate

ROOT = os.path.expanduser("~/ContentOps/social-listening")
INBOX = os.path.join(ROOT, "inbox")
PROCESSED = os.path.join(ROOT, "processed")
CONFIG = os.path.join(ROOT, "config")

load_dotenv(os.path.join(ROOT, ".env"), override=True)

NOTION_TOKEN = os.environ.get("NOTION_TOKEN")
if not NOTION_TOKEN:
    raise SystemExit("NOTION_TOKEN not set. Add it to .env (no quotes).")

with open(os.path.join(CONFIG, "notion.json")) as f:
    notion_cfg = json.load(f)

MENTIONS_DB_ID = notion_cfg["mentions_db_id"]

with open(os.path.join(CONFIG, "mention_schema.json")) as f:
    mention_schema = json.load(f)

HEADERS = {
    "Authorization": f"Bearer {NOTION_TOKEN}",
    "Content-Type": "application/json",
    "Notion-Version": "2022-06-28"
}

def notion_find_by_fingerprint(fingerprint: str) -> bool:
    url = f"https://api.notion.com/v1/databases/{MENTIONS_DB_ID}/query"
    payload = {
        "filter": {
            "property": "Fingerprint",
            "rich_text": {"equals": fingerprint}
        }
    }
    r = requests.post(url, headers=HEADERS, json=payload, timeout=60)
    r.raise_for_status()
    return len(r.json().get("results", [])) > 0

def notion_create_mention(m: dict) -> str:
    now = datetime.now(timezone.utc).isoformat()
    fingerprint = f"{m['platform']}|{m['url']}"
    title = f"{m['platform']} — {m['author']} — {m['text'][:60]}".replace("\n", " ").strip()

    payload = {
      "parent": {"database_id": MENTIONS_DB_ID},
      "properties": {
        "Mention": {"title": [{"text": {"content": title}}]},
        "Platform": {"select": {"name": m["platform"]}},
        "URL": {"url": m["url"]},
        "Source Text": {"rich_text": [{"text": {"content": m["text"]}}]},
        "Author": {"rich_text": [{"text": {"content": m["author"]}}]},
        "Post Created At": {"date": {"start": m["created_at"]}},
        "Detected At": {"date": {"start": now}},
        "Source Query": {"rich_text": [{"text": {"content": m.get("source_query","")}}]},
        "Fingerprint": {"rich_text": [{"text": {"content": fingerprint}}]}
      }
    }

    r = requests.post("https://api.notion.com/v1/pages", headers=HEADERS, json=payload, timeout=60)
    r.raise_for_status()
    return r.json()["id"]

def main():
    os.makedirs(PROCESSED, exist_ok=True)

    files = sorted(glob.glob(os.path.join(INBOX, "*.json")))
    if not files:
        print("No inbox/*.json files found.")
        return

    for fp in files:
        with open(fp) as f:
            mention = json.load(f)

        validate(instance=mention, schema=mention_schema)

        fingerprint = f"{mention['platform']}|{mention['url']}"

        if notion_find_by_fingerprint(fingerprint):
            print("DUPLICATE (skipping):", fingerprint, "|", os.path.basename(fp))
        else:
            page_id = notion_create_mention(mention)
            print("CREATED Mention:", page_id, "|", fingerprint)

        shutil.move(fp, os.path.join(PROCESSED, os.path.basename(fp)))

if __name__ == "__main__":
    main()
