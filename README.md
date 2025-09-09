# MCP BioForensics

[![CI](https://github.com/axdithyaxo/mcp-bioforensics/actions/workflows/ci.yml/badge.svg)](https://github.com/axdithyaxo/mcp-bioforensics/actions/workflows/ci.yml)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

AI‑Assisted Clinical Trial Explorer built on the **Model Context Protocol (MCP)**. 

**Ingestion → Indexing (FAISS) → Hybrid Retrieval (FAISS + SQL) → RAG Answers → Forensic Reporting**

---

## 🔍 What it does
- **Ingest** clinical/biomedical CSVs into PostgreSQL (canonical schema).
- **Index** free‑text fields (summaries/outcomes) into **FAISS** with Sentence‑Transformers.
- **Query** via **RAG**: natural language → relevant trials → structured JSON + Markdown table.
- **Forensics**: dataset hashing, anomaly checks (missing outcomes, duplicate IDs, impossible dates).
- **Report**: export Markdown/CSV summaries by disease/phase; optional PDF via pandoc.

> Built for reliability and auditability: typed I/O, deterministic test mode, CI on 3.10–3.12.

---

## ⚡ Quickstart

```bash
# 1) Clone and install (with optional vector + db extras)
git clone https://github.com/axdithyaxo/mcp-bioforensics.git
cd mcp-bioforensics
poetry install -E vector -E db

# 2) Sanity check CLI
poetry run biofx --help

# 3) Load sample data and index
poetry run biofx ingest data/samples/trials_sample.csv
poetry run biofx index

# 4) Ask a question (stubbed until PR2/PR3 completes)
poetry run biofx query "Phase II trials for glioblastoma with >100 participants"
```

### Run the MCP server
```bash
poetry run biofx-mcp
```
The server exposes typed **tools** (e.g., `list_trials`) discoverable by any MCP‑compatible client.

> Tip: If you use Claude Desktop, add this server to your MCP config and run a sample tool call.

---

## 🧱 Project structure
```
mcp-bioforensics/
├─ .github/workflows/ci.yml          # CI: lint, type-check, tests
├─ .pre-commit-config.yaml           # ruff/black/mypy hooks
├─ LICENSE                           # MIT (add if missing)
├─ README.md
├─ pyproject.toml                    # Poetry packaging
├─ data/samples/trials_sample.csv    # tiny example dataset
├─ src/mcp_bioforensics/
│  ├─ server.py                      # FastMCP server entry
│  ├─ cli.py                         # Typer CLI (ingest/index/query)
│  ├─ db/
│  │  └─ models.py                   # SQLAlchemy ORM (Trial)
│  ├─ ingest/                        # loaders/cleaners (next PR)
│  ├─ index/                         # embeddings + FAISS (next PR)
│  ├─ retrieval/                     # hybrid retriever + RAG (next PR)
│  ├─ forensics/                     # hashing/checks (next PR)
│  └─ reporting/                     # templating/export (next PR)
└─ tests/                            # pytest suites
```

---

## 🛠️ Commands (CLI)

```bash
poetry run biofx ingest <path>     # CSV → Postgres (normalize schema)
poetry run biofx index             # Build/update FAISS index
poetry run biofx query "..."       # RAG query → JSON + Markdown table
poetry run biofx-mcp               # Start FastMCP server
```

> Until PR2/PR3, commands are stubs that print progress. They’re wired for tests/CI already.

---

## 🧬 Data schema (canonical)
| column          | type        | notes                          |
|-----------------|-------------|--------------------------------|
| trial_id        | TEXT (PK)   | NCT/registry ID                |
| disease         | TEXT        | normalized disease label       |
| phase           | TEXT        | {I, II, III, IV}               |
| n_participants  | INT         | trial size                     |
| summary         | TEXT        | brief description              |
| outcomes_text   | TEXT        | primary/secondary outcomes     |
| status          | TEXT        | Recruiting/Completed/etc.      |
| sponsor         | TEXT        | sponsor name                   |
| start_date      | DATE        | optional                       |
| end_date        | DATE        | optional                       |

---

## 🧪 Testing & CI
- **pytest** with coverage; deterministic test mode for RAG.
- **ruff/black/mypy** enforce style and typing.
- GitHub Actions runs on Python 3.10–3.12.

Run locally:
```bash
poetry run ruff check . && poetry run ruff format --check .
poetry run mypy src
poetry run pytest -q
```

---

## 🗺️ Roadmap (milestones)
1. **Ingestion & Schema** — CSV→Postgres loader, phase/status normalization, Alembic migration.
2. **Indexing** — Sentence‑Transformers embeddings, FAISS store, ID mapping.
3. **Hybrid Retrieval + RAG** — FAISS top‑k + SQL filters → Pydantic‑validated JSON + Markdown table.
4. **Forensics** — dataset hashing, duplicate/outcome checks, impossible date flags.
5. **Reporting** — Jinja2 templates → Markdown/CSV (optional PDF via pandoc).
6. **Eval Harness** — tiny labeled QA set, precision@k + regression tests.

---

## 🤝 Contributing
PRs welcome! Please run pre‑commit hooks and keep changes small/atomic.

```bash
pre-commit install
pre-commit run --all-files
```

---

## 🔒 Security
See `SECURITY.md` for how to report vulnerabilities. No PII should be ingested.

---

## 📄 License
MIT — see `LICENSE`.

---

## 🙌 Acknowledgements
- MCP ecosystem & FastMCP
- FAISS and Sentence‑Transformers
- The open clinical research community
