#!/usr/bin/env python3
import os, json, time, requests
from dotenv import load_dotenv
from jsonschema import validate

ROOT = os.path.expanduser("~/ContentOps/social-listening")
load_dotenv(os.path.join(ROOT, ".env"), override=True)

OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY")
NOTION_TOKEN   = os.environ.get("NOTION_TOKEN")

MODEL_TRIAGE = os.environ.get("OPENAI_MODEL_TRIAGE", "gpt-4o-mini")
MODEL_HIGH   = os.environ.get("OPENAI_MODEL_HIGH", "gpt-5.2")

if not OPENAI_API_KEY:
    raise SystemExit("OPENAI_API_KEY missing in .env")
if not NOTION_TOKEN:
    raise SystemExit("NOTION_TOKEN missing in .env")

with open(os.path.join(ROOT, "config/notion.json")) as f:
    cfg = json.load(f)

MENTIONS_DB_ID    = cfg["mentions_db_id"]
LEADS_DB_ID       = cfg["leads_db_id"]
REPUTATION_DB_ID  = cfg["reputation_db_id"]
CONTENT_DB_ID     = cfg["content_db_id"]

NOTION_HEADERS = {
    "Authorization": f"Bearer {NOTION_TOKEN}",
    "Content-Type": "application/json",
    "Notion-Version": "2022-06-28",
}
OPENAI_HEADERS = {
    "Authorization": f"Bearer {OPENAI_API_KEY}",
    "Content-Type": "application/json",
}

# Model must return STRICT JSON matching this schema (keys + types)
TRIAGE_SCHEMA = {
  "type":"object",
  "additionalProperties": False,
  "required": ["sentiment","priority","compliance_mode","routes","entities","metros","confidence",
               "lead","reputation","content","notes"],
  "properties": {
    "sentiment": {"type":"string","enum":["Positive","Neutral","Negative","Mixed"]},
    "priority": {"type":"integer","minimum":1,"maximum":5},
    "compliance_mode": {"type":"boolean"},
    "routes": {
      "type":"object",
      "additionalProperties": False,
      "required": ["lead","reputation","content"],
      "properties": {
        "lead": {"type":"boolean"},
        "reputation": {"type":"boolean"},
        "content": {"type":"boolean"}
      }
    },
    "entities": {"type":"array","items":{"type":"string"}, "maxItems": 20},
    "metros": {"type":"array","items":{"type":"string"}, "maxItems": 10},
    "confidence": {"type":"number","minimum":0,"maximum":1},

    "lead": {
      "type":"object",
      "additionalProperties": False,
      "required": ["title","draft_reply"],
      "properties": {
        "title": {"type":"string"},
        "draft_reply": {"type":"string"}
      }
    },
    "reputation": {
      "type":"object",
      "additionalProperties": False,
      "required": ["title","draft_reply","risk_level"],
      "properties": {
        "title": {"type":"string"},
        "draft_reply": {"type":"string"},
        "risk_level": {"type":"string","enum":["Low","Medium","High"]}
      }
    },
    "content": {
      "type":"object",
      "additionalProperties": False,
      "required": ["title","angle","outline_bullets","canva_prompts"],
      "properties": {
        "title": {"type":"string"},
        "angle": {"type":"string"},
        "outline_bullets": {"type":"array","items":{"type":"string"}, "maxItems": 12},
        "canva_prompts": {"type":"array","items":{"type":"string"}, "maxItems": 6}
      }
    },
    "notes": {"type":"string"}
  }
}

def notion_get_database(db_id: str) -> dict:
    r = requests.get(f"https://api.notion.com/v1/databases/{db_id}", headers=NOTION_HEADERS, timeout=60)
    r.raise_for_status()
    return r.json()

def notion_query(db_id: str, payload: dict) -> list[dict]:
    r = requests.post(f"https://api.notion.com/v1/databases/{db_id}/query",
                      headers=NOTION_HEADERS, json=payload, timeout=60)
    r.raise_for_status()
    return r.json().get("results", [])

def notion_update_page(page_id: str, properties: dict) -> None:
    r = requests.patch(f"https://api.notion.com/v1/pages/{page_id}",
                       headers=NOTION_HEADERS, json={"properties": properties}, timeout=60)
    r.raise_for_status()

def notion_create_page(db_id: str, properties: dict) -> str:
    r = requests.post("https://api.notion.com/v1/pages",
                      headers=NOTION_HEADERS,
                      json={"parent":{"database_id": db_id}, "properties": properties},
                      timeout=60)
    r.raise_for_status()
    return r.json()["id"]

def title_prop_name(db_schema: dict) -> str:
    for name, p in db_schema.get("properties", {}).items():
        if p.get("type") == "title":
            return name
    raise RuntimeError("No title property found in target database schema")

def rt_text(prop: dict) -> str:
    t = prop.get("type")
    if t == "title":
        return "".join(x.get("plain_text","") for x in prop.get("title", []))
    if t == "rich_text":
        return "".join(x.get("plain_text","") for x in prop.get("rich_text", []))
    return ""

def prop_value(prop: dict):
    t = prop.get("type")
    if t == "select":
        s = prop.get("select")
        return s.get("name") if s else None
    if t == "multi_select":
        return [x.get("name") for x in prop.get("multi_select", []) if x.get("name")]
    if t == "url":
        return prop.get("url")
    if t == "date":
        d = prop.get("date")
        return d.get("start") if d else None
    if t == "number":
        return prop.get("number")
    if t == "checkbox":
        return bool(prop.get("checkbox"))
    if t in ("title","rich_text"):
        return rt_text(prop)
    if t == "relation":
        return [x.get("id") for x in prop.get("relation", []) if x.get("id")]
    return None

def openai_classify(model: str, mention: dict, prior: dict | None = None) -> dict:
    system = """You are a triage + routing engine for social listening mentions for a real estate investor / fund operator.

Return ONLY a single JSON object. No markdown. No explanations. No extra keys.
All keys MUST be present even if values are empty.
Use EXACT casing for enumerations (case-sensitive).

OUTPUT MUST MATCH THIS EXACT SHAPE:
{
  "sentiment": "Positive" | "Neutral" | "Negative" | "Mixed",
  "priority": 1 | 2 | 3 | 4 | 5,
  "compliance_mode": true | false,
  "routes": { "lead": true|false, "reputation": true|false, "content": true|false },
  "entities": [string],
  "metros": [string],
  "confidence": number,

  "lead": { "title": string, "draft_reply": string },

  "reputation": { "title": string, "draft_reply": string, "risk_level": "Low" | "Medium" | "High" },

  "content": { "title": string, "angle": string, "outline_bullets": [string], "canva_prompts": [string] },

  "notes": string
}

DECISION RULES:
- routes.lead = true if the author is asking for funding, a lender, JV, deal help, investor services, referrals/recommendations, or a direct connection.
- routes.reputation = true if there are complaints, accusations, threats, fraud/scam claims, legal disputes, or reputational risk about a person/company.
- routes.content = true if the theme is broadly educational and could become a BiggerPockets-style blog topic.
- compliance_mode = true if ANY of the following are present: allegations, disputes, threats, doxxing, licensing claims, fraud/scam/illegal activity claims, anything legally sensitive.
  When compliance_mode = true, draft replies must be conservative: no admissions, no accusations, no promises; suggest moving to private channel and/or consulting counsel.

PRIORITY (1 is highest urgency):
1 = urgent, high-stakes, time-sensitive, strong lead intent OR high reputation risk
2 = important, high-value lead OR material reputation concern
3 = normal lead/content opportunity
4 = low impact informational
5 = noise / very low signal

FIELD POPULATION RULES (IMPORTANT):
- If routes.lead is false: set lead.title="" and lead.draft_reply=""
- If routes.reputation is false: set reputation.title="", reputation.draft_reply="", and reputation.risk_level="Low"
- If routes.content is false: set content.title="", content.angle="", content.outline_bullets=[], content.canva_prompts=[]
- notes: 1–3 short sentences summarizing why you routed/prioritized the way you did.

If prior_triage is provided, use it as a hint but correct it if wrong.
"""

    user_obj = {"mention": mention}
    if prior is not None:
        user_obj["prior_triage"] = prior

    r = requests.post(
      "https://api.openai.com/v1/chat/completions",
      headers=OPENAI_HEADERS,
      json={
        "model": model,
        "messages": [
          {"role":"system","content": system},
          {"role":"user","content": json.dumps(user_obj, ensure_ascii=False)}
        ],
        "temperature": 0.2,
        "response_format": {"type":"json_object"}
      },
      timeout=90
    )
    r.raise_for_status()
    data = json.loads(r.json()["choices"][0]["message"]["content"])
    # BEGIN_NORMALIZE_OPENAI_OUTPUT
    # Normalize common model deviations (case + types) so they match schema + Notion fields.
    if isinstance(data.get("sentiment"), str):
        _s = data["sentiment"].strip().lower()
        data["sentiment"] = {"positive":"Positive","neutral":"Neutral","negative":"Negative","mixed":"Mixed"}.get(_s, data["sentiment"])

    # Ensure nested objects exist
    if not isinstance(data.get("lead"), dict):
        data["lead"] = {}
    if not isinstance(data.get("reputation"), dict):
        data["reputation"] = {}
    if not isinstance(data.get("content"), dict):
        data["content"] = {}
    if not isinstance(data.get("routes"), dict):
        data["routes"] = {}

    # Fill required keys (safe defaults)
    data["lead"].setdefault("title", "")
    data["lead"].setdefault("draft_reply", "")

    data["reputation"].setdefault("title", "")
    data["reputation"].setdefault("draft_reply", "")
    data["reputation"].setdefault("risk_level", "Low")

    data["content"].setdefault("title", "")
    data["content"].setdefault("angle", "")
    data["content"].setdefault("outline_bullets", [])
    data["content"].setdefault("canva_prompts", [])

    data["routes"].setdefault("lead", False)
    data["routes"].setdefault("reputation", False)
    data["routes"].setdefault("content", False)

    # Coerce risk_level into allowed enum (Low/Medium/High)
    rl = data["reputation"].get("risk_level", "Low")
    if isinstance(rl, (int, float)):
        # 0->Low, 1->Medium, 2+->High
        data["reputation"]["risk_level"] = "Low" if rl <= 0 else ("Medium" if rl == 1 else "High")
    elif isinstance(rl, str):
        _rl = rl.strip().lower()
        data["reputation"]["risk_level"] = {"low":"Low","medium":"Medium","high":"High"}.get(_rl, "Low")
    else:
        data["reputation"]["risk_level"] = "Low"

    # Coerce priority (must be int 1-5)
    pr = data.get("priority")
    if isinstance(pr, str) and pr.strip().isdigit():
        data["priority"] = int(pr.strip())
    elif isinstance(pr, float):
        data["priority"] = int(round(pr))

    # Coerce confidence (must be number 0..1)
    cf = data.get("confidence")
    if isinstance(cf, str):
        try:
            data["confidence"] = float(cf.strip())
        except Exception:
            pass

    # Ensure entities/metros are lists
    for key in ("entities", "metros"):
        v = data.get(key, [])
        if isinstance(v, str) and v.strip():
            data[key] = [v.strip()]
        elif not isinstance(v, list):
            data[key] = []

    data.setdefault("notes", "")
    # END_NORMALIZE_OPENAI_OUTPUT

    # Normalize common casing variations so they match schema + Notion select options
    if isinstance(data.get("sentiment"), str):
        _s = data["sentiment"].strip().lower()
        _map = {"positive": "Positive", "neutral": "Neutral", "negative": "Negative", "mixed": "Mixed"}
        if _s in _map:
            data["sentiment"] = _map[_s]

    if isinstance(data.get("reputation"), dict) and isinstance(data["reputation"].get("risk_level"), str):
        _r = data["reputation"]["risk_level"].strip().lower()
        _rmap = {"low": "Low", "medium": "Medium", "high": "High"}
        if _r in _rmap:
            data["reputation"]["risk_level"] = _rmap[_r]
    validate(instance=data, schema=TRIAGE_SCHEMA)
    return data

def should_escalate(t: dict) -> bool:
    return (
      t["compliance_mode"] is True
      or t["routes"]["reputation"] is True
      or t["priority"] <= 2
      or t["confidence"] < 0.7
    )

def main():
    # Validate target DBs (and get title property names)
    leads_schema = notion_get_database(LEADS_DB_ID)
    rep_schema   = notion_get_database(REPUTATION_DB_ID)
    cont_schema  = notion_get_database(CONTENT_DB_ID)

    leads_title_prop = title_prop_name(leads_schema)
    rep_title_prop   = title_prop_name(rep_schema)
    cont_title_prop  = title_prop_name(cont_schema)

    # Pull Mentions needing classification
    # IMPORTANT: these property names must match your Mentions DB exactly.
    results = notion_query(MENTIONS_DB_ID, {
      "filter": {
        "or": [
          {"property":"Sentiment","select":{"is_empty": True}},
          {"property":"Priority","number":{"is_empty": True}}
        ]
      },
      "page_size": 25
    })

    if not results:
        print("No untriaged Mentions found.")
        return

    for page in results:
        pid = page["id"]
        props = page["properties"]

        mention = {
          "platform": prop_value(props["Platform"]) or "Other",
          "url": prop_value(props["URL"]) or "",
          "text": prop_value(props["Source Text"]) or "",
          "author": prop_value(props["Author"]) or "",
          "created_at": prop_value(props["Post Created At"]) or "",
          "source_query": prop_value(props["Source Query"]) or ""
        }

        if not mention["url"] or not mention["text"]:
            print("SKIP missing url/text:", pid)
            continue

        # Pass 1: cheap triage
        triage = openai_classify(MODEL_TRIAGE, mention)

        # Pass 2: escalate if needed
        final = triage
        used_model = "TRIAGE"
        if should_escalate(triage):
            final = openai_classify(MODEL_HIGH, mention, prior=triage)
            used_model = "HIGH"

        # Update Mentions (assumes these properties exist in Mentions DB)
        notion_update_page(pid, {
          "Sentiment": {"select": {"name": final["sentiment"]}},
          "Priority": {"number": final["priority"]},
          "Compliance Mode": {"checkbox": bool(final["compliance_mode"])},
          "Entities": {"multi_select": [{"name": x} for x in final["entities"]]},
          "Metro": {"multi_select": [{"name": x} for x in final["metros"]]}
        })

        # Create queue items only if route=true AND no existing relation yet
        existing_leads = prop_value(props["Leads Queue"]) or []
        existing_rep   = prop_value(props["Reputation Queue"]) or []
        existing_cont  = prop_value(props["Content Queue"]) or []

        if final["routes"]["lead"] and not existing_leads:
            title = (final["lead"]["title"] or f"Lead — {mention['platform']} — {mention['author']}").strip()
            lead_id = notion_create_page(LEADS_DB_ID, {
              leads_title_prop: {"title": [{"text": {"content": title}}]}
            })
            notion_update_page(pid, {"Leads Queue": {"relation": [{"id": lead_id}]}})

        if final["routes"]["reputation"] and not existing_rep:
            title = (final["reputation"]["title"] or f"Reputation — {mention['platform']} — {mention['author']}").strip()
            rep_id = notion_create_page(REPUTATION_DB_ID, {
              rep_title_prop: {"title": [{"text": {"content": title}}]}
            })
            notion_update_page(pid, {"Reputation Queue": {"relation": [{"id": rep_id}]}})

        if final["routes"]["content"] and not existing_cont:
            title = (final["content"]["title"] or f"Content — {mention['platform']} — {mention['author']}").strip()
            cont_id = notion_create_page(CONTENT_DB_ID, {
              cont_title_prop: {"title": [{"text": {"content": title}}]}
            })
            notion_update_page(pid, {"Content Queue": {"relation": [{"id": cont_id}]}})

        print(f"TRIAGED: {pid} | {final['sentiment']} P{final['priority']} | {used_model} | routes={final['routes']}")
        time.sleep(0.25)

if __name__ == "__main__":
    main()
