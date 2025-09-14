# MCP BioForensics

[![CI](https://github.com/axdithyaxo/mcp-bioforensics/actions/workflows/ci.yml/badge.svg)](https://github.com/axdithyaxo/mcp-bioforensics/actions/workflows/ci.yml)  
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

**MCP BioForensics** is an AI-driven platform designed for comprehensive exploration of clinical trial datasets. Built upon the **Model Context Protocol (MCP)**, it supports reliable data ingestion, indexing, hybrid semantic and structured retrieval, and natural language question answering. Tailored for biomedical research and clinical trial analysis, MCP BioForensics emphasizes auditability, reproducibility, and extensibility.

---

## Architecture & Workflow

```
+----------------+     +----------------+     +----------------+     +----------------+     +----------------+
|  Data Ingestion| --> |    Indexing    | --> | Hybrid Retrieval| --> |     RAG Prompt  | --> | Forensics &      |
| (CSV → SQLite/ |     | (FAISS vector  |     | (FAISS + SQL)   |     | (trial-rag tool)|     | Reporting (Planned)|
|  Postgres DB)  |     |  embeddings)   |     |                |     |                |     |                |
+----------------+     +----------------+     +----------------+     +----------------+     +----------------+
```

1. **Data Ingestion**  
Clinical trial CSVs (e.g., ClinicalTrials.gov datasets) are normalized and ingested into SQLite by default, with optional PostgreSQL support. This step enforces canonical phase/status codes, normalizes schema, and prepares data for indexing.

2. **Indexing**  
Free-text fields such as trial summaries and outcomes are embedded via Sentence-Transformers and indexed using FAISS for efficient semantic search.

3. **Hybrid Retrieval**  
Queries combine semantic similarity search over FAISS with structured SQL filters (e.g., trial phase, minimum participants) to deliver precise results.

4. **RAG Prompting** *(Planned)*  
Retrieval-Augmented Generation (RAG) prompts will leverage search results to generate context-rich natural language answers.

5. **Forensics & Reporting** *(Planned)*  
Includes dataset hashing, anomaly detection (duplicates, missing data, invalid dates), and export of audit-ready reports in Markdown, CSV, and optionally PDF formats.

---

## Key Achievements & Significance

- **Agentic Hybrid Retrieval**: Integrates semantic vector search with structured SQL filters for precise, context-aware clinical trial queries.  
- **Reproducibility & Auditability**: Typed I/O, deterministic test mode, and CI pipelines on Python 3.10–3.12 ensure robust, maintainable code.  
- **Extensible MCP-based Server**: Exposes typed tools discoverable by any MCP-compatible client, enabling seamless integration and automation.  
- **Scalable Indexing**: Efficient embedding and FAISS indexing support large datasets, including the full ClinicalTrials.gov 2025 dataset (~17,732 trials).  
- **Future-Proof Design**: Planned forensic checks and RAG-based natural language QA will enhance trust and usability.

---

## Quickstart

```bash
# Clone and install with optional vector and database dependencies
git clone https://github.com/axdithyaxo/mcp-bioforensics.git
cd mcp-bioforensics
poetry install -E vector -E db

# Verify installation with CLI help
poetry run biofx --help

# Ingest sample data and build vector index
poetry run biofx ingest data/samples/trials_sample.csv
poetry run biofx index

# Example query: hybrid semantic + filter search
poetry run biofx query "Phase II trials for glioblastoma with >100 participants"
```

---

## How It Works: Tool Descriptions & Examples

### 1. `ping`  
Health check tool to verify server status.

**Example:**  
```
From "MCP BioForensics", run ping.
```

**Response:**  
```json
{"ok": true, "service": "mcp-bioforensics"}
```

---

### 2. `list_datasets`  
Lists all ingested datasets with metadata.

**Example:**  
```
From "MCP BioForensics", run list_datasets.
```

**Response:**  
```json
[
  {
    "dataset_id": "ctg2025_1",
    "name": "ClinicalTrials.gov 2025 Full",
    "row_count": 17732,
    "ingested_at": "2025-09-10T10:32:00",
    "source_path": "data/ctg-studies.csv"
  },
  {
    "dataset_id": "ctg2025_2",
    "name": "Supplemental Oncology Trials",
    "row_count": 2292,
    "ingested_at": "2025-09-10T10:40:00",
    "source_path": "data/oncology-extra.csv"
  }
]
```

---

### 3. `get_trial`  
Retrieves detailed information for a specific trial by `trial_id`.

**Example:**  
```
From "MCP BioForensics", run get_trial with:
trial_id="NCT04253873"
```

**Response:**  
```json
{
  "dataset_id": "ctg2025_1",
  "trial_id": "NCT04253873",
  "disease": "High-grade Gliomas",
  "phase": "PHASE2",
  "n_participants": 40,
  "summary": "...",
  "outcomes_text": "...",
  "status": "Completed",
  "sponsor": "XYZ Pharma",
  "start_date": "2023-01-15",
  "end_date": "2024-06-30"
}
```

---

### 4. `build_vector_index`  
Builds or updates the FAISS vector index from ingested data.

**Example:**  
```
From "MCP BioForensics", run build_vector_index.
```

**Response:**  
```json
{
  "dim": 384,
  "count": 20024,
  "index_path": "/Users/<you>/.local/share/mcp-bioforensics/index/faiss.index"
}
```

---

### 5. `search_trials`  
Performs hybrid semantic and structured search over trials.

**Payload Examples:**

- Basic semantic query:  
```json
{
  "query": "glioblastoma phase 2 trials"
}
```

- Query with phase filter:  
```json
{
  "query": "brain tumor",
  "options": {"phase": "PHASE3", "top_k": 5}
}
```

- Query with minimum participants:  
```json
{
  "query": "lung cancer",
  "options": {"min_participants": 100, "top_k": 5}
}
```

**Sample Response (top result):**  
```json
{
  "dataset_id": "ctg2025_1",
  "trial_id": "NCT06396481",
  "score": 0.726,
  "disease": "GBM|DIPG Brain Tumor|Medulloblastoma",
  "phase": "EARLY_PHASE1",
  "n_participants": 25
}
```

---

### 6. `trial-rag`  
Constructs a Retrieval-Augmented Generation prompt for natural language QA over trials.

**Example:**  
```
From "MCP BioForensics", run trial-rag with:
query="Show me Phase 2 breast cancer trials with 200+ patients"
```

**Response:**  
Returns a `messages` array containing a compact context built from search results, suitable for input to an LLM assistant.

---

## Data Schema (Canonical)

| Column          | Type      | Description                             |
|-----------------|-----------|---------------------------------------|
| trial_id        | TEXT (PK) | Unique NCT/registry identifier        |
| dataset_id      | TEXT      | Dataset identifier (supports multiple)|
| disease         | TEXT      | Normalized disease label               |
| phase           | TEXT      | Canonical phase codes (I, II, III, IV)|
| n_participants  | INT       | Number of participants in trial       |
| summary         | TEXT      | Brief trial description                |
| outcomes_text   | TEXT      | Primary and secondary outcomes        |
| status          | TEXT      | Trial status (Recruiting, Completed)  |
| sponsor         | TEXT      | Sponsor organization                   |
| start_date      | DATE      | Trial start date (optional)            |
| end_date        | DATE      | Trial end date (optional)              |

---

## Real Run Examples

### Hybrid Search Example

**Query:**  
```
Phase II trials for glioblastoma with >100 participants
```

**Top 3 Results:**

| Trial ID    | Disease           | Phase   | Participants | Dataset    |
|-------------|-------------------|---------|--------------|------------|
| NCT03776071 | Glioblastoma      | PHASE3  | 260          | ctg2025_1  |
| NCT04253873 | High-grade Gliomas| PHASE2  | 150          | ctg2025_1  |
| NCT04704817 | Glioblastoma      | PHASE2  | 180          | ctg2025    |

---

## Roadmap

| Milestone             | Status      | Description                                   |
|-----------------------|-------------|-----------------------------------------------|
| 1. Ingestion & Schema | Completed   | CSV → SQLite/Postgres loader, schema normalization, Alembic migrations |
| 2. Indexing           | Completed   | Sentence-Transformers embeddings, FAISS index construction |
| 3. Hybrid Retrieval   | Completed   | Semantic + structured SQL search, Pydantic validation |
| 4. Forensics          | Planned     | Dataset hashing, duplicate and anomaly detection |
| 5. Reporting          | Planned     | Jinja2 templates for Markdown/CSV/PDF export |
| 6. Evaluation Harness | Planned     | QA datasets, precision@k metrics, regression tests |

---

## Project Structure

```
mcp-bioforensics/
├─ .github/workflows/ci.yml          # CI: lint, type-check, tests
├─ .pre-commit-config.yaml           # ruff/black/mypy hooks
├─ LICENSE                          # MIT License
├─ README.md                       # This documentation
├─ pyproject.toml                  # Poetry packaging and dependencies
├─ data/samples/trials_sample.csv  # Sample dataset
├─ src/mcp_bioforensics/
│  ├─ server.py                    # FastMCP server entrypoint
│  ├─ cli.py                       # CLI commands (ingest, index, query)
│  ├─ db/
│  │  └─ models.py                 # SQLAlchemy ORM models
│  ├─ ingest/                      # Data loaders and cleaners
│  ├─ index/                       # Embedding and FAISS index logic
│  ├─ retrieval/                   # Hybrid retriever and RAG prompt builders
│  ├─ forensics/                   # Forensic hashing and anomaly checks (planned)
│  └─ reporting/                   # Reporting templates and exporters (planned)
└─ tests/                         # Pytest test suites (ingestion and smoke tests)
```

---

## Commands (CLI)

```bash
poetry run biofx ingest <path>     # Ingest CSV data into SQLite/Postgres
poetry run biofx index             # Build or update FAISS vector index
poetry run biofx query "..."       # Run hybrid semantic + structured query
poetry run biofx-mcp               # Start FastMCP server exposing MCP tools
```

---

## Testing & Continuous Integration

- **pytest** with ~60% coverage on ingestion and smoke tests.  
- Retrieval and indexing tests are under active development.  
- Code style and typing enforced via **ruff**, **black**, and **mypy**.  
- CI pipelines run on Python 3.10–3.12 to ensure compatibility.

To run tests locally:

```bash
poetry run ruff check . && poetry run ruff format --check .
poetry run mypy src
poetry run pytest -q
```

---

## Contributing

Contributions are welcome! Please run pre-commit hooks before submitting pull requests:

```bash
pre-commit install
pre-commit run --all-files
```

---

## Security

No personally identifiable information (PII) is ingested. For vulnerability reporting, please refer to `SECURITY.md`.

---

## License

MIT — see the `LICENSE` file.

---

## Acknowledgements

- MCP ecosystem & FastMCP framework  
- FAISS and Sentence-Transformers for semantic indexing  
- Open clinical research community for datasets and standards
