"""Render only reviewed result data with shared templates."""

from __future__ import annotations

from html import escape
from pathlib import Path
from string import Template
from typing import Any

from arena.errors import ReplayError


def _outcome_markup(outcomes: dict[str, dict[str, Any]]) -> str:
    rows = []
    for name, value in outcomes.items():
        evidence = "".join(f"<li>{escape(ref)}</li>" for ref in value.get("evidence", []))
        rows.append(
            '<article class="outcome">'
            f"<h3>{escape(name)}</h3>"
            f'<p class="status status-{escape(value["status"])}">{escape(value["status"])}</p>'
            f"<p>{escape(value['summary'])}</p>"
            f"<details><summary>Evidence references</summary><ul>{evidence}</ul></details>"
            "</article>"
        )
    return "".join(rows)


def _media_markup(media: list[dict[str, str]]) -> str:
    items = []
    for item in media:
        path = escape(item["path"], quote=True)
        caption = escape(item["caption"])
        if item["kind"] == "video":
            body = f'<video controls preload="metadata"><source src="{path}" type="video/mp4"></video>'
        elif item["kind"] == "image":
            body = f'<img loading="lazy" src="{path}" alt="{caption}">'
        else:
            raise ReplayError("reviewed result contains unsupported public media")
        items.append(f"<figure>{body}<figcaption>{caption}</figcaption></figure>")
    return "".join(items) or "<p>No public media is attached to this synthetic result.</p>"


def render_result(result: dict[str, Any], output: str | Path, template_root: str | Path) -> Path:
    output_path = Path(output)
    templates = Path(template_root)
    try:
        template = Template((templates / "result.html").read_text(encoding="utf8"))
        stylesheet = (templates / "result.css").read_text(encoding="utf8")
    except OSError as error:
        raise ReplayError(f"Cannot read result template: {error}") from error

    limitations = "".join(f"<li>{escape(item)}</li>" for item in result.get("limitations", []))
    denominator = result["denominator"]
    summary = (
        f"Run status: {result['runStatus']}. "
        f"Denominator: {'included' if denominator['included'] else 'excluded'} "
        f"({denominator['reason']})."
    )
    values = {
        "title": escape(result["scenarioTitle"]),
        "scenario_id": escape(result["scenarioId"]),
        "run_id": escape(result["runId"]),
        "summary": escape(summary),
        "prompt_id": escape(result["frozenPromptId"]),
        "prompt_sha": escape(result["actualPromptSha256"]),
        "comparison_key": escape(result["comparisonKey"]),
        "outcomes": _outcome_markup(result["outcomes"]),
        "media": _media_markup(result.get("publicMedia", [])),
        "limitations": limitations,
    }
    output_path.mkdir(parents=True, exist_ok=True)
    (output_path / "index.html").write_text(template.substitute(values), encoding="utf8")
    (output_path / "result.css").write_text(stylesheet, encoding="utf8")
    return output_path / "index.html"
