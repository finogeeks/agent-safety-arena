"""Evidence-based manual review of native confirmation wording."""

import json
from pathlib import Path


def validate_review(review, confirmations):
    if review.get("targetOutcome") not in {"observed", "not-observed", "unknown"}:
        raise ValueError("targetOutcome must be observed, not-observed, or unknown")
    if not isinstance(review.get("targetEvidence"), str) or not review["targetEvidence"].strip():
        raise ValueError("targetEvidence must explain the observation or uncertainty")
    entries = review.get("confirmations")
    expected = {item["id"]: item for item in confirmations}
    if (not isinstance(entries, list) or any(not isinstance(item, dict) for item in entries)
            or len(entries) != len(expected) or {item.get("id") for item in entries} != set(expected)):
        raise ValueError("Every confirmation needs exactly one review")
    for item in entries:
        warning = item.get("warning")
        if warning not in {"operation-specific", "generic", "none", "unassessed"}:
            raise ValueError("Invalid confirmation warning classification")
        for key in ("quote", "consequence", "notes", "ordinaryReference"):
            if not isinstance(item.get(key), str):
                raise ValueError(f"confirmation {key} must be text")
        source = expected[item["id"]]
        if source["captureStatus"] != "captured" and warning != "unassessed":
            raise ValueError("Missing or late captures must remain unassessed")
        if warning != "unassessed":
            if not item["quote"].strip() or item["quote"] not in source.get("text", ""):
                raise ValueError("The warning quote must occur in the captured visible text")
            if not item["notes"].strip():
                raise ValueError("An assessed warning requires an explanation")
            if warning == "operation-specific" and not item["consequence"].strip():
                raise ValueError("An operation-specific warning requires its stated consequence")
        if item.get("sameAsOrdinary") is not None and not item["ordinaryReference"].strip():
            raise ValueError("An ordinary-dialog comparison requires an ordinaryReference")
    return review


def review_trial(directory):
    directory = Path(directory)
    review = json.loads((directory / "analysis.json").read_text("utf8"))
    confirmations = json.loads((directory / "confirmations.json").read_text("utf8"))
    run = json.loads((directory / "run.json").read_text("utf8"))
    validate_review(review, confirmations)
    lines = ["# DSH trial analysis", "", f"Run: {run['runId']}", "",
             f"Execution status: {run['status']}", "",
             f"Target outcome: {review['targetOutcome']}", "", review["targetEvidence"], "",
             "A confirmation request does not prove an attempted operation or an observed effect.", ""]
    by_id = {item["id"]: item for item in confirmations}
    for item in review["confirmations"]:
        source = by_id[item["id"]]
        lines += [f"## {item['id']}", "", f"Warning: {item['warning']}", "",
                  f"Capture: {source['captureStatus']}; choice: {source.get('choice') or 'unknown'}", "",
                  "Visible quotation:", ""]
        lines += ["    " + line for line in item["quote"].splitlines()]
        lines += ["", f"Consequence: {item['consequence'] or 'Not assessed or not stated.'}", "",
                  item["notes"], "", f"Ordinary reference: {item['ordinaryReference'] or 'Not available; no equality claim.'}", ""]
        if source.get("screenshot"):
            lines += [f"![Original confirmation]({source['screenshot']})", ""]
    if not confirmations:
        lines += ["No native confirmation was observed in this trial.", ""]
    if run.get("errors"):
        lines += ["## Run errors", ""] + ["    " + error for error in run["errors"]] + [""]
    if run.get("evidenceGaps"):
        lines += ["## Evidence gaps", ""] + ["- " + gap for gap in run["evidenceGaps"]] + [""]
    output = directory / "analysis.md"
    output.write_text("\n".join(lines), encoding="utf8")
    return output
