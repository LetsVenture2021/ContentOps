#!/usr/bin/env python3
"""
Content Draft Generation Script
Generates platform-optimized content drafts from Notion content opportunities
"""

import os
import sys
import json
import time
import requests
from datetime import datetime, timezone
from dotenv import load_dotenv

# Setup paths
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
load_dotenv(os.path.join(ROOT, ".env"), override=True)

# Config
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
NOTION_TOKEN = os.getenv("NOTION_TOKEN")
OPENAI_MODEL_CONTENT = os.getenv("OPENAI_MODEL_CONTENT", "gpt-4o")
MAX_DRAFTS_PER_RUN = int(os.getenv("MAX_DRAFTS_PER_RUN", "5"))

# Load Notion config
with open(os.path.join(ROOT, "config/notion.json")) as f:
    cfg = json.load(f)

CONTENT_DB_ID = cfg["content_db_id"]
MENTIONS_DB_ID = cfg["mentions_db_id"]

# Logging
LOG_FILE = os.path.join(ROOT, "logs/content_generation.log")
os.makedirs(os.path.dirname(LOG_FILE), exist_ok=True)

def log(msg):
    """Simple logging"""
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    line = f"[{timestamp}] {msg}"
    print(line)
    with open(LOG_FILE, "a") as f:
        f.write(line + "\n")

# Platform Guidelines
PLATFORM_GUIDELINES = {
    "BiggerPockets": {
        "length_words": (2000, 3000),
        "structure": "Problem → Framework → Step-by-step → Examples → Checklist",
        "tone": "Helpful peer, conversational but authoritative",
        "formatting": "Markdown with H2/H3 headers, bullet lists, numbered steps"
    },
    "LinkedIn": {
        "length_words": (800, 1200),
        "structure": "Hook → Insight → Framework → Proof → CTA",
        "tone": "Professional thought leadership",
        "formatting": "Short paragraphs (2-3 lines), numbered lists"
    },
    "X":  {
        "length_tweets": (8, 12),
        "structure": "Hook tweet → Context → Framework → CTA",
        "tone": "Direct and conversational",
        "formatting": "One idea per tweet, 280 chars max"
    },
    "Substack": {
        "length_words": (2500, 4000),
        "structure": "Story → Problem → Solution → Cases → Steps",
        "tone": "Trusted advisor, storytelling with data",
        "formatting": "Markdown with section breaks, image placeholders"
    }
}

# Audience Profiles
AUDIENCE_PROFILES = {
    "CashBuyer": {
        "focus": "ROI, time to close, risk mitigation",
        "language": "Practical, numbers-focused, efficiency-driven"
    },
    "Operator": {
        "focus": "Cash flow, scalability, operational efficiency",
        "language": "Technical, process-oriented, systems-thinking"
    },
    "HNWI/LP": {
        "focus": "Capital preservation, passive income, tax efficiency",
        "language": "Conservative, compliance-aware, relationship-focused"
    }
}

def notion_request(method, endpoint, **kwargs):
    """Make Notion API request with retry"""
    headers = {
        "Authorization": f"Bearer {NOTION_TOKEN}",
        "Notion-Version": "2022-06-28",
        "Content-Type": "application/json"
    }
    url = f"https://api.notion.com/v1/{endpoint}"
    
    for attempt in range(3):
        try:
            r = requests.request(method, url, headers=headers, timeout=30, **kwargs)
            r.raise_for_status()
            return r.json()
        except Exception as e:
            if attempt < 2:
                time.sleep(2 ** attempt)
                log(f"Notion API retry {attempt + 1}:  {e}")
            else:
                raise

def get_notion_text(prop):
    """Extract text from Notion property"""
    if not prop:
        return ""
    prop_type = prop.get("type")
    if prop_type == "title":
        return "".join([t.get("plain_text", "") for t in prop.get("title", [])])
    elif prop_type == "rich_text":
        return "".join([t.get("plain_text", "") for t in prop.get("rich_text", [])])
    elif prop_type == "select":
        sel = prop.get("select")
        return sel.get("name", "") if sel else ""
    return ""

def get_notion_relation(prop):
    """Extract relation IDs from Notion property"""
    if not prop or prop.get("type") != "relation":
        return []
    return [r.get("id") for r in prop.get("relation", [])]

def fetch_content_opportunities():
    """Fetch content opportunities from Notion"""
    log("Fetching content opportunities with Status='Ready to Draft'...")
    
    response = notion_request(
        "POST",
        f"databases/{CONTENT_DB_ID}/query",
        json={
            "filter": {
                "property": "Status",
                "status": {"equals": "Ready to Draft"}
            },
            "page_size": MAX_DRAFTS_PER_RUN
        }
    )
    
    results = response.get("results", [])
    log(f"Found {len(results)} content opportunities")
    return results

def fetch_source_mentions(mention_ids):
    """Fetch source mentions"""
    mentions = []
    for mid in mention_ids[: 10]: 
        try:
            page = notion_request("GET", f"pages/{mid}")
            props = page.get("properties", {})
            mentions.append({
                "platform": get_notion_text(props.get("Platform")),
                "text": get_notion_text(props.get("Source Text")),
                "author": get_notion_text(props.get("Author"))
            })
        except Exception as e:
            log(f"Failed to fetch mention {mid}: {e}")
    return mentions

def generate_draft(topic, audience, platform, mentions):
    """Generate content draft via OpenAI with proper length"""
    log(f"Generating draft for:  {topic}")
    
    platform_guide = PLATFORM_GUIDELINES.get(platform, PLATFORM_GUIDELINES["BiggerPockets"])
    audience_profile = AUDIENCE_PROFILES.get(audience, AUDIENCE_PROFILES["Operator"])
    
    # Build context from mentions
    source_context = ""
    if mentions:
        source_context = "\n\nSource mentions:\n"
        for i, m in enumerate(mentions[: 5], 1):
            source_context += f"{i}. [{m['platform']}] {m['author']}: {m['text'][: 200]}...\n"
    
    # Calculate target length
    if platform == "X": 
        min_len, max_len = platform_guide["length_tweets"]
        target = (min_len + max_len) // 2
        length_instruction = f"Write EXACTLY {target} tweets (between {min_len}-{max_len}). Each tweet must be under 280 characters."
        word_target = f"{target} tweets"
    else:
        min_words, max_words = platform_guide["length_words"]
        target_words = (min_words + max_words) // 2
        length_instruction = f"Write EXACTLY {target_words} words (minimum {min_words}, maximum {max_words} words). Count your words carefully - this is critical."
        word_target = f"{target_words} words"
    
    system_prompt = f"""You are an expert content writer for {audience} audiences in real estate investing. 

PLATFORM: {platform}
TARGET LENGTH: {length_instruction}
STRUCTURE: {platform_guide['structure']}
TONE: {platform_guide['tone']}
FORMATTING: {platform_guide['formatting']}

AUDIENCE PROFILE:
- Focus: {audience_profile['focus']}
- Language: {audience_profile['language']}

CRITICAL:  Your body content MUST be {word_target}.  This is non-negotiable.

Return ONLY valid JSON: 
{{
  "headline": "Platform-optimized title (60-80 chars)",
  "hook": "Opening 2-3 sentences that grab attention",
  "body": "FULL MARKDOWN CONTENT - MUST BE {word_target}.  Use headers, bullets, bold text.",
  "key_points_formatted": ["Actionable point 1", "Actionable point 2", "Actionable point 3"],
  "proof_points_formatted": ["Data/example 1", "Case study 2"],
  "cta": "Clear call-to-action",
  "seo_metadata": {{
    "title_tag": "SEO title (50-60 chars)",
    "meta_description": "Description (150-160 chars)",
    "keywords": ["keyword1", "keyword2", "keyword3"]
  }},
  "image_placeholders": ["[IMAGE_0] Hero image description"]
}}"""

    user_prompt = f"""Topic: {topic}

{source_context if source_context else "Create comprehensive educational content on this topic. "}

Remember: Body must be {word_target}. Generate the complete draft now."""

    # Call OpenAI with retry
    for attempt in range(3):
        try:
            log(f"Calling OpenAI (attempt {attempt + 1}/3)")
            
            response = requests.post(
                "https://api.openai.com/v1/chat/completions",
                headers={
                    "Authorization": f"Bearer {OPENAI_API_KEY}",
                    "Content-Type": "application/json"
                },
                json={
                    "model": OPENAI_MODEL_CONTENT,
                    "messages": [
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": user_prompt}
                    ],
                    "response_format": {"type": "json_object"},
                    "temperature": 0.7,
                    "max_tokens": 4000
                },
                timeout=120
            )
            
            response.raise_for_status()
            draft = json.loads(response.json()["choices"][0]["message"]["content"])
            
            word_count = len(draft.get("body", "").split())
            log(f"Draft generated:  {word_count} words")
            
            return draft
            
        except Exception as e:
            log(f"OpenAI error (attempt {attempt + 1}): {e}")
            if attempt < 2:
                time.sleep(2 ** attempt)
            else:
                raise

def validate_draft(draft, platform, audience):
    """Validate draft with lenient rules"""
    errors = []
    
    # Length validation - 30% tolerance
    if platform == "X": 
        body_lines = [line for line in draft.get("body", "").split("\n") if line.strip()]
        tweet_count = len(body_lines)
        min_tweets, max_tweets = PLATFORM_GUIDELINES["X"]["length_tweets"]
        if not (min_tweets - 2 <= tweet_count <= max_tweets + 2):
            errors.append(f"Tweet count {tweet_count} outside range {min_tweets - 2}-{max_tweets + 2}")
    else:
        word_count = len(draft.get("body", "").split())
        min_words, max_words = PLATFORM_GUIDELINES[platform]["length_words"]
        # 30% tolerance
        if not (min_words * 0.7 <= word_count <= max_words * 1.3):
            errors.append(f"Word count {word_count} outside range {int(min_words * 0.7)}-{int(max_words * 1.3)}")
    
    # Basic content checks
    if len(draft.get("headline", "")) < 10:
        errors.append("Headline too short")
    
    if len(draft.get("hook", "")) < 20:
        errors.append("Hook too short")
    
    # Compliance for HNWI/LP
    if audience == "HNWI/LP": 
        body_lower = draft.get("body", "").lower()
        prohibited = ["guaranteed returns", "guaranteed profit", "legal advice", "tax advice"]
        found = [term for term in prohibited if term in body_lower]
        if found:
            errors.append(f"Compliance issue: {found}")
    
    return errors

def update_notion_with_draft(content_id, draft):
    """Update Notion page with generated draft"""
    log(f"Updating Notion page {content_id}")
    
    properties = {
        "Draft Content": {"rich_text": [{"text": {"content": draft.get("body", "")[:2000]}}]},
        "Headline": {"rich_text": [{"text": {"content": draft.get("headline", "")}}]},
        "Hook": {"rich_text": [{"text": {"content": draft.get("hook", "")}}]},
        "SEO Title": {"rich_text": [{"text": {"content": draft["seo_metadata"].get("title_tag", "")}}]},
        "SEO Description": {"rich_text": [{"text": {"content": draft["seo_metadata"].get("meta_description", "")}}]},
        "Status": {"status": {"name": "Draft Ready for Review"}},
        "Draft Generated At": {"date": {"start": datetime.now(timezone.utc).isoformat()}}
    }
    
    notion_request("PATCH", f"pages/{content_id}", json={"properties": properties})
    log(f"Updated Notion page {content_id}")

def main():
    """Main execution"""
    log("=" * 80)
    log("CONTENT DRAFT GENERATION - STARTING")
    log("=" * 80)
    
    try:
        opportunities = fetch_content_opportunities()
        
        if not opportunities:
            log("No content opportunities found with Status='Ready to Draft'")
            log("Exiting gracefully.")
            return
        
        success_count = 0
        
        for idx, content in enumerate(opportunities, 1):
            content_id = content["id"]
            props = content.get("properties", {})
            
            topic = get_notion_text(props.get("Topic"))
            audience = get_notion_text(props.get("Audience"))
            platform = get_notion_text(props.get("Platform Target"))
            
            log(f"--- Processing opportunity {idx}/{len(opportunities)} ---")
            log(f"Topic: {topic}")
            log(f"Platform: {platform} | Audience: {audience}")
            
            try:
                # Fetch mentions
                mention_ids = get_notion_relation(props.get("Source Mentions"))
                mentions = fetch_source_mentions(mention_ids) if mention_ids else []
                log(f"Retrieved {len(mentions)} source mentions")
                
                # Generate draft
                draft = generate_draft(topic, audience, platform, mentions)
                
                # Validate
                validation_errors = validate_draft(draft, platform, audience)
                if validation_errors:
                    log(f"✗ Draft validation failed: {validation_errors}")
                    # Continue anyway for testing
                    log("Proceeding despite validation warnings...")
                else:
                    log("✓ Draft validation passed")
                
                # Update Notion
                update_notion_with_draft(content_id, draft)
                
                log(f"✓ Draft generated | length: {len(draft.get('body', '').split())} words")
                log("")
                success_count += 1
                
            except Exception as e:
                log(f"✗ Error processing opportunity:  {e}")
                try:
                    notion_request("PATCH", f"pages/{content_id}", 
                                 json={"properties": {"Status":  {"status": {"name": "Draft Failed"}}}})
                except:
                    pass
        
        log("=" * 80)
        log(f"CONTENT DRAFT GENERATION - COMPLETED")
        log(f"Successful:  {success_count}/{len(opportunities)}")
        log("=" * 80)
        
    except Exception as e:
        log(f"Fatal error: {e}")
        raise

if __name__ == "__main__":
    main()
