# AdsVault RAG

AdsVault RAG is a Meta ads ingestion, processing, and retrieval system.

Features:
- Meta Graph API ingestion
- Media enrichment
- S3 asset storage
- Industry classification
- Ad benchmarking
- Dataset cleaning
- Hybrid RAG search
- Streamlit UI

---

# Structure

```text
core/      # pipeline scripts
pages/     # streamlit app
data/      # local datasets
test/      # checkpoints/tests
```

---

# Installation

```bash
python -m venv .venv
source .venv/bin/activate

pip install -r requirements.txt
pip install sentence-transformers
```

---

# Environment Variables

Create `.env`:

```env
META_ACCESS_TOKEN=
META_DATE_SINCE=
BUSINESS_ID=

AWS_ACCESS_KEY_ID=
AWS_SECRET_ACCESS_KEY=
AWS_DEFAULT_REGION=ap-southeast-1
S3_BUCKET=

OPENAI_API_KEY=
```

---

# Data Pipeline Flow

```text
Meta API
  ↓
Ingestion
  ↓
Media Enrichment
  ↓
S3 Upload
  ↓
Page Mapping
  ↓
Industry Classification
  ↓
Benchmarking
  ↓
Cleaning
  ↓
RAG Search
  ↓
Streamlit UI
```


---

# Streamlit App

```bash
streamlit run pages/_01_main.py
```

- No query → ads table
- Query → RAG search results

---

# Notes

- Meta API version: `v24.0`
- Some S3 paths are hardcoded
- Streamlit expects cleaned dataset in S3