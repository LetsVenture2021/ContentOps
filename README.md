## Overview

This application is designed to support modern Content Operations (ContentOps) through automated social media monitoring, data collection, and analysis. It continuously listens to social platforms, captures relevant conversations, and processes them into actionable insights that inform brand strategy, content planning, and market awareness.

At its core, the tool functions as a centralized social listening engine—providing visibility into audience sentiment, competitive activity, and emerging trends.

---

## Directory Structure

The application is organized into the following key directories:

### `config/`

Contains configuration files that define:

* API credentials for social media platforms
* Monitoring rules and parameters
* Data source definitions and filters

This directory controls how and where the app listens.

### `scripts/`

Houses the core processing logic, including:

* Data collection scripts
* Parsing and normalization routines
* Analysis and transformation workflows

These scripts are responsible for gathering raw social data and converting it into usable insights.

### `logs/`

Stores execution logs for:

* Monitoring system health
* Debugging errors or failures
* Auditing data collection and processing events

Logs provide operational transparency and reliability.

### `processed/`

Contains finalized outputs, such as:

* Cleaned and structured datasets
* Aggregated insights
* Analysis-ready files for reporting or downstream tools

This directory represents the app’s actionable output layer.

---

## What the App Does

* Monitors social media platforms for mentions, keywords, and topics
* Collects relevant posts and conversations automatically
* Processes and analyzes data for sentiment, trends, and signals
* Outputs structured insights for review, reporting, or integration

---

## Why It’s Important

Social listening is a critical capability for modern content and brand operations:

* **Brand Monitoring**
  Track what audiences are saying about your brand, products, or services in real time.

* **Competitive Intelligence**
  Observe competitor activity, positioning, and emerging market narratives.

* **Customer Insights**
  Capture unfiltered customer sentiment, feedback, and pain points.

* **Crisis Management**
  Detect early warning signs of negative sentiment or PR risks before they escalate.

* **Content Strategy Alignment**
  Identify trending topics, language patterns, and engagement opportunities.

---

## How It’s Valuable for ContentOps

This application enhances ContentOps workflows by providing:

* **Automated Data Collection**
  Eliminates the need for manual social media monitoring.

* **Centralized Insights**
  Consolidates signals from multiple platforms into a single system.

* **Trend Identification**
  Surfaces emerging conversations and shifts in audience interest.

* **Performance Tracking**
  Helps measure how content resonates across social channels.

* **Data-Driven Decision Making**
  Supplies quantifiable inputs to guide content planning, messaging, and timing.

---

## Summary

This tool acts as the organization’s **“ears on social media”**, enabling content and brand teams to stay informed, proactive, and strategically aligned with real-world audience conversations and market dynamics.

**Would you like this README adapted for a public open-source repo, an internal enterprise tool, or an investor-facing technical overview?**

---

## Testing & Quality Assurance

### Classifier Evaluation

The `social-listening/scripts/eval_classifier.py` script provides regression testing for the AI-powered triage classifier that routes social mentions to appropriate queues (leads, reputation management, content opportunities).

**Quick Start:**

```bash
# Run evaluation on 10 examples (fast iteration)
cd social-listening
MAX_EXAMPLES=10 python scripts/eval_classifier.py

# Run full evaluation suite (100 examples)
MAX_EXAMPLES=100 python scripts/eval_classifier.py

# Use custom model for testing
OPENAI_MODEL_TRIAGE=gpt-4o MAX_EXAMPLES=50 python scripts/eval_classifier.py
```

**What It Tests:**

- **Core Routing Accuracy**: Validates sentiment, priority, compliance mode, and routing decisions
- **Entity Extraction**: Measures Jaccard similarity for extracted entities and metro areas
- **Content Population**: Ensures conditional fields are properly filled based on routing decisions
- **Confidence Scoring**: Flags low-confidence predictions for review

**When to Run:**

- After modifying system prompts in `classify_and_route.py`
- Before deploying classifier changes to production
- When evaluating new OpenAI models
- As part of CI/CD validation pipelines

**Output:**

The script generates a comprehensive report showing accuracy metrics across all categories and exits with code 0 (pass) or 1 (fail) based on configurable thresholds.

**Test Data:**

The evaluation uses `tests/pv_labeled_examples_pack.jsonl`, a dataset of 100 synthetic social listening mentions with expected classifications, covering:
- Lead inquiries (hard money, cash buyers, capital partnerships)
- Reputation management (negative sentiment, questions, testimonials)
- Content opportunities (DSCR loans, competitor mentions, market trends)
