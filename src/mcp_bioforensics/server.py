from typing import Any

from fastmcp import FastMCP

app = FastMCP("mcp-bioforensics")


@app.tool()
def list_trials(disease: str) -> list[dict[str, Any]]:
    """Return trial rows filtered by disease (stub)."""
    return [{"trial_id": "NCT000000", "disease": disease, "phase": "II"}]


def run() -> None:
    app.run()
