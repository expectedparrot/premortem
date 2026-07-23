from __future__ import annotations

import typer

from .. import docs as docs_lib
from ..renderer import render_markdown, table
from ..store import PremortemError
from .common import HumanOption, QuietOption, fail, finish, should_emit_json

app = typer.Typer(help="Read and search built-in premortem guidance.")


@app.command("list")
def list_docs(
    human: bool = HumanOption,
    quiet: bool = QuietOption,
) -> None:
    command = "docs list"
    json_flag = should_emit_json(human)
    topics = docs_lib.list_topics()
    data = [{"topic": topic.name, "title": topic.title, "summary": topic.summary} for topic in topics]
    if json_flag:
        finish(command, data, True, quiet)
        return
    if quiet:
        return
    tbl = table("Topic", "Title", "Summary")
    for item in data:
        tbl.add_row(item["topic"], item["title"], item["summary"])
    from ..renderer import console

    console.print(tbl)


@app.command("show")
def show_doc(
    topic: str,
    human: bool = HumanOption,
    quiet: bool = QuietOption,
) -> None:
    command = "docs show"
    json_flag = should_emit_json(human)
    try:
        text = docs_lib.read_topic(topic)
    except KeyError as exc:
        fail(
            command,
            PremortemError("ID_NOT_FOUND", "Documentation topic not found.", context=topic, hint="Run `premortem docs list`."),
            json_flag,
        )
    if json_flag:
        finish(command, {"topic": topic, "markdown": text}, True, quiet)
        return
    if not quiet:
        render_markdown(text)


@app.command("search")
def search_docs(
    query: str,
    human: bool = HumanOption,
    quiet: bool = QuietOption,
) -> None:
    command = "docs search"
    json_flag = should_emit_json(human)
    matches = docs_lib.search(query)
    if json_flag:
        finish(command, {"query": query, "matches": matches}, True, quiet)
        return
    if quiet:
        return
    tbl = table("Topic", "Score", "Snippet")
    for match in matches:
        tbl.add_row(str(match["topic"]), str(match["score"]), str(match["snippet"]))
    from ..renderer import console

    console.print(tbl)
