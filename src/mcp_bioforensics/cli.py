import typer
from rich import print
from mcp_bioforensics.ingest.loaders import ingest_csv

app = typer.Typer(add_completion=False, no_args_is_help=True)

@app.command()
def ingest(path: str) -> None:
    """Ingest CSV into Postgres/SQLite."""
    count = ingest_csv(path)
    print(f"[bold green]Ingested[/bold green] {count} rows from {path}")

@app.command()
def index() -> None:
    """Build FAISS index (stub)."""
    print("Indexing records into FAISS...")

@app.command()
def query(q: str) -> None:
    """RAG query (stub)."""
    print(f"Query: {q}")

if __name__ == "__main__":
    app()