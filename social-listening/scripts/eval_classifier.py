#!/usr/bin/env python3
"""
Classifier Evaluation Harness
==============================

Tests the openai_classify() triage logic against labeled examples.

Usage:
    # Run on 10 examples (fast)
    MAX_EXAMPLES=10 python scripts/eval_classifier.py

    # Run full suite
    MAX_EXAMPLES=100 python scripts/eval_classifier.py

    # With custom model
    OPENAI_MODEL_TRIAGE=gpt-4o python scripts/eval_classifier.py

Output:
    - Prints detailed accuracy report
    - Exits 0 if passing, 1 if failing
    - Use in CI: `MAX_EXAMPLES=50 python scripts/eval_classifier.py || exit 1`

When to re-run:
    - After modifying system prompt in classify_and_route.py
    - After changing normalization logic
    - Before deploying classifier to production
"""

import os
import sys
import json
from pathlib import Path

# Add scripts directory to path to import classify_and_route
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from classify_and_route import openai_classify, MODEL_TRIAGE

# Configurable pass criteria thresholds
THRESHOLDS = {
    "sentiment_exact": 0.85,
    "priority_exact": 0.80,
    "compliance_exact": 0.95,
    "routes_exact": 0.85,
    "entity_jaccard": 0.65,
    "content_population": 0.90
}

def load_dataset(path: str, max_examples: int = None) -> list[dict]:
    """Load labeled examples from JSONL file."""
    examples = []
    with open(path, 'r') as f:
        for line in f:
            if line.strip():
                examples.append(json.loads(line))
    
    if max_examples is not None:
        examples = examples[:max_examples]
    
    return examples

def jaccard_similarity(set1: set, set2: set) -> float:
    """Calculate Jaccard similarity between two sets."""
    if not set1 and not set2:
        return 1.0  # Both empty = perfect match
    if not set1 or not set2:
        return 0.0  # One empty = no match
    
    intersection = len(set1 & set2)
    union = len(set1 | set2)
    return intersection / union if union > 0 else 0.0

def normalize_list(items):
    """Normalize list items to lowercase strings for comparison."""
    if not items:
        return set()
    return set(str(item).lower().strip() for item in items)

def evaluate_example(example: dict, model: str) -> dict:
    """Evaluate a single example and return scoring results."""
    mention = example["mention"]
    expected = example["expected"]
    
    # Call the classifier
    try:
        actual = openai_classify(model, mention)
    except Exception as e:
        return {
            "error": str(e),
            "example_id": example["example_id"]
        }
    
    results = {
        "example_id": example["example_id"],
        "error": None,
        "scores": {}
    }
    
    # Core field scoring
    results["scores"]["sentiment_exact"] = 1.0 if actual["sentiment"] == expected["sentiment"] else 0.0
    
    # Priority with ±1 tolerance
    priority_diff = abs(actual["priority"] - expected["priority"])
    results["scores"]["priority_exact"] = 1.0 if priority_diff == 0 else 0.0
    results["scores"]["priority_tolerance"] = 1.0 if priority_diff <= 1 else 0.0
    
    results["scores"]["compliance_exact"] = 1.0 if actual["compliance_mode"] == expected["compliance_mode"] else 0.0
    
    # Route scoring
    results["scores"]["route_lead"] = 1.0 if actual["routes"]["lead"] == expected["routes"]["lead"] else 0.0
    results["scores"]["route_reputation"] = 1.0 if actual["routes"]["reputation"] == expected["routes"]["reputation"] else 0.0
    results["scores"]["route_content"] = 1.0 if actual["routes"]["content"] == expected["routes"]["content"] else 0.0
    
    # Entity extraction (Jaccard)
    actual_entities = normalize_list(actual.get("entities", []))
    expected_entities = normalize_list(expected.get("entities", []))
    results["scores"]["entities_jaccard"] = jaccard_similarity(actual_entities, expected_entities)
    
    actual_metros = normalize_list(actual.get("metros", []))
    expected_metros = normalize_list(expected.get("metros", []))
    results["scores"]["metros_jaccard"] = jaccard_similarity(actual_metros, expected_metros)
    
    # Content population checks (conditional on routes)
    results["scores"]["content_checks"] = {}
    
    # Lead checks
    if expected["routes"]["lead"]:
        results["scores"]["content_checks"]["lead_title_filled"] = 1.0 if actual["lead"]["title"].strip() else 0.0
        results["scores"]["content_checks"]["lead_reply_filled"] = 1.0 if actual["lead"]["draft_reply"].strip() else 0.0
    
    # Reputation checks
    if expected["routes"]["reputation"]:
        results["scores"]["content_checks"]["reputation_title_filled"] = 1.0 if actual["reputation"]["title"].strip() else 0.0
        results["scores"]["content_checks"]["reputation_risk_exact"] = 1.0 if actual["reputation"]["risk_level"] == expected["reputation"]["risk_level"] else 0.0
    
    # Content checks
    if expected["routes"]["content"]:
        results["scores"]["content_checks"]["content_title_filled"] = 1.0 if actual["content"]["title"].strip() else 0.0
        results["scores"]["content_checks"]["content_bullets_filled"] = 1.0 if len(actual["content"]["outline_bullets"]) > 0 else 0.0
    
    # Confidence check
    results["scores"]["low_confidence"] = actual.get("confidence", 1.0) < 0.7
    
    # Store actual for failure reporting
    results["actual"] = actual
    results["expected"] = expected
    
    return results

def generate_report(results: list[dict], model: str, total_examples: int) -> dict:
    """Generate evaluation report with metrics."""
    
    # Filter out errors
    valid_results = [r for r in results if r.get("error") is None]
    error_results = [r for r in results if r.get("error") is not None]
    
    if not valid_results:
        return {
            "error": "No valid results to evaluate",
            "error_count": len(error_results)
        }
    
    n = len(valid_results)
    
    # Calculate core routing accuracy
    sentiment_exact = sum(r["scores"]["sentiment_exact"] for r in valid_results) / n
    priority_exact = sum(r["scores"]["priority_exact"] for r in valid_results) / n
    priority_tolerance = sum(r["scores"]["priority_tolerance"] for r in valid_results) / n
    compliance_exact = sum(r["scores"]["compliance_exact"] for r in valid_results) / n
    
    route_lead = sum(r["scores"]["route_lead"] for r in valid_results) / n
    route_reputation = sum(r["scores"]["route_reputation"] for r in valid_results) / n
    route_content = sum(r["scores"]["route_content"] for r in valid_results) / n
    
    # Average Jaccard scores
    entities_jaccard = sum(r["scores"]["entities_jaccard"] for r in valid_results) / n
    metros_jaccard = sum(r["scores"]["metros_jaccard"] for r in valid_results) / n
    
    # Content population stats (conditional)
    content_stats = {}
    
    # Lead stats
    lead_examples = [r for r in valid_results if r["expected"]["routes"]["lead"]]
    if lead_examples:
        lead_title_filled = sum(r["scores"]["content_checks"].get("lead_title_filled", 0) for r in lead_examples)
        lead_reply_filled = sum(r["scores"]["content_checks"].get("lead_reply_filled", 0) for r in lead_examples)
        content_stats["lead_title"] = (lead_title_filled, len(lead_examples))
        content_stats["lead_reply"] = (lead_reply_filled, len(lead_examples))
    
    # Reputation stats
    rep_examples = [r for r in valid_results if r["expected"]["routes"]["reputation"]]
    if rep_examples:
        rep_title_filled = sum(r["scores"]["content_checks"].get("reputation_title_filled", 0) for r in rep_examples)
        rep_risk_exact = sum(r["scores"]["content_checks"].get("reputation_risk_exact", 0) for r in rep_examples)
        content_stats["reputation_title"] = (rep_title_filled, len(rep_examples))
        content_stats["reputation_risk"] = (rep_risk_exact, len(rep_examples))
    
    # Content stats
    content_examples = [r for r in valid_results if r["expected"]["routes"]["content"]]
    if content_examples:
        content_title_filled = sum(r["scores"]["content_checks"].get("content_title_filled", 0) for r in content_examples)
        content_bullets_filled = sum(r["scores"]["content_checks"].get("content_bullets_filled", 0) for r in content_examples)
        content_stats["content_title"] = (content_title_filled, len(content_examples))
        content_stats["content_bullets"] = (content_bullets_filled, len(content_examples))
    
    # Low confidence flags
    low_confidence_count = sum(1 for r in valid_results if r["scores"]["low_confidence"])
    
    # Collect failures
    failures = []
    for r in valid_results:
        example_id = r["example_id"]
        
        # Check for route mismatches
        if r["scores"]["route_lead"] == 0:
            failures.append(f"{example_id}: routes.lead expected={r['expected']['routes']['lead']}, got={r['actual']['routes']['lead']}")
        if r["scores"]["route_reputation"] == 0:
            failures.append(f"{example_id}: routes.reputation expected={r['expected']['routes']['reputation']}, got={r['actual']['routes']['reputation']}")
        if r["scores"]["route_content"] == 0:
            failures.append(f"{example_id}: routes.content expected={r['expected']['routes']['content']}, got={r['actual']['routes']['content']}")
        
        # Check for priority mismatches
        if r["scores"]["priority_exact"] == 0:
            failures.append(f"{example_id}: priority expected={r['expected']['priority']}, got={r['actual']['priority']}")
        
        # Check for sentiment mismatches
        if r["scores"]["sentiment_exact"] == 0:
            failures.append(f"{example_id}: sentiment expected={r['expected']['sentiment']}, got={r['actual']['sentiment']}")
    
    # Calculate pass criteria
    routes_avg = (route_lead + route_reputation + route_content) / 3
    content_population_scores = [v[0]/v[1] for v in content_stats.values() if v[1] > 0]
    content_population_avg = sum(content_population_scores) / len(content_population_scores) if content_population_scores else 1.0
    
    pass_criteria = {
        "sentiment_exact": sentiment_exact >= THRESHOLDS["sentiment_exact"],
        "priority_exact": priority_exact >= THRESHOLDS["priority_exact"],
        "compliance_exact": compliance_exact >= THRESHOLDS["compliance_exact"],
        "routes_exact": routes_avg >= THRESHOLDS["routes_exact"],
        "entity_jaccard": entities_jaccard >= THRESHOLDS["entity_jaccard"],
        "content_population": content_population_avg >= THRESHOLDS["content_population"]
    }
    
    return {
        "model": model,
        "examples_evaluated": n,
        "total_examples": total_examples,
        "errors": len(error_results),
        "core_routing": {
            "sentiment_exact": sentiment_exact,
            "priority_exact": priority_exact,
            "priority_tolerance": priority_tolerance,
            "compliance_exact": compliance_exact,
            "route_lead": route_lead,
            "route_reputation": route_reputation,
            "route_content": route_content
        },
        "entity_extraction": {
            "entities_jaccard": entities_jaccard,
            "metros_jaccard": metros_jaccard
        },
        "content_population": content_stats,
        "low_confidence_count": low_confidence_count,
        "failures": failures,
        "pass_criteria": pass_criteria,
        "overall_pass": all(pass_criteria.values())
    }

def print_report(report: dict):
    """Print formatted evaluation report."""
    
    if "error" in report:
        print(f"ERROR: {report['error']}")
        if report.get("error_count"):
            print(f"Failed examples: {report['error_count']}")
        return
    
    print("=== Classifier Evaluation Report ===")
    print(f"Model: {report['model']}")
    print(f"Examples: {report['examples_evaluated']} / {report['total_examples']}")
    if report["errors"] > 0:
        print(f"Errors: {report['errors']}")
    print()
    
    print("CORE ROUTING ACCURACY:")
    cr = report["core_routing"]
    print(f"  Sentiment:        {cr['sentiment_exact']*100:.1f}% ({int(cr['sentiment_exact']*report['examples_evaluated'])}/{report['examples_evaluated']} exact matches)")
    print(f"  Priority:         {cr['priority_exact']*100:.1f}% ({int(cr['priority_exact']*report['examples_evaluated'])}/{report['examples_evaluated']} exact, {int(cr['priority_tolerance']*report['examples_evaluated'])} within ±1)")
    print(f"  Compliance Mode:  {cr['compliance_exact']*100:.1f}% ({int(cr['compliance_exact']*report['examples_evaluated'])}/{report['examples_evaluated']})")
    print(f"  Route - Lead:     {cr['route_lead']*100:.1f}% ({int(cr['route_lead']*report['examples_evaluated'])}/{report['examples_evaluated']})")
    print(f"  Route - Reputation: {cr['route_reputation']*100:.1f}% ({int(cr['route_reputation']*report['examples_evaluated'])}/{report['examples_evaluated']})")
    print(f"  Route - Content:  {cr['route_content']*100:.1f}% ({int(cr['route_content']*report['examples_evaluated'])}/{report['examples_evaluated']})")
    print()
    
    print("ENTITY EXTRACTION:")
    ee = report["entity_extraction"]
    print(f"  Entities (Jaccard): {ee['entities_jaccard']:.2f} avg")
    print(f"  Metros (Jaccard):   {ee['metros_jaccard']:.2f} avg")
    print()
    
    print("CONTENT POPULATION (conditional):")
    cp = report["content_population"]
    if "lead_title" in cp:
        lt = cp["lead_title"]
        print(f"  Lead title filled:       {int(lt[0])}/{lt[1]} when route=true")
    if "lead_reply" in cp:
        lr = cp["lead_reply"]
        print(f"  Lead reply filled:       {int(lr[0])}/{lr[1]} when route=true")
    if "reputation_title" in cp:
        rt = cp["reputation_title"]
        print(f"  Reputation title filled: {int(rt[0])}/{rt[1]} when route=true")
    if "reputation_risk" in cp:
        rr = cp["reputation_risk"]
        print(f"  Reputation risk_level:   {int(rr[0])}/{rr[1]} correct")
    if "content_title" in cp:
        ct = cp["content_title"]
        print(f"  Content title filled:    {int(ct[0])}/{ct[1]} when route=true")
    if "content_bullets" in cp:
        cb = cp["content_bullets"]
        print(f"  Content bullets filled:  {int(cb[0])}/{cb[1]} when route=true")
    print()
    
    print(f"LOW CONFIDENCE FLAGS: {report['low_confidence_count']} example(s) < 0.7")
    print()
    
    if report["failures"]:
        print("FAILURES:")
        for failure in report["failures"][:10]:  # Show first 10
            print(f"  {failure}")
        if len(report["failures"]) > 10:
            print(f"  ... and {len(report['failures']) - 10} more")
        print()
    
    print("PASS CRITERIA:")
    pc = report["pass_criteria"]
    cr = report["core_routing"]
    ee = report["entity_extraction"]
    
    routes_avg = (cr['route_lead'] + cr['route_reputation'] + cr['route_content']) / 3
    content_pop_scores = [v[0]/v[1] for v in cp.values() if v[1] > 0]
    content_pop_avg = sum(content_pop_scores) / len(content_pop_scores) if content_pop_scores else 1.0
    
    def status(passed):
        return "✅" if passed else "❌"
    
    print(f"  {status(pc['sentiment_exact'])} Sentiment exact match ≥ {THRESHOLDS['sentiment_exact']*100:.0f}% (got {cr['sentiment_exact']*100:.1f}%)")
    print(f"  {status(pc['priority_exact'])} Priority exact match ≥ {THRESHOLDS['priority_exact']*100:.0f}% (got {cr['priority_exact']*100:.1f}%)")
    print(f"  {status(pc['compliance_exact'])} Compliance exact match ≥ {THRESHOLDS['compliance_exact']*100:.0f}% (got {cr['compliance_exact']*100:.1f}%)")
    print(f"  {status(pc['routes_exact'])} Core routing accuracy ≥ {THRESHOLDS['routes_exact']*100:.0f}% (got {routes_avg*100:.1f}%)")
    print(f"  {status(pc['entity_jaccard'])} Entity Jaccard ≥ {THRESHOLDS['entity_jaccard']:.2f} (got {ee['entities_jaccard']:.2f})")
    print(f"  {status(pc['content_population'])} Content population ≥ {THRESHOLDS['content_population']*100:.0f}% when route=true (got {content_pop_avg*100:.1f}%)")
    print()
    
    overall_status = "✅ PASS" if report["overall_pass"] else "❌ FAIL"
    failed_count = sum(1 for v in pc.values() if not v)
    print(f"OVERALL: {overall_status} ({failed_count} criteria below threshold)" if failed_count > 0 else f"OVERALL: {overall_status}")

def main():
    # Configuration
    root = Path(__file__).parent.parent
    dataset_path = root / "tests" / "pv_labeled_examples_pack.jsonl"
    
    max_examples = int(os.environ.get("MAX_EXAMPLES", 10))
    model = os.environ.get("OPENAI_MODEL_TRIAGE", MODEL_TRIAGE)
    
    # Check dataset exists
    if not dataset_path.exists():
        print(f"ERROR: Dataset not found at {dataset_path}")
        print("Please run tests/generate_synthetic_dataset.py first")
        sys.exit(1)
    
    # Load dataset
    print(f"Loading dataset from {dataset_path}...")
    all_examples = load_dataset(str(dataset_path))
    examples = all_examples[:max_examples]
    print(f"Loaded {len(examples)} examples (of {len(all_examples)} total)")
    print()
    
    # Evaluate each example
    print("Evaluating examples...")
    results = []
    for i, example in enumerate(examples, 1):
        print(f"  [{i}/{len(examples)}] {example['example_id']}", end="\r")
        result = evaluate_example(example, model)
        results.append(result)
    print()
    print()
    
    # Generate and print report
    report = generate_report(results, model, len(all_examples))
    print_report(report)
    
    # Exit with appropriate code
    sys.exit(0 if report.get("overall_pass", False) else 1)

if __name__ == "__main__":
    main()
