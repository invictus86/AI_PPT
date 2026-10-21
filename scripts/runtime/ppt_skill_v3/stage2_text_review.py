"""Bind controller per-image proofreading to the actual images and Stage 1 text."""
from __future__ import annotations

from pathlib import Path
from typing import Any

from .file_hashing import file_sha256
from .json_io import read_json
from .validation import ValidationError, validate_image_result


def text_review_inputs(run_dir: str | Path, scope: str) -> tuple[dict[str, str], list[dict[str, Any]]]:
    root = Path(run_dir)
    content = read_json(root / "_state/阶段1/content.json")
    from .stage1_plan import _validate_clean_transcript_doc
    transcript = _validate_clean_transcript_doc(root, content)
    basis = {path.relative_to(root).as_posix(): file_sha256(path) for path in
             (root / "_state/阶段1/content.json", transcript)}
    pages = {slide["slide_index"]: slide for slide in content["slides"]}
    if len(pages) != len(content["slides"]):
        raise ValidationError("duplicate Stage 1 slide indices")

    from .image_style import result_is_current
    from .stage2_trial import _usable_trial_result, _usable_result
    results = []
    if scope == "cover_options":
        for option_id in "ABCD":
            path = root / f"_state/阶段2/cover_options/results/cover_option_{option_id}.json"
            raw = read_json(path)
            result = validate_image_result(raw, production=not bool(raw.get("fixture")))
            if (result.get("purpose") != "cover_option" or result.get("option_id") != option_id
                    or not result_is_current(root, result)
                    or pages.get(result["slide_index"], {}).get("page_type") != "cover"):
                raise ValidationError(f"cover {option_id} is missing or stale for text review")
            results.append(result)
    elif scope in {"trial_first5", "full_image_deck"}:
        indices = (read_json(root / "_state/阶段2/trial_first5/selection.json").get("selected_slide_indices", [])
                   if scope == "trial_first5" else list(pages))
        if not indices or len(set(indices)) != len(indices) or any(i not in pages for i in indices):
            raise ValidationError("text review requires the complete current page selection")
        for index in indices:
            result = (_usable_trial_result(root, index) if scope == "trial_first5"
                      else _usable_result(root, index, "full_slide"))
            if not result:
                raise ValidationError(f"slide {index} is missing or stale for text review")
            results.append(result)
        if scope == "full_image_deck":
            manifest = read_json(root / "_state/阶段2/manifests/image_deck.json")
            images = manifest.get("images", [])
            if sorted(images) != sorted(result["image_path"] for result in results):
                raise ValidationError("full-deck text review must match the actual PDF image manifest")
            results.sort(key=lambda result: images.index(result["image_path"]))
    else:
        raise ValidationError("unknown text review scope")

    rows = []
    for result in results:
        text = pages[result["slide_index"]].get("final_visible_text")
        if not isinstance(text, list) or any(not isinstance(item, str) for item in text):
            raise ValidationError("Stage 1 final_visible_text is required for proofreading")
        row = {"slide_index": result["slide_index"], "image_path": result["image_path"],
               "image_sha256": result["image_sha256"], "reference_text": text}
        if scope == "cover_options":
            row["option_id"] = result["option_id"]
        rows.append(row)
    return basis, rows


def require_current_text_reviews(run_dir: str | Path, review: dict[str, Any]) -> None:
    basis, expected = text_review_inputs(run_dir, review["review_scope"])
    if review.get("text_review_basis") != basis:
        raise ValidationError("text review is stale: recheck current Stage 1 text and clean transcript")
    actual = review.get("text_reviews", [])
    if len(actual) != len(expected):
        raise ValidationError("text review must cover every image exactly once")
    def identity(row):
        return row.get("slide_index"), row.get("option_id")
    actual_by_id = {identity(row): row for row in actual}
    if len(actual_by_id) != len(actual):
        raise ValidationError("duplicate per-image text review")
    for row in expected:
        recorded = actual_by_id.get(identity(row), {})
        if any(recorded.get(key) != value for key, value in row.items()):
            raise ValidationError(f"text review missing or stale for slide {row['slide_index']} {row.get('option_id', '')}")
