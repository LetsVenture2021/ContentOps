#!/usr/bin/env python3
"""
Content Draft Generation Script - Phase 1 of Content Automation Pipeline

This script automatically generates platform-optimized content drafts from content
opportunities identified by the social listening system.

Features:
- Fetches content opportunities from Notion (Status = "Ready to Draft")
- Retrieves source mention context
- Generates platform-specific drafts using OpenAI
- Validates output (JSON structure, length, compliance)
- Updates Notion with generated drafts
"""

import os
import json
import time
import requests
from datetime import datetime, timezone
from dotenv import load_dotenv
from jsonschema import validate

# ============================================================================
# CONFIGURATION
# ============================================================================

# Determine root directory - support both ~/ContentOps and work directory paths
ROOT = os.path.expanduser("~/ContentOps/social-listening")
if not os.path.exists(ROOT):
    # Fallback to script's parent directory
    ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

load_dotenv(os.path.join(ROOT, ".env"), override=True)

# API Credentials
OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY")
NOTION_TOKEN = os.environ.get("NOTION_TOKEN")

# Model Configuration
OPENAI_MODEL_CONTENT = os.environ.get("OPENAI_MODEL_CONTENT", "gpt-4o")
CONTENT_GENERATION_ENABLED = os.environ.get("CONTENT_GENERATION_ENABLED", "true").lower() == "true"
MAX_DRAFTS_PER_RUN = int(os.environ.get("MAX_DRAFTS_PER_RUN", "5"))

if not OPENAI_API_KEY:
    raise SystemExit("OPENAI_API_KEY missing in .env")
if not NOTION_TOKEN:
    raise SystemExit("NOTION_TOKEN missing in .env")

# Load Notion Configuration
with open(os.path.join(ROOT, "config/notion.json")) as f:
    cfg = json.load(f)

MENTIONS_DB_ID = cfg["mentions_db_id"]
CONTENT_DB_ID = cfg["content_db_id"]

# API Headers
NOTION_HEADERS = {
    "Authorization": f"Bearer {NOTION_TOKEN}",
    "Content-Type": "application/json",
    "Notion-Version": "2022-06-28",
}

OPENAI_HEADERS = {
    "Authorization": f"Bearer {OPENAI_API_KEY}",
    "Content-Type": "application/json",
}

# ============================================================================
# PLATFORM GUIDELINES
# ============================================================================

PLATFORM_GUIDELINES = {
    "BiggerPockets": {
        "style": "Educational, detailed, forum post",
        "length": "2000-3000 words",
        "structure": "Problem → Framework → Step-by-step → Examples → Checklist",
        "tone": "Helpful peer, conversational but authoritative",
        "formatting": "Markdown with clear H2/H3 headers, bullet lists, numbered steps",
        "cta": "Download free resource or ask follow-up question"
    },
    "LinkedIn": {
        "style": "Professional thought leadership",
        "length": "800-1200 words",
        "structure": "Hook → Insight → Framework → Proof → CTA",
        "tone": "Industry expert, confident but approachable",
        "formatting": "Short paragraphs (2-3 lines), numbered lists, minimal links",
        "cta": "Comment your experience or connect for discussion"
    },
    "X": {
        "style": "Conversational, punchy thread",
        "length": "8-12 tweets (280 chars each)",
        "structure": "Hook tweet → Context (2-3 tweets) → Framework (4-6 tweets) → Proof (1-2 tweets) → CTA tweet",
        "tone": "Friend sharing valuable insight, direct and clear",
        "formatting": "One idea per tweet, line breaks for readability, minimal hashtags",
        "cta": "Reply with your take or bookmark for later"
    },
    "Substack": {
        "style": "Long-form narrative newsletter",
        "length": "2500-4000 words",
        "structure": "Story opener → Problem deep-dive → Solution framework → Case studies → Actionable steps → Wrap-up",
        "tone": "Trusted advisor, storytelling with data",
        "formatting": "Markdown with section breaks, blockquotes for key points, inline images [IMAGE_0], [IMAGE_1]",
        "cta": "Reply to this email or forward to a colleague"
    }
}

# ============================================================================
# AUDIENCE PROFILES
# ============================================================================

AUDIENCE_PROFILES = {
    "CashBuyer": {
        "pain_points": ["Deal flow quality", "off-market sourcing", "valuation speed", "closing certainty"],
        "priorities": ["ROI", "time to close", "risk mitigation"],
        "language": "Practical, numbers-focused, efficiency-driven"
    },
    "Operator": {
        "pain_points": ["Underwriting accuracy", "financing options", "property management", "exit strategy"],
        "priorities": ["Cash flow", "scalability", "operational efficiency"],
        "language": "Technical, process-oriented, systems-thinking"
    },
    "HNWI/LP": {
        "pain_points": ["Capital deployment", "risk-adjusted returns", "tax efficiency", "sponsor vetting"],
        "priorities": ["Preservation", "passive income", "diversification"],
        "language": "Conservative, compliance-aware, relationship-focused"
    }
}

# ============================================================================
# DRAFT VALIDATION SCHEMA
# ============================================================================

DRAFT_SCHEMA = {
    "type": "object",
    "additionalProperties": False,
    "required": ["headline", "hook", "body", "key_points_formatted", 
                 "proof_points_formatted", "cta", "seo_metadata", 
                 "image_placeholders", "content_structure_notes"],
    "properties": {
        "headline": {"type": "string", "minLength": 10},
        "hook": {"type": "string", "minLength": 20},
        "body": {"type": "string", "minLength": 100},
        "key_points_formatted": {
            "type": "array",
            "items": {"type": "string"},
            "minItems": 3,
            "maxItems": 15
        },
        "proof_points_formatted": {
            "type": "array",
            "items": {"type": "string"},
            "maxItems": 15
        },
        "cta": {"type": "string", "minLength": 10},
        "seo_metadata": {
            "type": "object",
            "required": ["title_tag", "meta_description", "keywords", "suggested_tags"],
            "properties": {
                "title_tag": {"type": "string"},
                "meta_description": {"type": "string"},
                "keywords": {"type": "array", "items": {"type": "string"}},
                "suggested_tags": {"type": "array", "items": {"type": "string"}}
            }
        },
        "image_placeholders": {
            "type": "array",
            "items": {"type": "string"}
        },
        "content_structure_notes": {"type": "string"}
    }
}

# ============================================================================
# NOTION API HELPERS
# ============================================================================

def notion_query(db_id: str, payload: dict) -> list[dict]:
    """Query a Notion database with pagination support."""
    r = requests.post(
        f"https://api.notion.com/v1/databases/{db_id}/query",
        headers=NOTION_HEADERS,
        json=payload,
        timeout=60
    )
    r.raise_for_status()
    return r.json().get("results", [])

def notion_get_page(page_id: str) -> dict:
    """Retrieve a single Notion page by ID."""
    r = requests.get(
        f"https://api.notion.com/v1/pages/{page_id}",
        headers=NOTION_HEADERS,
        timeout=60
    )
    r.raise_for_status()
    return r.json()

def notion_update_page(page_id: str, properties: dict) -> None:
    """Update properties of a Notion page."""
    r = requests.patch(
        f"https://api.notion.com/v1/pages/{page_id}",
        headers=NOTION_HEADERS,
        json={"properties": properties},
        timeout=60
    )
    r.raise_for_status()

def prop_value(prop: dict):
    """Extract value from a Notion property."""
    t = prop.get("type")
    if t == "title":
        return "".join(x.get("plain_text", "") for x in prop.get("title", []))
    if t == "rich_text":
        return "".join(x.get("plain_text", "") for x in prop.get("rich_text", []))
    if t == "select":
        s = prop.get("select")
        return s.get("name") if s else None
    if t == "number":
        return prop.get("number")
    if t == "relation":
        return [x.get("id") for x in prop.get("relation", []) if x.get("id")]
    if t == "status":
        s = prop.get("status")
        return s.get("name") if s else None
    return None

# ============================================================================
# CONTENT OPPORTUNITY FETCHING
# ============================================================================

def fetch_content_opportunities() -> list[dict]:
    """
    Fetch content opportunities from Notion with Status = "Ready to Draft".
    
    Returns list of dicts with:
    - page_id: Notion page ID
    - topic: Content title/topic
    - audience: Target audience (CashBuyer | Operator | HNWI/LP)
    - platform_target: Target platform
    - source_mention_ids: List of related mention IDs
    - key_points: Array of key points
    - proof_points: Array of proof points
    - priority: Priority number (1-5)
    """
    log("Fetching content opportunities with Status='Ready to Draft'...")
    
    results = notion_query(CONTENT_DB_ID, {
        "filter": {
            "property": "Status",
            "status": {
                "equals": "Ready to Draft"
            }
        },
        "page_size": MAX_DRAFTS_PER_RUN
    })
    
    opportunities = []
    for page in results:
        props = page["properties"]
        
        opportunity = {
            "page_id": page["id"],
            "topic": prop_value(props.get("Topic", {})) or "Untitled",
            "audience": prop_value(props.get("Audience", {})) or "Operator",
            "platform_target": prop_value(props.get("Platform Target", {})) or "BiggerPockets",
            "source_mention_ids": prop_value(props.get("Source Mentions", {})) or [],
            "key_points": (prop_value(props.get("Key Points", {})) or "").split("\n"),
            "proof_points": (prop_value(props.get("Proof Points", {})) or "").split("\n"),
            "priority": prop_value(props.get("Priority", {})) or 3
        }
        
        # Clean up bullet points
        opportunity["key_points"] = [
            p.strip().lstrip("-").strip() 
            for p in opportunity["key_points"] 
            if p.strip()
        ]
        opportunity["proof_points"] = [
            p.strip().lstrip("-").strip() 
            for p in opportunity["proof_points"] 
            if p.strip()
        ]
        
        opportunities.append(opportunity)
    
    log(f"Found {len(opportunities)} content opportunities")
    return opportunities

# ============================================================================
# SOURCE MENTION RETRIEVAL
# ============================================================================

def retrieve_source_mentions(mention_ids: list[str]) -> list[dict]:
    """
    Retrieve full context for source mentions.
    
    Returns list of dicts with:
    - mention_id: Notion page ID
    - source_text: Full text content
    - platform: Social platform
    - author: Author name
    - url: Source URL
    """
    mentions = []
    
    for mention_id in mention_ids:
        try:
            page = notion_get_page(mention_id)
            props = page["properties"]
            
            mention = {
                "mention_id": mention_id,
                "source_text": prop_value(props.get("Source Text", {})) or "",
                "platform": prop_value(props.get("Platform", {})) or "",
                "author": prop_value(props.get("Author", {})) or "",
                "url": prop_value(props.get("URL", {})) or ""
            }
            mentions.append(mention)
        except Exception as e:
            log(f"WARNING: Failed to retrieve mention {mention_id}: {e}")
    
    return mentions

def format_source_mentions(mentions: list[dict]) -> str:
    """Format source mentions for LLM prompt."""
    if not mentions:
        return "No source mentions available."
    
    formatted = []
    for i, m in enumerate(mentions, 1):
        formatted.append(f"""
[MENTION {i}]
Platform: {m['platform']}
Author: {m['author']}
URL: {m['url']}
Text: {m['source_text'][:500]}...
""")
    
    return "\n".join(formatted)

# ============================================================================
# OPENAI DRAFT GENERATION
# ============================================================================

def generate_draft_with_openai(
    topic: str,
    audience: str,
    platform_target: str,
    priority: int,
    key_points: list[str],
    proof_points: list[str],
    mentions: list[dict],
    max_retries: int = 3
) -> dict:
    """
    Generate platform-optimized content draft using OpenAI.
    
    Returns dict matching DRAFT_SCHEMA.
    """
    system_prompt = f"""You are a content writer specializing in real estate investing for {audience} audiences.

AUDIENCE PROFILE:
{json.dumps(AUDIENCE_PROFILES.get(audience, AUDIENCE_PROFILES["Operator"]), indent=2)}

PLATFORM REQUIREMENTS:
{json.dumps(PLATFORM_GUIDELINES.get(platform_target, PLATFORM_GUIDELINES["BiggerPockets"]), indent=2)}

CONTENT PRINCIPLES:
1. Lead with concrete value (no fluff or generic advice)
2. Use specific numbers, examples, and frameworks
3. Cite real market data when possible
4. Include actionable steps or checklists
5. Avoid: salesy language, hype, unsubstantiated claims
6. Maintain compliance sensitivity (no promises of returns, legal advice, or investment recommendations)

OUTPUT FORMAT (JSON):
{{
  "headline": "Platform-optimized title (50-80 chars for BiggerPockets/LinkedIn, 60-100 for Substack, compelling for X)",
  "hook": "Opening 2-3 sentences that grab attention and establish relevance",
  "body": "Full Markdown-formatted content following platform structure",
  "key_points_formatted": ["Actionable takeaway 1", "Actionable takeaway 2", ...],
  "proof_points_formatted": ["Data point or example 1", "Case study or stat 2", ...],
  "cta": "Platform-appropriate call-to-action",
  "seo_metadata": {{
    "title_tag": "SEO-optimized title (50-60 chars)",
    "meta_description": "Compelling description (150-160 chars)",
    "keywords": ["keyword1", "keyword2", ...],
    "suggested_tags": ["tag1", "tag2", ...]
  }},
  "image_placeholders": ["[IMAGE_0] Hero image description", "[IMAGE_1] Section break", "[IMAGE_2] Social card"],
  "content_structure_notes": "Brief explanation of why you structured it this way for this audience/platform"
}}
"""

    user_prompt = f"""
TOPIC: {topic}
AUDIENCE: {audience}
PLATFORM: {platform_target}
PRIORITY: {priority}

SOURCE MENTIONS (inspiration from real conversations):
{format_source_mentions(mentions)}

KEY POINTS TO COVER:
{chr(10).join(f"- {point}" for point in key_points if point)}

PROOF POINTS TO INCORPORATE:
{chr(10).join(f"- {point}" for point in proof_points if point)}

Generate a complete, publish-ready draft following all platform and audience guidelines.
"""

    for attempt in range(max_retries):
        try:
            r = requests.post(
                "https://api.openai.com/v1/chat/completions",
                headers=OPENAI_HEADERS,
                json={
                    "model": OPENAI_MODEL_CONTENT,
                    "messages": [
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": user_prompt}
                    ],
                    "temperature": 0.3,
                    "response_format": {"type": "json_object"}
                },
                timeout=120
            )
            r.raise_for_status()
            
            draft = json.loads(r.json()["choices"][0]["message"]["content"])
            
            # Validate schema
            validate(instance=draft, schema=DRAFT_SCHEMA)
            
            return draft
            
        except Exception as e:
            log(f"Draft generation attempt {attempt + 1} failed: {e}")
            if attempt < max_retries - 1:
                wait_time = 2 ** attempt  # Exponential backoff
                log(f"Retrying in {wait_time} seconds...")
                time.sleep(wait_time)
            else:
                raise

# ============================================================================
# DRAFT VALIDATION
# ============================================================================

def validate_draft(draft: dict, platform_target: str, audience: str) -> tuple[bool, list[str]]:
    """
    Validate draft against platform guidelines and compliance requirements.
    
    Returns (is_valid, list_of_errors)
    """
    errors = []
    
    # Check length constraints
    body_length = len(draft["body"].split())
    
    length_ranges = {
        "BiggerPockets": (1800, 3300),  # 2000-3000 ±10%
        "LinkedIn": (720, 1320),         # 800-1200 ±10%
        "X": (7, 13),                    # 8-12 tweets ±1
        "Substack": (2250, 4400)         # 2500-4000 ±10%
    }
    
    min_len, max_len = length_ranges.get(platform_target, (0, 999999))
    
    if platform_target == "X":
        # For X, count tweets (split by newlines or tweet markers)
        tweet_count = draft["body"].count("\n\n") + 1
        if tweet_count < min_len or tweet_count > max_len:
            errors.append(f"Tweet count {tweet_count} outside range {min_len}-{max_len}")
    else:
        # For other platforms, count words
        if body_length < min_len or body_length > max_len:
            errors.append(f"Word count {body_length} outside range {min_len}-{max_len}")
    
    # Check compliance language for HNWI/LP audience
    if audience == "HNWI/LP":
        prohibited_terms = [
            "guaranteed returns", "guaranteed profit", "guaranteed roi",
            "legal advice", "tax advice", "investment advice",
            "promise", "assure you will", "you will make"
        ]
        
        body_lower = draft["body"].lower()
        for term in prohibited_terms:
            if term in body_lower:
                errors.append(f"Compliance violation: prohibited term '{term}' found")
    
    # Check required sections exist
    if len(draft.get("headline", "")) < 10:
        errors.append("Headline too short (< 10 chars)")
    
    if len(draft.get("hook", "")) < 20:
        errors.append("Hook too short (< 20 chars)")
    
    if len(draft.get("key_points_formatted", [])) < 3:
        errors.append("Insufficient key points (< 3)")
    
    return (len(errors) == 0, errors)

# ============================================================================
# NOTION UPDATE
# ============================================================================

def update_notion_with_draft(content_id: str, draft: dict, validation_errors: list[str] = None) -> None:
    """Update Notion Content DB with generated draft."""
    
    if validation_errors:
        # Mark as failed
        log(f"Draft validation failed for {content_id}: {validation_errors}")
        notion_update_page(content_id, {
            "Status": {"status": {"name": "Draft Failed"}},
            "Content Structure Notes": {
                "rich_text": [{"text": {"content": f"Validation errors: {', '.join(validation_errors)}"}}]
            }
        })
        return
    
    # Prepare properties
    properties = {
        "Draft Content": {"rich_text": [{"text": {"content": draft["body"][:2000]}}]},
        "Headline": {"rich_text": [{"text": {"content": draft["headline"][:2000]}}]},
        "Hook": {"rich_text": [{"text": {"content": draft["hook"][:2000]}}]},
        "SEO Title": {"rich_text": [{"text": {"content": draft["seo_metadata"]["title_tag"][:2000]}}]},
        "SEO Description": {"rich_text": [{"text": {"content": draft["seo_metadata"]["meta_description"][:2000]}}]},
        "SEO Keywords": {"multi_select": [{"name": kw[:100]} for kw in draft["seo_metadata"]["keywords"][:20]]},
        "Image Placeholders": {"rich_text": [{"text": {"content": "\n".join(draft["image_placeholders"])[:2000]}}]},
        "Status": {"status": {"name": "Draft Ready for Review"}},
        "Draft Generated At": {"date": {"start": datetime.now(timezone.utc).isoformat()}},
        "Content Structure Notes": {"rich_text": [{"text": {"content": draft["content_structure_notes"][:2000]}}]}
    }
    
    notion_update_page(content_id, properties)
    log(f"Updated Notion page {content_id} with draft")

# ============================================================================
# LOGGING
# ============================================================================

def log(message: str) -> None:
    """Log message with timestamp."""
    timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")
    log_message = f"[{timestamp}] {message}"
    print(log_message)
    
    # Also write to log file
    log_file = os.path.join(ROOT, "logs", "content_generation.log")
    with open(log_file, "a") as f:
        f.write(log_message + "\n")

# ============================================================================
# MAIN EXECUTION
# ============================================================================

def main():
    """Main execution flow."""
    log("=" * 80)
    log("CONTENT DRAFT GENERATION - STARTING")
    log("=" * 80)
    
    if not CONTENT_GENERATION_ENABLED:
        log("Content generation is disabled (CONTENT_GENERATION_ENABLED=false)")
        return
    
    try:
        # Step 1: Fetch content opportunities
        opportunities = fetch_content_opportunities()
        
        if not opportunities:
            log("No content opportunities found with Status='Ready to Draft'")
            log("Exiting gracefully.")
            return
        
        # Step 2: Process each opportunity
        for i, opp in enumerate(opportunities, 1):
            log(f"\n--- Processing opportunity {i}/{len(opportunities)} ---")
            log(f"Topic: {opp['topic']}")
            log(f"Platform: {opp['platform_target']} | Audience: {opp['audience']} | Priority: {opp['priority']}")
            
            try:
                # Retrieve source mentions
                mentions = retrieve_source_mentions(opp["source_mention_ids"])
                log(f"Retrieved {len(mentions)} source mentions")
                
                # Generate draft
                log(f"Generating draft with {OPENAI_MODEL_CONTENT}...")
                draft = generate_draft_with_openai(
                    topic=opp["topic"],
                    audience=opp["audience"],
                    platform_target=opp["platform_target"],
                    priority=opp["priority"],
                    key_points=opp["key_points"],
                    proof_points=opp["proof_points"],
                    mentions=mentions
                )
                
                # Validate draft
                is_valid, errors = validate_draft(draft, opp["platform_target"], opp["audience"])
                
                if is_valid:
                    log(f"✓ Draft validation passed")
                    word_count = len(draft["body"].split())
                    log(f"✓ Draft generated | length: {word_count} words | model: {OPENAI_MODEL_CONTENT}")
                else:
                    log(f"✗ Draft validation failed: {errors}")
                
                # Update Notion
                update_notion_with_draft(
                    content_id=opp["page_id"],
                    draft=draft,
                    validation_errors=errors if not is_valid else None
                )
                
                # Rate limiting delay
                time.sleep(2)
                
            except Exception as e:
                log(f"ERROR processing opportunity {opp['page_id']}: {e}")
                # Mark as failed in Notion
                try:
                    notion_update_page(opp["page_id"], {
                        "Status": {"status": {"name": "Draft Failed"}},
                        "Content Structure Notes": {
                            "rich_text": [{"text": {"content": f"Error: {str(e)[:2000]}"}}]
                        }
                    })
                except Exception as update_error:
                    log(f"Failed to update error status: {update_error}")
        
        log("\n" + "=" * 80)
        log("CONTENT DRAFT GENERATION - COMPLETED")
        log("=" * 80)
        
    except Exception as e:
        log(f"FATAL ERROR: {e}")
        raise

if __name__ == "__main__":
    main()
