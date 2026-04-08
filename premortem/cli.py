from __future__ import annotations

import typer

from .commands.analyze import app as analyze_app
from .commands.graph import app as graph_app
from .commands.ingest import app as ingest_app
from .commands.init import app as init_app
from .commands.mitigate import app as mitigate_app
from .commands.persona import app as persona_app
from .commands.reason import app as reason_app
from .commands.report import app as report_app
from .commands.score import app as score_app
from .commands.status import app as status_app

app = typer.Typer(help="Gary Klein style pre-mortem analysis CLI.")
app.add_typer(init_app)
app.add_typer(status_app)
app.add_typer(persona_app, name="persona")
app.add_typer(reason_app, name="reason")
app.add_typer(graph_app, name="graph")
app.add_typer(score_app, name="score")
app.add_typer(mitigate_app, name="mitigate")
app.add_typer(report_app, name="report")
app.add_typer(ingest_app, name="ingest")
app.add_typer(analyze_app, name="analyze")


def main() -> None:
    app()


if __name__ == "__main__":
    main()
