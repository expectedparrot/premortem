from __future__ import annotations

import json
from typing import Any

from rich.console import Console
from rich.markdown import Markdown
from rich.panel import Panel
from rich.table import Table

from .store import PremortemError

console = Console()


def emit_json(data: dict[str, Any]) -> None:
    console.print_json(json.dumps(data))


def render_error(err: PremortemError) -> None:
    console.print(f"[red]Error:[/red] [{err.code}] {err.message}")
    if err.context:
        console.print(f"  Context: {err.context}")
    if err.hint:
        console.print(f"  Hint: {err.hint}")


def render_markdown(text: str) -> None:
    console.print(Markdown(text))


def render_kv_panel(title: str, items: list[tuple[str, str]]) -> None:
    body = "\n".join(f"[bold]{key}:[/bold] {value}" for key, value in items)
    console.print(Panel.fit(body, title=title))


def table(*columns: str) -> Table:
    tbl = Table(show_header=True, header_style="bold cyan")
    for column in columns:
        tbl.add_column(column)
    return tbl
