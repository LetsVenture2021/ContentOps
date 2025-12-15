#!/usr/bin/env python3
"""
Generate synthetic labeled dataset for classifier evaluation.
This script creates 100 labeled examples covering various categories.
"""
import json
import random
from datetime import datetime, timedelta

# Set seed for reproducibility
random.seed(42)

def generate_example(example_id, category, index):
    """Generate a single synthetic example based on category."""
    
    platforms = ["BiggerPockets", "Reddit", "LinkedIn", "Twitter", "Facebook"]
    platform = random.choice(platforms)
    
    base_time = datetime(2025, 12, 15, 12, 0, 0)
    created_at = (base_time - timedelta(days=random.randint(0, 30))).isoformat() + "Z"
    
    # Generate mention data based on category
    if category == "lead_hard_money":
        authors = [f"investor_{i}" for i in range(50)]
        metros = ["Houston", "Dallas", "Austin", "Phoenix", "Atlanta", "Miami", "Denver", "Seattle"]
        texts = [
            f"Looking for a hard money lender in {random.choice(metros)} for a fix-and-flip deal. Need $250k for 6 months.",
            f"Anyone know a good hard money lender for {random.choice(metros)} area? Working on a rehab project.",
            f"Need bridge financing for commercial property in {random.choice(metros)}. Who do you recommend?",
            f"Seeking hard money loan for rental property acquisition in {random.choice(metros)}. Fast close needed.",
            f"Looking for recommendations on hard money lenders in the {random.choice(metros)} metro area.",
        ]
        metro = random.choice(metros)
        text = random.choice(texts).replace(metro, metro)  # Ensure consistency
        
        mention = {
            "platform": platform,
            "url": f"https://{platform.lower()}.com/post/{random.randint(10000, 99999)}",
            "text": text,
            "author": random.choice(authors),
            "created_at": created_at,
            "source_query": "hard money lender OR bridge loan"
        }
        
        expected = {
            "sentiment": "Neutral",
            "priority": 1 if "fast close" in text.lower() or "need" in text.lower() else 2,
            "confidence": random.uniform(0.85, 0.95),
            "compliance_mode": False,
            "entities": ["hard money lender", metro],
            "metros": [metro],
            "routes": {"lead": True, "reputation": False, "content": False},
            "lead": {
                "title": f"Hard Money Inquiry - {metro} - {mention['author']}",
                "draft_reply": f"Thanks for reaching out! We'd be happy to discuss hard money lending options in {metro}. Could you share more details about your project?"
            },
            "reputation": {
                "title": "",
                "draft_reply": "",
                "risk_level": "Low"
            },
            "content": {
                "title": "",
                "angle": "",
                "outline_bullets": [],
                "canva_prompts": []
            },
            "notes": "High-priority lead inquiry for hard money lending in target metro."
        }
    
    elif category == "lead_cash_buyer":
        authors = [f"seller_{i}" for i in range(30)]
        metros = ["Los Angeles", "San Diego", "Las Vegas", "Portland", "Sacramento"]
        texts = [
            f"Need to sell my rental property in {random.choice(metros)} quickly. Any cash buyers?",
            f"Looking for cash buyer for distressed property in {random.choice(metros)}. Needs work.",
            f"Have a portfolio of 3 rentals in {random.choice(metros)}. Looking for investor to buy.",
            f"Selling off-market property in {random.choice(metros)}. Cash offers only.",
        ]
        metro = random.choice(metros)
        text = random.choice(texts).replace("random.choice(metros)", metro)
        
        mention = {
            "platform": platform,
            "url": f"https://{platform.lower()}.com/post/{random.randint(10000, 99999)}",
            "text": text,
            "author": random.choice(authors),
            "created_at": created_at,
            "source_query": "cash buyer OR sell property"
        }
        
        expected = {
            "sentiment": "Neutral",
            "priority": 2,
            "confidence": random.uniform(0.80, 0.92),
            "compliance_mode": False,
            "entities": ["cash buyer", metro, "rental property"],
            "metros": [metro],
            "routes": {"lead": True, "reputation": False, "content": False},
            "lead": {
                "title": f"Cash Purchase Opportunity - {metro}",
                "draft_reply": "We're interested in cash purchases in your area. Can you share property details and asking price?"
            },
            "reputation": {
                "title": "",
                "draft_reply": "",
                "risk_level": "Low"
            },
            "content": {
                "title": "",
                "angle": "",
                "outline_bullets": [],
                "canva_prompts": []
            },
            "notes": "Potential acquisition lead - seller seeking cash buyer."
        }
    
    elif category == "lead_capital":
        authors = [f"syndicator_{i}" for i in range(20)]
        metros = ["Chicago", "Boston", "Washington DC", "Nashville", "Tampa"]
        texts = [
            f"Raising $2M for multifamily syndication in {random.choice(metros)}. Looking for LP investors.",
            f"Seeking capital partners for commercial development in {random.choice(metros)}. 15% preferred return.",
            f"New fund forming for {random.choice(metros)} area student housing. Who's interested?",
            f"JV opportunity on 150-unit multifamily in {random.choice(metros)}. Need equity partner.",
        ]
        metro = random.choice(metros)
        text = random.choice(texts).replace("random.choice(metros)", metro)
        
        mention = {
            "platform": platform,
            "url": f"https://{platform.lower()}.com/post/{random.randint(10000, 99999)}",
            "text": text,
            "author": random.choice(authors),
            "created_at": created_at,
            "source_query": "LP investor OR syndication OR JV partner"
        }
        
        expected = {
            "sentiment": "Positive",
            "priority": 2,
            "confidence": random.uniform(0.75, 0.90),
            "compliance_mode": False,
            "entities": ["capital raise", "LP investor", metro, "multifamily"],
            "metros": [metro],
            "routes": {"lead": True, "reputation": False, "content": False},
            "lead": {
                "title": f"Capital Partnership - {metro} Syndication",
                "draft_reply": "Your syndication opportunity sounds interesting. We'd like to learn more about the deal structure and terms."
            },
            "reputation": {
                "title": "",
                "draft_reply": "",
                "risk_level": "Low"
            },
            "content": {
                "title": "",
                "angle": "",
                "outline_bullets": [],
                "canva_prompts": []
            },
            "notes": "Capital raise opportunity - potential LP relationship."
        }
    
    elif category == "reputation_negative":
        authors = [f"complainant_{i}" for i in range(25)]
        companies = ["XYZ Capital", "ABC Lending", "BestFund Group", "QuickFlip Co", "ReliableLenders Inc"]
        texts = [
            f"WARNING: Stay away from {random.choice(companies)}. They took my money and disappeared!",
            f"DO NOT work with {random.choice(companies)}. Total scam. Filing complaints with state AG.",
            f"{random.choice(companies)} is a fraud. They charged hidden fees and won't return calls.",
            f"Terrible experience with {random.choice(companies)}. Might be illegal what they're doing.",
        ]
        company = random.choice(companies)
        text = random.choice(texts).replace("random.choice(companies)", company)
        
        mention = {
            "platform": platform,
            "url": f"https://{platform.lower()}.com/post/{random.randint(10000, 99999)}",
            "text": text,
            "author": random.choice(authors),
            "created_at": created_at,
            "source_query": "scam OR fraud OR warning"
        }
        
        expected = {
            "sentiment": "Negative",
            "priority": 1,
            "confidence": random.uniform(0.90, 0.98),
            "compliance_mode": True,
            "entities": [company, "fraud allegations"],
            "metros": [],
            "routes": {"lead": False, "reputation": True, "content": False},
            "lead": {
                "title": "",
                "draft_reply": ""
            },
            "reputation": {
                "title": f"Fraud Allegation - {company}",
                "draft_reply": "We take these concerns seriously. Please contact us privately at compliance@company.com to discuss this matter.",
                "risk_level": "High"
            },
            "content": {
                "title": "",
                "angle": "",
                "outline_bullets": [],
                "canva_prompts": []
            },
            "notes": "High-risk reputation issue with fraud allegations. Requires compliance review."
        }
    
    elif category == "reputation_question":
        authors = [f"curious_investor_{i}" for i in range(20)]
        companies = ["PrimeVest Partners", "Elite Capital", "SureInvest Group", "TrustFund Co"]
        texts = [
            f"Has anyone worked with {random.choice(companies)}? Are they legit?",
            f"Considering investing with {random.choice(companies)}. Any reviews or experiences?",
            f"What do people think about {random.choice(companies)}? Seems too good to be true.",
            f"Due diligence question: Is {random.choice(companies)} trustworthy?",
        ]
        company = random.choice(companies)
        text = random.choice(texts).replace("random.choice(companies)", company)
        
        mention = {
            "platform": platform,
            "url": f"https://{platform.lower()}.com/post/{random.randint(10000, 99999)}",
            "text": text,
            "author": random.choice(authors),
            "created_at": created_at,
            "source_query": "review OR legit OR trustworthy"
        }
        
        expected = {
            "sentiment": "Neutral",
            "priority": 2,
            "confidence": random.uniform(0.80, 0.92),
            "compliance_mode": False,
            "entities": [company, "due diligence"],
            "metros": [],
            "routes": {"lead": False, "reputation": True, "content": False},
            "lead": {
                "title": "",
                "draft_reply": ""
            },
            "reputation": {
                "title": f"Reputation Inquiry - {company}",
                "draft_reply": "Thanks for asking! We'd be happy to share more information about our track record. Feel free to DM us.",
                "risk_level": "Low"
            },
            "content": {
                "title": "",
                "angle": "",
                "outline_bullets": [],
                "canva_prompts": []
            },
            "notes": "Due diligence inquiry - opportunity to provide positive information."
        }
    
    elif category == "reputation_proof":
        authors = [f"satisfied_client_{i}" for i in range(15)]
        companies = ["OurCompany", "VentureGroup", "TopInvestors LLC"]
        metros = ["Charlotte", "Raleigh", "Orlando", "Memphis"]
        texts = [
            f"Just closed my 5th deal with {random.choice(companies)}. They're the real deal in {random.choice(metros)}!",
            f"Shoutout to {random.choice(companies)} for excellent service on our {random.choice(metros)} project!",
            f"Highly recommend {random.choice(companies)}. Professional and reliable in the {random.choice(metros)} market.",
        ]
        company = random.choice(companies)
        metro = random.choice(metros)
        text = random.choice(texts).replace("random.choice(companies)", company).replace("random.choice(metros)", metro)
        
        mention = {
            "platform": platform,
            "url": f"https://{platform.lower()}.com/post/{random.randint(10000, 99999)}",
            "text": text,
            "author": random.choice(authors),
            "created_at": created_at,
            "source_query": "recommend OR shoutout OR excellent"
        }
        
        expected = {
            "sentiment": "Positive",
            "priority": 3,
            "confidence": random.uniform(0.85, 0.95),
            "compliance_mode": False,
            "entities": [company, metro],
            "metros": [metro],
            "routes": {"lead": False, "reputation": True, "content": False},
            "lead": {
                "title": "",
                "draft_reply": ""
            },
            "reputation": {
                "title": f"Positive Testimonial - {metro}",
                "draft_reply": "Thank you for the kind words! We're glad we could help with your project.",
                "risk_level": "Low"
            },
            "content": {
                "title": "",
                "angle": "",
                "outline_bullets": [],
                "canva_prompts": []
            },
            "notes": "Positive social proof - good for testimonial collection."
        }
    
    elif category == "content_dscr":
        authors = [f"landlord_{i}" for i in range(30)]
        texts = [
            "What exactly is a DSCR loan? How is it different from conventional financing?",
            "Can someone explain DSCR requirements for rental property loans?",
            "Looking into DSCR loans for my STR portfolio. What should I know?",
            "DSCR vs conventional - which is better for buy-and-hold investors?",
            "How do lenders calculate DSCR? Is 1.25 the magic number?",
        ]
        
        mention = {
            "platform": platform,
            "url": f"https://{platform.lower()}.com/post/{random.randint(10000, 99999)}",
            "text": random.choice(texts),
            "author": random.choice(authors),
            "created_at": created_at,
            "source_query": "DSCR loan"
        }
        
        expected = {
            "sentiment": "Neutral",
            "priority": 3,
            "confidence": random.uniform(0.80, 0.92),
            "compliance_mode": False,
            "entities": ["DSCR loan", "rental property"],
            "metros": [],
            "routes": {"lead": False, "reputation": False, "content": True},
            "lead": {
                "title": "",
                "draft_reply": ""
            },
            "reputation": {
                "title": "",
                "draft_reply": "",
                "risk_level": "Low"
            },
            "content": {
                "title": "DSCR Loans Explained: What Rental Property Investors Need to Know",
                "angle": "Educational explainer on DSCR loan basics and requirements",
                "outline_bullets": [
                    "What is DSCR and how is it calculated",
                    "DSCR loan requirements and qualification criteria",
                    "DSCR vs conventional financing comparison",
                    "Common DSCR ratio thresholds (1.0, 1.25, etc.)"
                ],
                "canva_prompts": [
                    "DSCR calculation formula infographic",
                    "Comparison chart: DSCR vs Conventional loans"
                ]
            },
            "notes": "Educational content opportunity - DSCR loan fundamentals."
        }
    
    elif category == "content_competitor":
        authors = [f"forum_user_{i}" for i in range(25)]
        competitors = ["Lima One", "Visio Lending", "Kiavi", "RCN Capital", "Anchor Loans"]
        texts = [
            f"Anyone have experience with {random.choice(competitors)}? How are their rates?",
            f"Just got quoted by {random.choice(competitors)}. Seems high. What are alternatives?",
            f"Comparing {random.choice(competitors)} to other DSCR lenders. Thoughts?",
            f"{random.choice(competitors)} rejected my app. Who else should I try?",
        ]
        competitor = random.choice(competitors)
        text = random.choice(texts).replace("random.choice(competitors)", competitor)
        
        mention = {
            "platform": platform,
            "url": f"https://{platform.lower()}.com/post/{random.randint(10000, 99999)}",
            "text": text,
            "author": random.choice(authors),
            "created_at": created_at,
            "source_query": f"{competitor}"
        }
        
        expected = {
            "sentiment": "Neutral",
            "priority": 3,
            "confidence": random.uniform(0.75, 0.88),
            "compliance_mode": False,
            "entities": [competitor, "DSCR lender", "comparison"],
            "metros": [],
            "routes": {"lead": False, "reputation": False, "content": True},
            "lead": {
                "title": "",
                "draft_reply": ""
            },
            "reputation": {
                "title": "",
                "draft_reply": "",
                "risk_level": "Low"
            },
            "content": {
                "title": f"DSCR Lender Comparison: {competitor} vs Alternatives",
                "angle": "Competitive analysis and lender comparison guide",
                "outline_bullets": [
                    f"{competitor} key features and requirements",
                    "Rate and fee comparison across top DSCR lenders",
                    "Pros and cons of each lender",
                    "Best lender for different investor profiles"
                ],
                "canva_prompts": [
                    "DSCR lender comparison table graphic",
                    f"{competitor} vs competitors rate chart"
                ]
            },
            "notes": "Competitive intelligence - comparison content opportunity."
        }
    
    elif category == "content_trend":
        authors = [f"market_watcher_{i}" for i in range(30)]
        trends = [
            "Interest rates finally dropping - time to refinance rentals?",
            "STR regulations tightening in major cities. How are investors adapting?",
            "Seeing a surge in multi-generational housing demand. Investment angle?",
            "Industrial-to-residential conversions trending. Opportunity or trap?",
            "Climate-resilient properties commanding premium prices now.",
            "Remote work shift is changing commercial real estate fundamentally.",
            "Prop tech AI tools disrupting property management - what's worth it?",
        ]
        
        mention = {
            "platform": platform,
            "url": f"https://{platform.lower()}.com/post/{random.randint(10000, 99999)}",
            "text": random.choice(trends),
            "author": random.choice(authors),
            "created_at": created_at,
            "source_query": "real estate trends"
        }
        
        expected = {
            "sentiment": "Neutral",
            "priority": 3,
            "confidence": random.uniform(0.70, 0.85),
            "compliance_mode": False,
            "entities": ["real estate trends", "market analysis"],
            "metros": [],
            "routes": {"lead": False, "reputation": False, "content": True},
            "lead": {
                "title": "",
                "draft_reply": ""
            },
            "reputation": {
                "title": "",
                "draft_reply": "",
                "risk_level": "Low"
            },
            "content": {
                "title": "Real Estate Trend Alert: Market Shifts and Investment Implications",
                "angle": "Trend analysis with actionable insights for investors",
                "outline_bullets": [
                    "Current market trend overview",
                    "What's driving this change",
                    "Investment opportunities and risks",
                    "How to position for this trend"
                ],
                "canva_prompts": [
                    "Market trend data visualization",
                    "Before/after market shift comparison"
                ]
            },
            "notes": "Trending topic - timely content opportunity for thought leadership."
        }
    
    else:
        raise ValueError(f"Unknown category: {category}")
    
    return {
        "example_id": example_id,
        "mention": mention,
        "expected": expected
    }

def main():
    """Generate 100 labeled examples across all categories."""
    
    categories = [
        ("lead_hard_money", 22),
        ("lead_cash_buyer", 10),
        ("lead_capital", 8),
        ("reputation_negative", 10),
        ("reputation_question", 8),
        ("reputation_proof", 6),
        ("content_dscr", 12),
        ("content_competitor", 10),
        ("content_trend", 14),
    ]
    
    examples = []
    example_counter = 1
    
    for category, count in categories:
        for i in range(count):
            example_id = f"ex_{example_counter:03d}"
            example = generate_example(example_id, category, i)
            examples.append(example)
            example_counter += 1
    
    # Save to JSONL file
    output_path = "/home/runner/work/ContentOps/ContentOps/social-listening/tests/pv_labeled_examples_pack.jsonl"
    with open(output_path, "w") as f:
        for example in examples:
            f.write(json.dumps(example, ensure_ascii=False) + "\n")
    
    print(f"Generated {len(examples)} labeled examples")
    print(f"Saved to: {output_path}")
    
    # Print category distribution
    print("\nCategory distribution:")
    for category, count in categories:
        print(f"  {category}: {count}")

if __name__ == "__main__":
    main()
