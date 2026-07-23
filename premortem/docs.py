from __future__ import annotations

import re
from dataclasses import dataclass
from importlib import resources


@dataclass(frozen=True)
class DocTopic:
    name: str
    title: str
    summary: str


TOPICS: list[DocTopic] = [
    DocTopic("facilitation-guide", "Pre-mortem Facilitation Guide", "How to facilitate the analysis from intake through reports."),
    DocTopic("overview", "Pre-mortem Workflow Overview", "Short phase map and state ownership summary."),
    DocTopic("failure-statement", "Failure Statement", "How to craft a definitive outcome-focused failure statement."),
    DocTopic("personas", "Personas", "How to generate and review stakeholder personas."),
    DocTopic("failure-reasons", "Failure Reasons", "Episodic and structural failure narrative guidance."),
    DocTopic("causal-graph", "Causal Graph", "How to synthesize a compact causal graph."),
    DocTopic("mitigations", "Mitigations", "How to elicit concrete node-targeted mitigations."),
    DocTopic("research-agenda", "Research Agenda", "How to identify empirical questions before launch."),
    DocTopic("reporting", "Reporting", "Expected report contents and transparency notes."),
]


def list_topics() -> list[DocTopic]:
    return TOPICS


def topic_names() -> set[str]:
    return {topic.name for topic in TOPICS}


def read_topic(name: str) -> str:
    if name not in topic_names():
        raise KeyError(name)
    return resources.files("premortem.docs_content").joinpath(f"{name}.md").read_text()


def _snippet(text: str, terms: list[str]) -> str:
    lower = text.lower()
    positions = [lower.find(term) for term in terms if term and lower.find(term) >= 0]
    pos = min(positions) if positions else 0
    start = max(0, pos - 90)
    end = min(len(text), pos + 220)
    snippet = re.sub(r"\s+", " ", text[start:end]).strip()
    if start:
        snippet = "..." + snippet
    if end < len(text):
        snippet += "..."
    return snippet


def search(query: str) -> list[dict[str, object]]:
    terms = [term.lower() for term in re.findall(r"[A-Za-z0-9_-]+", query)]
    results: list[dict[str, object]] = []
    for topic in TOPICS:
        text = read_topic(topic.name)
        haystack = f"{topic.name} {topic.title} {topic.summary} {text}".lower()
        score = sum(haystack.count(term) for term in terms)
        if not score:
            continue
        results.append(
            {
                "topic": topic.name,
                "title": topic.title,
                "summary": topic.summary,
                "score": score,
                "snippet": _snippet(text, terms),
            }
        )
    results.sort(key=lambda item: int(item["score"]), reverse=True)
    return results
