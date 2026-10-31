"""Passive contracts for the three-step, deeply enhanced thematic workflow.

The controller supplies actual human authorization and evidence-based reviews.
File presence and this validator never judge educational quality themselves.
"""
from __future__ import annotations

import hashlib
from pathlib import Path
from typing import Any

from .events import append_event
from .json_io import read_json, write_json
from .state import read_state, write_state
from .time_utils import now_iso
from .validation import ValidationError

SCENES = {"class_meeting", "parent_meeting"}
BANDS = {"primary", "junior_high", "senior_high"}
REVIEW_CRITERIA = {
    "planning": ("theme_framework", "substantial_enhancement", "audience_and_grade_fit",
                 "reasoning_and_values", "practical_activities", "transfer_and_reflection",
                 "freshness_and_sources", "expression_and_visual_intent"),
    "deck": ("actual_page_meaning", "reasoning_and_values", "audience_and_grade_fit",
             "practical_activities", "freshness_and_main_images", "legibility_and_accuracy"),
    "package": ("page_and_title_alignment", "teacher_usability", "duration_and_activity_feasibility",
                "oral_naturalness", "grade_adaptation", "no_fabricated_effects"),
}


def _hash(path: Path) -> str:
    return "sha256:" + hashlib.sha256(path.read_bytes()).hexdigest()


def configure_project(run_dir: str | Path, settings: dict[str, Any]) -> dict[str, Any]:
    """Four editable inputs; extra inferred context is resolved by the controller.

    A value has {value, source, evidence}. 'explicit' means supplied by the human,
    not copied from an old source deck. Unspecified grade stays '通用版'.
    """
    root = Path(run_dir)
    state = read_state(root)
    if state["current_stage"] not in {"stage0", "stage1"}:
        raise ValidationError("change target settings before covers; reopen planning for later changes")
    allowed = {"school_stage", "scene", "page_count", "duration_minutes", "grade", "theme", "usage_date", "applicability"}
    if not isinstance(settings, dict) or set(settings) - allowed:
        raise ValidationError("unsupported thematic settings")
    brief = dict(state.get("thematic_brief", {}))
    sources = dict(brief.get("sources", {}))
    for key, entry in settings.items():
        if not isinstance(entry, dict) or entry.get("source") not in {"explicit", "project", "source", "inferred", "default"}:
            raise ValidationError(f"{key}: value/source/evidence are required")
        if not isinstance(entry.get("evidence"), str) or not entry["evidence"].strip():
            raise ValidationError(f"{key}: evidence is required")
        if sources.get(key, {}).get("source") == "explicit" and entry["source"] != "explicit":
            continue
        value = entry.get("value")
        if key == "school_stage" and value not in BANDS:
            raise ValidationError("school_stage must be primary/junior_high/senior_high")
        if key == "scene" and value not in SCENES:
            raise ValidationError("scene must be class_meeting/parent_meeting")
        if key == "page_count":
            if (not isinstance(value, list) or len(value) != 2 or
                    any(type(n) is not int or n < 5 for n in value) or value[0] > value[1]):
                raise ValidationError("page_count must be [min,max], including the cover, min>=5")
        elif key == "duration_minutes":
            if type(value) is not int or value < 1:
                raise ValidationError("duration_minutes must be a positive integer")
        elif not isinstance(value, str) or not value.strip():
            raise ValidationError(f"{key} must be non-empty text")
        brief[key] = value
        sources[key] = {"source": entry["source"], "evidence": entry["evidence"]}
    brief.setdefault("grade", "通用版")
    brief.setdefault("page_count", [20, 30])
    sources.setdefault("grade", {"source": "default", "evidence": "学段通用，不自动拆分SKU"})
    sources.setdefault("page_count", {"source": "default", "evidence": "20—30页为参考范围，包含封面"})
    if brief.get("scene"):
        if "duration_minutes" not in brief or sources.get("duration_minutes", {}).get("source") == "default":
            brief["duration_minutes"] = 60 if brief["scene"] == "parent_meeting" else 40
        sources.setdefault("duration_minutes", {"source": "default", "evidence": "设计时长假设，非学校事实"})
    brief["sources"] = sources
    state["thematic_brief"] = brief
    state.setdefault("controller_acceptances", {}).update({"stage1_plan": False, "stage2_image_deck": False})
    state["confirmed"]["stage1_plan"] = False
    state["quality"]["stage1"] = "needs_review"
    write_state(root, state)
    append_event(root, "target_settings_recorded", "main_controller", settings=brief)
    return brief


def education_context_from_brief(brief: dict[str, Any]) -> dict[str, Any]:
    scene = brief.get("scene")
    if scene not in SCENES:
        return {}
    band = brief.get("school_stage", "unknown")
    return {"is_k12": True, "confidence": "inferred_high", "school_stage": band,
            "grade": brief.get("grade", "通用版"), "scene": scene,
            "audience": "parents" if scene == "parent_meeting" else "students",
            "subject": "家校共育" if scene == "parent_meeting" else "主题教育",
            "subject_group": "integrated", "lesson_title": brief.get("theme", "主题活动"),
            "class_type": "家长会" if scene == "parent_meeting" else "主题班会",
            "lesson_scope": "thematic_project", "period_count": 1,
            "minutes_per_period": brief.get("duration_minutes", 60 if scene == "parent_meeting" else 40),
            "period_strategy": "explicit" if brief.get("sources", {}).get("duration_minutes", {}).get("source") == "explicit" else "single_period_default",
            "plan_type": "meeting_implementation" if scene == "parent_meeting" else "class_meeting_lesson",
            "applicability": brief.get("applicability", "所选学段通用；按活动采用简化或拓展替代用法")}


def authorize_step(run_dir: str | Path, step: int | str, evidence: str) -> dict[str, Any]:
    root = Path(run_dir)
    state = read_state(root)
    if step != "2-3":
        try:
            step = int(step)
        except (ValueError, TypeError):
            raise ValidationError("step must be 1, 2, 3 or 2-3")
    valid = {1: {"initialized", "stage1_draft", "planning_revision_requested", "revision_requested"},
             2: {"waiting_user_cover_style_selection"},
             3: {"waiting_user_trial_first5_confirmation"},
             "2-3": {"waiting_user_cover_style_selection"}}
    if step not in valid or state["status"] not in valid[step]:
        raise ValidationError("step authorization is not valid at the current checkpoint")
    if not isinstance(evidence, str) or not evidence.strip():
        raise ValidationError("quote the actual human request authorizing this entire step")
    entry = {"step": step, "evidence": evidence, "recorded_at": now_iso(),
             "covers": {1: ["stage0", "stage1", "stage2_covers"], 2: ["stage2_trial"],
                        3: ["stage2_remaining", "stage2_qa", "stage3", "stage4"],
                        "2-3": ["stage2_trial", "stage2_remaining", "stage2_qa", "stage3", "stage4"]}[step]}
    if step in {2, 3, "2-3"}:
        entry["basis"] = authorization_basis(root, step)
    # Switching back to the ordinary Step 2 explicitly removes continuous authority.
    if step in {2, "2-3"}:
        for key in ("2", "3", "2-3"):
            state["workflow"]["authorizations"].pop(key, None)
        state["controller_acceptances"]["stage2_trial_first5"] = False
        state["confirmed"]["stage2_trial_first5"] = False
    state["workflow"]["authorizations"][str(step)] = entry
    write_state(root, state)
    append_event(root, "step_authorized", "main_controller", **entry)
    return entry


def require_step(state: dict[str, Any], step: int) -> None:
    if step in {2, 3} and "2-3" in state.get("workflow", {}).get("authorizations", {}):
        require_combined_authorization(state)
        if step == 3:
            require_trial_continuation(state)
        return
    if str(step) not in state.get("workflow", {}).get("authorizations", {}):
        raise ValidationError(f"requires actual human authorization for step {step}; approval of a sample alone is insufficient")
    if step in {2, 3}:
        entry = state["workflow"]["authorizations"][str(step)]
        if entry.get("basis") != authorization_basis(Path(state["run_dir"]), step):
            raise ValidationError("user authorization refers to a different content/target/sample version")


def require_combined_authorization(state: dict[str, Any]) -> None:
    entry = state.get("workflow", {}).get("authorizations", {}).get("2-3", {})
    if not isinstance(entry, dict) or not isinstance(entry.get("evidence"), str) or not entry["evidence"].strip():
        raise ValidationError("requires explicit human authorization for combined steps 2-3")
    if entry.get("step") != "2-3" or entry.get("covers") != ["stage2_trial", "stage2_remaining", "stage2_qa", "stage3", "stage4"]:
        raise ValidationError("combined authorization must explicitly cover trial, full deck, QA, package and delivery")
    if entry.get("basis") != authorization_basis(Path(state["run_dir"]), "2-3"):
        raise ValidationError("combined authorization is stale: content, target or selected cover changed")


def require_trial_continuation(state: dict[str, Any]) -> None:
    if "2-3" not in state.get("workflow", {}).get("authorizations", {}):
        if state.get("confirmed", {}).get("stage2_trial_first5"):
            return
        raise ValidationError("trial first5 requires actual user confirmation")
    require_combined_authorization(state)
    if (not state.get("confirmed", {}).get("stage1_plan")
            or not state["confirmed"].get("stage2_cover_style")
            or state.get("controller_acceptances", {}).get("stage2_trial_first5") is not True):
        raise ValidationError("combined steps require confirmed planning/cover and controller-accepted trial first5")
    require_combined_trial_review(state)


def require_combined_trial_review(state: dict[str, Any]) -> None:
    from .stage2_trial import stage2_trial_first5_results_complete
    from .stage2_visual_qa import require_stage2_aesthetic_review
    selection = read_json(Path(state["run_dir"]) / "_state/阶段2/trial_first5/selection.json")
    indices = selection.get("selected_slide_indices", [])
    content = read_json(Path(state["run_dir"]) / "_state/阶段1/content.json")
    covers = {s["slide_index"] for s in content["slides"] if s.get("page_type") == "cover"}
    if len(indices) != 5 or not covers.intersection(indices):
        raise ValidationError("combined steps retain a five-page trial including the cover")
    if not stage2_trial_first5_results_complete(state["run_dir"]):
        raise ValidationError("combined trial first5 is incomplete or stale")
    require_stage2_aesthetic_review(state["run_dir"], scope="trial_first5")


def authorization_basis(root: Path, step: int | str) -> dict[str, str]:
    import json
    brief = read_state(root).get("thematic_brief", {})
    basis = {"@thematic_brief": "sha256:" + hashlib.sha256(json.dumps(brief, ensure_ascii=False, sort_keys=True).encode()).hexdigest(),
             "_state/阶段1/content.json": _hash(root / "_state/阶段1/content.json")}
    if step == "2-3":
        # The controller prepares the user's chosen cover selection before recording
        # continuous authority. Missing assets never become an unbound approval.
        path = root / "_state/阶段2/cover_options/selection/selection.json"
        if not path.is_file():
            raise ValidationError("prepare the actual selected cover before authorizing combined steps 2-3")
        basis[path.relative_to(root).as_posix()] = _hash(path)
    if step == 3:
        for path in [root / "_state/阶段2/cover_options/selection/selection.json",
                     *[root / f"阶段2_图片版PPT/img/slide_{i:03d}.png" for i in range(1, 6)]]:
            if path.is_file():
                basis[path.relative_to(root).as_posix()] = _hash(path)
    return basis


def review_basis(root: Path, scope: str) -> dict[str, str]:
    paths = [root / "_state/阶段1/content.json", root / "_state/阶段1/design_contract.json",
             root / "_state/阶段1/slides.json", root / "阶段1_规划确认/每页干净逐字稿.md",
             root / "阶段1_规划确认/图片风格.md", root / "阶段1_规划确认/PPT一致性.md"]
    if scope in {"deck", "package"}:
        manifest = read_json(root / "_state/阶段2/manifests/image_deck.json")
        paths += [root / manifest["pdf_path"], *(root / p for p in manifest["images"])]
    if scope == "package":
        from .document_review import require_package_document_reviews
        require_package_document_reviews(root)
        for name in ("speaker_script", "lesson_plan"):
            manifest_path = root / f"_state/阶段3/{name}_manifest.json"
            manifest = read_json(manifest_path)
            paths += [manifest_path, root / f"_state/阶段3/{name}.json"]
            paths += [root / entry["path"] for entry in manifest["files"]]
            for entry in manifest['files']:
                artifact = root/entry['path']
                if artifact.suffix.lower() in {'.docx','.pdf'}:
                    from .file_hashing import file_sha256
                    paths.append(root/'_state/document_reviews'/(file_sha256(artifact).split(':')[-1]+'.json'))
    if any(not p.is_file() for p in paths):
        raise ValidationError("review basis is incomplete")
    basis = {p.relative_to(root).as_posix(): _hash(p) for p in paths}
    brief = read_state(root).get("thematic_brief", {})
    import json
    basis["@thematic_brief"] = "sha256:" + hashlib.sha256(json.dumps(brief, ensure_ascii=False, sort_keys=True).encode()).hexdigest()
    return basis


def record_content_review(run_dir: str | Path, scope: str, review: dict[str, Any]) -> dict[str, Any]:
    root = Path(run_dir)
    state = read_state(root)
    if scope not in REVIEW_CRITERIA:
        raise ValidationError("unknown content review scope")
    stage = {"planning": "stage1", "deck": "stage2", "package": "stage3"}[scope]
    allowed_stages = {stage, "stage2"} if scope == "planning" else {stage}
    if state["current_stage"] not in allowed_stages or state["required_actor"] != "main_controller":
        raise ValidationError("content review is not allowed at this checkpoint")
    if review.get("controller_reviewed") is not True or review.get("status") not in {"pass", "needs_rework"}:
        raise ValidationError("actual controller review with pass/needs_rework is required")
    if not isinstance(review.get("summary"), str) or not review["summary"].strip():
        raise ValidationError("review summary is required")
    content = read_json(root / "_state/阶段1/content.json")
    pages = {s["slide_index"] for s in content["slides"]}
    reviewed = review.get("reviewed_pages")
    if not isinstance(reviewed, list) or any(type(p) is not int for p in reviewed) or set(reviewed) != pages:
        raise ValidationError("review must cover every planned/actual page")
    checks = review.get("checks", {})
    if not isinstance(checks, dict) or set(checks) != set(REVIEW_CRITERIA[scope]):
        raise ValidationError(f"required review checks: {REVIEW_CRITERIA[scope]}")
    for key, check in checks.items():
        if not isinstance(check, dict) or check.get("status") not in {"pass", "fail"}:
            raise ValidationError(f"{key}: pass/fail and concrete evidence required")
        if not isinstance(check.get("evidence"), str) or not check["evidence"].strip():
            raise ValidationError(f"{key}: cite actual pages, cases, reasoning, activities or corrections")
    if not isinstance(review.get("blocking_issues"), list):
        raise ValidationError("blocking_issues must be a list")
    if review["status"] == "pass" and (review["blocking_issues"] or any(c["status"] != "pass" for c in checks.values())):
        raise ValidationError("a blocked/failed review cannot pass")
    result = {**review, "scope": scope, "basis": review_basis(root, scope), "created_at": now_iso()}
    write_json(root / f"_state/content_reviews/{scope}.json", result)
    append_event(root, "content_review_recorded", "main_controller", scope=scope, status=result["status"])
    return result


def require_content_review(run_dir: str | Path, scope: str) -> dict[str, Any]:
    root = Path(run_dir)
    path = root / f"_state/content_reviews/{scope}.json"
    if not path.is_file():
        raise ValidationError(f"missing {scope} depth/content review")
    review = read_json(path)
    if review.get("status") != "pass" or review.get("basis") != review_basis(root, scope):
        raise ValidationError(f"{scope} content review failed or stale; inspect changed content and re-review")
    return review


def plan_accepted(state: dict[str, Any]) -> bool:
    return bool(state.get("controller_acceptances", {}).get("stage1_plan"))


def deck_accepted(state: dict[str, Any]) -> bool:
    return bool(state.get("controller_acceptances", {}).get("stage2_image_deck"))


def validate_target_plan(run_dir: str | Path, slides_count: int) -> None:
    brief = read_state(run_dir).get("thematic_brief", {})
    if brief.get("scene") not in SCENES or brief.get("school_stage") not in BANDS:
        raise ValidationError("infer and record the target scene and school stage before final planning; ask only if genuinely ambiguous")
    bounds = brief.get("page_count", [20, 30])
    if brief.get("sources", {}).get("page_count", {}).get("source") == "explicit" and not bounds[0] <= slides_count <= bounds[1]:
        raise ValidationError("total pages including cover are outside the human-specified range")
