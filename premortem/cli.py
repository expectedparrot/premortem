from __future__ import annotations

import typer

from .commands.agent_end import app as agent_end_app
from .commands.analyze import app as analyze_app
from .commands.docs import app as docs_app
from .commands.graph import app as graph_app
from .commands.ingest import app as ingest_app
from .commands.init import app as init_app
from .commands.job import app as job_app
from .commands.mitigate import app as mitigate_app
from .commands.persona import app as persona_app
from .commands.project import app as project_app
from .commands.reason import app as reason_app
from .commands.report import app as report_app
from .commands.score import app as score_app
from .commands.status import app as status_app
from .commands.workflow import app as workflow_app

app = typer.Typer(help="Gary Klein style pre-mortem analysis CLI.")
app.add_typer(agent_end_app)
app.add_typer(init_app)
app.add_typer(project_app, name="project")
app.add_typer(status_app)
app.add_typer(persona_app, name="persona")
app.add_typer(reason_app, name="reason")
app.add_typer(graph_app, name="graph")
app.add_typer(score_app, name="score")
app.add_typer(mitigate_app, name="mitigate")
app.add_typer(report_app, name="report")
app.add_typer(ingest_app, name="ingest")
app.add_typer(analyze_app, name="analyze")
app.add_typer(job_app, name="job")
app.add_typer(docs_app, name="docs")
app.add_typer(workflow_app, name="workflow")


def main() -> None:
    app()


if __name__ == "__main__":
    main()
