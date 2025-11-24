import typer
from rich import print
from rich.table import Table

from mcp_bioforensics.db.session import SessionLocal
from mcp_bioforensics.index.faiss_store import build_index
from mcp_bioforensics.ingest.loaders import ingest_csv
from mcp_bioforensics.retrieval.hybrid import hybrid_search

app = typer.Typer(add_completion=False, no_args_is_help=True)


@app.command()  # type: ignore[misc]
def ingest(
    path: str,
    dataset: str = typer.Option(..., "--dataset", "-d", help="Dataset ID to tag rows with"),
    name: str | None = typer.Option(None, "--name", "-n", help="Human-friendly dataset name"),
) -> None:
    """Ingest CSV into Postgres/SQLite."""
    count = ingest_csv(path, dataset_id=dataset, dataset_name=name)
    print(
        f"[bold green]Ingested[/bold green] {count} rows into dataset "
        f"[cyan]{dataset}[/cyan] from {path}"
    )


@app.command()  # type: ignore[misc]
def index() -> None:
    """Build FAISS index (stub)."""
    with SessionLocal() as s:
        stats = build_index(s)
    print(
        f"[bold green]Built index with {stats.count}"
        f"ectors (dim={stats.dim}) at {stats.index_path}[/bold green]"
    )


@app.command()  # type: ignore[misc]
def query(
    q: str,
    phase: str | None = typer.Option(None, "--phase", help="Filter by trial phase"),
    disease: str | None = typer.Option(None, "--disease", help="Filter by disease/condition"),
    min_participants: int | None = typer.Option(
        None, "--min-participants", help="Minimum participants"
    ),
    status: str | None = typer.Option(None, "--status", help="Filter by study status"),
) -> None:
    """Hybrid RAG query with structured filters."""
    results = hybrid_search(
        q, phase=phase, disease=disease, min_participants=min_participants, status=status, top_k=10
    )

    table = Table(title="Query Results")
    table.add_column("Dataset", justify="left", style="white")
    table.add_column("Trial ID", justify="right", style="cyan", no_wrap=True)
    table.add_column("Score", justify="right", style="magenta")
    table.add_column("Disease", style="green")
    table.add_column("Phase", style="yellow")
    table.add_column("N", justify="right", style="blue")

    for r in results:
        table.add_row(
            r.dataset_id, r.trial_id, f"{r.score:.3f}", r.disease, r.phase, str(r.n_participants)
        )

    print(table)


if __name__ == "__main__":
    app()
