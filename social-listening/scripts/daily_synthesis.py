import os
import json
import datetime as dt
import requests
from dotenv import load_dotenv
from jsonschema import validate

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CFG_PATH = os.path.join(ROOT, "config", "notion.json")

NOTION_VERSION = "2022-06-28"
OPENAI_URL = "https://api.openai.com/v1/chat/completions"

# -------- Notion property names (adjust ONLY if your DB uses different names) --------
# Mentions DB
MENTIONS_DETECTED_AT = "Detected At"
MENTIONS_SYNTHED_AT = "Synthesized At"      # NEW: Date property you must add
MENTIONS_PLATFORM = "Platform"
MENTIONS_URL = "URL"
MENTIONS_AUTHOR = "Author"
MENTIONS_SOURCE_TEXT = "Source Text"
MENTIONS_SOURCE_QUERY = "Source Query"      # optional

# Content DB (required)
CONTENT_TOPIC = "Topic"
CONTENT_AUDIENCE = "Audience"
CONTENT_PLATFORM_TARGET = "Platform Target"
CONTENT_PRIORITY = "Priority"
CONTENT_STATUS = "Status"
CONTENT_SOURCE_MENTIONS = "Source Mentions"

# Content DB (optional; only written if present)
CONTENT_HOOK = "Hook"
CONTENT_KEY_POINTS = "Key Points"
CONTENT_PROOF_POINTS = "Proof Points"
CONTENT_SOURCE_LINKS = "Source Links"

ALLOWED_AUDIENCE = ["CashBuyer", "Operator", "HNWI/LP"]
ALLOWED_PLATFORM_TARGET = ["BiggerPockets", "LinkedIn", "X", "Substack"]
DEFAULT_STATUS = "Backlog"

SYNTHESIS_SCHEMA = {
    "type": "object",
    "additionalProperties": False,
    "required": ["topics"],
    "properties": {
        "topics": {
            "type": "array",
            "minItems": 1,
            "maxItems": 3,
            "items": {
                "type": "object",
                "additionalProperties": False,
                "required": [
                    "topic", "audience", "platform_target", "priority",
                    "hook", "key_points", "proof_points", "mention_ids"
                ],
                "properties": {
                    "topic": {"type": "string", "minLength": 5},
                    "audience": {"type": "string"},
                    "platform_target": {"type": "string"},
                    "priority": {"type": "integer", "minimum": 1, "maximum": 5},
                    "hook": {"type": "string"},
                    "key_points": {"type": "array", "items": {"type": "string"}, "minItems": 3, "maxItems": 10},
                    "proof_points": {"type": "array", "items": {"type": "string"}, "minItems": 0, "maxItems": 8},
                    "mention_ids": {"type": "array", "items": {"type": "string"}, "minItems": 1, "maxItems": 15},
                },
            },
        },
    },
}

def iso_utc(x: dt.datetime) -> str:
    if x.tzinfo is None:
        x = x.replace(tzinfo=dt.UTC)
    else:
        x = x.astimezone(dt.UTC)
    return x.replace(microsecond=0).isoformat()  # +00:00

def load_cfg():
    with open(CFG_PATH, "r") as f:
        return json.load(f)

def notion_headers(token: str):
    return {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
        "Notion-Version": NOTION_VERSION,
    }

def notion_get_database(token: str, db_id: str) -> dict:
    r = requests.get(
        f"https://api.notion.com/v1/databases/{db_id}",
        headers=notion_headers(token),
        timeout=60
    )
    r.raise_for_status()
    return r.json()

def notion_query_database(token: str, db_id: str, payload: dict):
    url = f"https://api.notion.com/v1/databases/{db_id}/query"
    out = []
    cursor = None
    while True:
        p = dict(payload)
        if cursor:
            p["start_cursor"] = cursor
        r = requests.post(url, headers=notion_headers(token), json=p, timeout=60)
        r.raise_for_status()
        data = r.json()
        out.extend(data.get("results", []))
        if not data.get("has_more"):
            break
        cursor = data.get("next_cursor")
    return out

def notion_create_page(token: str, parent_db_id: str, props: dict):
    r = requests.post(
        "https://api.notion.com/v1/pages",
        headers=notion_headers(token),
        json={"parent": {"database_id": parent_db_id}, "properties": props},
        timeout=60
    )
    r.raise_for_status()
    return r.json()

def notion_update_page(token: str, page_id: str, props: dict):
    r = requests.patch(
        f"https://api.notion.com/v1/pages/{page_id}",
        headers=notion_headers(token),
        json={"properties": props},
        timeout=60
    )
    r.raise_for_status()
    return r.json()

def prop_text(p: dict):
    t = p.get("type")
    if t == "title":
        return "".join(x.get("plain_text", "") for x in p.get("title", [])).strip()
    if t == "rich_text":
        return "".join(x.get("plain_text", "") for x in p.get("rich_text", [])).strip()
    if t == "url":
        return (p.get("url") or "").strip()
    if t == "select":
        sel = p.get("select")
        return (sel.get("name") if sel else "").strip()
    if t == "multi_select":
        return [x.get("name", "") for x in p.get("multi_select", [])]
    if t == "number":
        return p.get("number")
    if t == "checkbox":
        return bool(p.get("checkbox"))
    if t == "relation":
        return p.get("relation", [])
    if t == "date":
        d = p.get("date") or {}
        return d.get("start")
    return ""

def normalize_choice(value: str, allowed: list[str], default: str) -> str:
    if not isinstance(value, str):
        return default
    v = value.strip()
    if v in allowed:
        return v
    for a in allowed:
        if a.lower() == v.lower():
            return a
    return default

def clean_bullets(items, max_n):
    if not isinstance(items, list):
        return []
    out, seen = [], set()
    for x in items:
        if not isinstance(x, str):
            continue
        s = " ".join(x.strip().split())
        if not s:
            continue
        k = s.lower()
        if k in seen:
            continue
        seen.add(k)
        out.append(s)
        if len(out) >= max_n:
            break
    return out

def openai_synthesize(api_key: str, model: str, mentions: list[dict], topics_max: int):
    system = f"""You produce DAILY CONTENT IDEAS from social listening mentions.

Return ONLY a single JSON object. No markdown. No commentary.
Follow the output shape exactly.

Create 1 to {topics_max} high-signal topics from the mentions.
Each topic must link to 2–15 mention_ids from the input list. If you cannot find at least 2 mention_ids for a topic, do NOT include that topic.
Prefer themes that recur or show strong operator pain.

ENUMS (case-sensitive):
- audience: {ALLOWED_AUDIENCE}
- platform_target: {ALLOWED_PLATFORM_TARGET}
- priority: integer 1–5 where 1 is highest urgency/value.

OUTPUT SHAPE:
{{
  "topics": [
    {{
      "topic": "string",
      "audience": "CashBuyer|Operator|HNWI/LP",
      "platform_target": "BiggerPockets|LinkedIn|X|Substack",
      "priority": 1-5,
      "hook": "1–2 lines",
      "key_points": ["3–10 bullets"],
      "proof_points": ["0–8 bullets"],
      "mention_ids": ["2–15 ids from input"]
    }}
  ]
}}
"""
    payload = {
        "model": model,
        "messages": [
            {"role": "system", "content": system},
            {"role": "user", "content": json.dumps({"mentions": mentions, "topics_max": topics_max}, ensure_ascii=False)},
        ],
        "temperature": 0.2,
        "response_format": {"type": "json_object"},
    }
    r = requests.post(
        OPENAI_URL,
        headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
        json=payload,
        timeout=90,
    )
    r.raise_for_status()
    data = json.loads(r.json()["choices"][0]["message"]["content"])
    validate(instance=data, schema=SYNTHESIS_SCHEMA)

    for t in data.get("topics", []):
        if isinstance(t.get("topic"), str):
            t["topic"] = " ".join(t["topic"].strip().split())[:120]
        t["key_points"] = clean_bullets(t.get("key_points"), 10)
        t["proof_points"] = clean_bullets(t.get("proof_points"), 8)
        mids = [m for m in t.get("mention_ids", []) if isinstance(m, str) and m.strip()]
        t["mention_ids"] = list(dict.fromkeys(mids))[:15]
    return data

def preflight_db(token: str, db_id: str, required_props: set[str], label: str) -> set[str]:
    schema = notion_get_database(token, db_id)
    prop_names = set((schema.get("properties") or {}).keys())
    missing = sorted(list(required_props - prop_names))
    if missing:
        print(f"{label} DB missing properties:", missing)
        print(f"{label} DB available properties:", sorted(list(prop_names)))
        return set()
    return prop_names

def main():
    load_dotenv(os.path.join(ROOT, ".env"), override=True)

    notion_token = os.getenv("NOTION_TOKEN", "")
    openai_key = os.getenv("OPENAI_API_KEY", "")
    if not notion_token:
        raise SystemExit("NOTION_TOKEN missing in .env")
    if not openai_key:
        raise SystemExit("OPENAI_API_KEY missing in .env")

    cfg = load_cfg()
    mentions_db = cfg["mentions_db_id"]
    content_db = cfg["content_db_id"]

    hours = int(os.getenv("SYNTH_WINDOW_HOURS", "24"))
    max_mentions = int(os.getenv("SYNTH_MAX_MENTIONS", "60"))
    topics_max = int(os.getenv("SYNTH_TOPICS_MAX", "3"))
    model = os.getenv("MODEL_SYNTHESIS", "gpt-4o-mini")

    mentions_required = {
        MENTIONS_DETECTED_AT, MENTIONS_SYNTHED_AT,
        MENTIONS_PLATFORM, MENTIONS_URL, MENTIONS_AUTHOR, MENTIONS_SOURCE_TEXT
    }
    mentions_prop_names = preflight_db(notion_token, mentions_db, mentions_required, "Mentions")
    if not mentions_prop_names:
        print("Fix: ensure Mentions has 'Synthesized At' (Date) and update constants if names differ.")
        return

    content_required = {
        CONTENT_TOPIC, CONTENT_AUDIENCE, CONTENT_PLATFORM_TARGET,
        CONTENT_PRIORITY, CONTENT_STATUS, CONTENT_SOURCE_MENTIONS
    }
    content_prop_names = preflight_db(notion_token, content_db, content_required, "Content")
    if not content_prop_names:
        print("Fix: update Content constants at top of scripts/daily_synthesis.py to match your DB.")
        return

    now = dt.datetime.now(dt.UTC)
    start = now - dt.timedelta(hours=hours)

    # Eligibility is now based on Synthesized At, NOT the Content Queue relation.
    mentions_pages = notion_query_database(
        notion_token,
        mentions_db,
        {
            "filter": {
                "and": [
                    {"property": MENTIONS_DETECTED_AT, "date": {"on_or_after": iso_utc(start)}},
                    {"property": MENTIONS_SYNTHED_AT, "date": {"is_empty": True}},
                ]
            },
            "sorts": [{"property": MENTIONS_DETECTED_AT, "direction": "descending"}],
            "page_size": 100,
        },
    )

    if not mentions_pages:
        print("No mentions eligible (Detected At window + Synthesized At empty).")
        return

    mentions_pages = mentions_pages[:max_mentions]
    mentions = []
    for pg in mentions_pages:
        pr = pg.get("properties", {})
        mentions.append({
            "id": pg.get("id"),
            "platform": prop_text(pr.get(MENTIONS_PLATFORM, {})),
            "url": prop_text(pr.get(MENTIONS_URL, {})),
            "author": prop_text(pr.get(MENTIONS_AUTHOR, {})),
            "text": prop_text(pr.get(MENTIONS_SOURCE_TEXT, {})),
            "source_query": prop_text(pr.get(MENTIONS_SOURCE_QUERY, {})) if MENTIONS_SOURCE_QUERY in mentions_prop_names else "",
        })

    synth = openai_synthesize(openai_key, model, mentions, topics_max)

    id_to_url = {m["id"]: m.get("url", "") for m in mentions}
    created = 0
    touched_mentions = set()

    for t in synth.get("topics", []):
        topic = (t.get("topic") or "").strip()
        if len(topic) < 5:
            continue

        mention_ids = list(dict.fromkeys(t.get("mention_ids", [])))[:15]
        if len(mention_ids) < 2:
            continue

        audience = normalize_choice(t.get("audience", ""), ALLOWED_AUDIENCE, "Operator")
        platform_target = normalize_choice(t.get("platform_target", ""), ALLOWED_PLATFORM_TARGET, "BiggerPockets")
        priority = max(1, min(5, int(t.get("priority", 3))))
        source_links = "\n".join([id_to_url.get(mid, "") for mid in mention_ids if id_to_url.get(mid, "")])[:1800]

        page_props = {
            CONTENT_TOPIC: {"title": [{"text": {"content": topic}}]},
            CONTENT_AUDIENCE: {"select": {"name": audience}},
            CONTENT_PLATFORM_TARGET: {"select": {"name": platform_target}},
            CONTENT_PRIORITY: {"number": priority},
            CONTENT_STATUS: {"status": {"name": DEFAULT_STATUS}},
            CONTENT_SOURCE_MENTIONS: {"relation": [{"id": mid} for mid in mention_ids]},
        }

        if CONTENT_HOOK in content_prop_names:
            page_props[CONTENT_HOOK] = {"rich_text": [{"text": {"content": (t.get("hook") or "").strip()[:1800]}}]}
        if CONTENT_KEY_POINTS in content_prop_names:
            kp = "\n".join([f"- {x}" for x in (t.get("key_points") or [])])[:1800]
            page_props[CONTENT_KEY_POINTS] = {"rich_text": [{"text": {"content": kp}}]}
        if CONTENT_PROOF_POINTS in content_prop_names:
            pp = "\n".join([f"- {x}" for x in (t.get("proof_points") or [])])[:1800]
            page_props[CONTENT_PROOF_POINTS] = {"rich_text": [{"text": {"content": pp}}]}
        if CONTENT_SOURCE_LINKS in content_prop_names:
            page_props[CONTENT_SOURCE_LINKS] = {"rich_text": [{"text": {"content": source_links}}]}

        page = notion_create_page(notion_token, content_db, page_props)
        created += 1
        print("CREATED Content:", page.get("id"), "|", topic)
        touched_mentions.update(mention_ids)

    # Mark used mentions as synthesized
    if touched_mentions:
        stamp = iso_utc(dt.datetime.now(dt.UTC))
        for mid in touched_mentions:
            notion_update_page(notion_token, mid, {MENTIONS_SYNTHED_AT: {"date": {"start": stamp}}})
        print("Marked Synthesized At on mentions:", len(touched_mentions))

    if created == 0:
        print("No new Content items created (no valid topics or all skipped).")
    else:
        print(f"Done. Created {created} Content item(s).")

if __name__ == "__main__":
    main()
