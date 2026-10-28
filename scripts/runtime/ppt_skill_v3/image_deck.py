from __future__ import annotations

import hashlib
from pathlib import Path
from typing import Any

from PIL import Image
from reportlab.lib.utils import ImageReader
from reportlab.pdfgen.canvas import Canvas

from .deliverable_naming import project_deliverable_relpaths
from .dev_mode import require_dev_fixture_enabled
from .image_prompt_docs import refresh_prompt_delivery
from .image_style import result_is_current
from .events import append_event
from .image_routes import DEFAULT_PPT_IMAGE_HEIGHT_PX, DEFAULT_PPT_IMAGE_WIDTH_PX
from .json_io import read_json, write_json
from .planning_assets import content_path, deck_style_path, layout_intent_path, slide_prompt_briefs_path
from .stage1_plan import load_stage1_slides
from .stage_docs import sync_stage_docs
from .state import read_state, write_state
from .time_utils import now_iso
from .validation import ValidationError, validate_image_result, validate_stage1_plan


PDF_CANVAS_SIZE = (DEFAULT_PPT_IMAGE_WIDTH_PX, DEFAULT_PPT_IMAGE_HEIGHT_PX)
PDF_RESOLUTION_DPI = 120


def build_image_deck(run_dir: str | Path, *, allow_dev_fixture: bool = False) -> Path:
    if allow_dev_fixture:
        require_dev_fixture_enabled()

    root = Path(run_dir)
    state = read_state(root)
    from .thematic_workflow import require_step
    require_step(state, 3)
    if state["current_stage"] != "stage2":
        raise ValidationError("image deck can only be built in stage2")
    if not state["confirmed"].get("stage2_cover_style"):
        raise ValidationError("image deck requires approved cover style")

    plan = validate_stage1_plan(load_stage1_slides(root))
    results = [_load_stage2_result(root, slide["slide_index"], allow_dev_fixture) for slide in plan["slides"]]

    page_entries = [_pdf_page_from_image(root / result["image_path"]) for result in results]
    pages = [entry["page"] for entry in page_entries]
    if not pages:
        raise ValidationError("image deck requires at least one stage2 image")

    relpaths = project_deliverable_relpaths(root, state=state)
    deck_rel = relpaths["stage2_image_deck"]
    deck_path = root / deck_rel
    deck_path.parent.mkdir(parents=True, exist_ok=True)
    try:
        _write_image_pages_pdf(deck_path, page_entries)
    finally:
        for page in pages:
            page.close()

    manifest = {
        "schema_version": "2.0",
        "project_name": state["project_name"],
        "run_dir": state["run_dir"],
        "artifact_type": "stage2_image_pdf",
        "output_format": "pdf",
        "deck_path": deck_rel,
        "pdf_path": deck_rel,
        "slides_count": len(results),
        "page_size": {"width_px": PDF_CANVAS_SIZE[0], "height_px": PDF_CANVAS_SIZE[1], "resolution_dpi": PDF_RESOLUTION_DPI},
        "images": [result["image_path"] for result in results],
        "result_paths": [result.get("result_path") for result in results],
        "pdf_sha256": f"sha256:{hashlib.sha256(deck_path.read_bytes()).hexdigest()}",
        "image_page_transforms": [_manifest_entry_without_page(entry) for entry in page_entries],
        "assets": {
            "content": str(content_path(root).relative_to(root)),
            "slide_prompt_briefs": str(slide_prompt_briefs_path(root).relative_to(root)),
            "deck_style": str(deck_style_path(root).relative_to(root)),
            "layout_intent": str(layout_intent_path(root).relative_to(root)),
            "final_prompts_dir": "_state/阶段2/final_prompts",
        },
        "dev_fixture_used": any(result["fixture"] for result in results),
        "created_at": now_iso(),
    }
    write_json(root / "_state" / "阶段2" / "manifests" / "image_deck.json", manifest)

    state["status"] = "full_deck_pending_controller_qa"
    state["required_actor"] = "main_controller"
    state.setdefault("user_artifacts", {})["stage2_image_deck"] = deck_rel
    state.setdefault("expected_user_paths", {})["stage2_image_deck"] = deck_rel
    state["quality"]["stage2"] = "pending_controller_review"
    state["next_required_action"] = "主控实际审阅整套PDF的内容与视觉，验收锁定后连续制作配套和整理交付"
    write_state(root, state)
    sync_stage_docs(root)
    append_event(root, "image_deck_built", "runtime", slides_count=len(results), allow_dev_fixture=allow_dev_fixture)
    refresh_prompt_delivery(root)
    return deck_path


def _pdf_page_from_image(image_path: Path) -> dict[str, Any]:
    with Image.open(image_path) as original:
        source = original.copy()
        source_width, source_height = source.size
        factor = min(1.0, PDF_CANVAS_SIZE[0] / source_width, PDF_CANVAS_SIZE[1] / source_height)
        placed_width = round(source_width * factor)
        placed_height = round(source_height * factor)
        return {
            "page": source,
            "source": str(image_path),
            "source_width_px": source_width,
            "source_height_px": source_height,
            "canvas_width_px": PDF_CANVAS_SIZE[0],
            "canvas_height_px": PDF_CANVAS_SIZE[1],
            "placed_width_px": placed_width,
            "placed_height_px": placed_height,
            "embedded_width_px": source_width,
            "embedded_height_px": source_height,
            "resize_mode": "pdf_placement_only" if factor < 1 else "none",
            "raster_resampled": False,
            "warnings": [],
        }


def _write_image_pages_pdf(path: Path, entries: list[dict[str, Any]]) -> None:
    """Keep the existing page geometry while embedding every original pixel losslessly."""
    points_per_canvas_pixel = 72 / PDF_RESOLUTION_DPI
    canvas_width, canvas_height = PDF_CANVAS_SIZE
    pdf = Canvas(str(path), pagesize=(canvas_width * points_per_canvas_pixel,
                                     canvas_height * points_per_canvas_pixel), pageCompression=1)
    for entry in entries:
        width, height = entry['placed_width_px'], entry['placed_height_px']
        left = (canvas_width - width) // 2
        top = (canvas_height - height) // 2
        pdf.setFillColorRGB(1, 1, 1)
        pdf.rect(0, 0, canvas_width * points_per_canvas_pixel,
                 canvas_height * points_per_canvas_pixel, fill=1, stroke=0)
        pdf.drawImage(ImageReader(entry['page']), left * points_per_canvas_pixel,
                      (canvas_height - top - height) * points_per_canvas_pixel,
                      width=width * points_per_canvas_pixel, height=height * points_per_canvas_pixel,
                      mask='auto')
        pdf.showPage()
    pdf.save()


def _manifest_entry_without_page(entry: dict[str, Any]) -> dict[str, Any]:
    return {key: value for key, value in entry.items() if key != "page"}


def _load_stage2_result(root: Path, slide_index: int, allow_dev_fixture: bool) -> dict[str, Any]:
    result_path = root / "_state" / "阶段2" / "results" / f"slide_{slide_index:03d}.json"
    if not result_path.exists():
        raise ValidationError(f"missing stage2 image result for slide {slide_index}")
    result = validate_image_result(read_json(result_path), production=not allow_dev_fixture)
    if not result_is_current(root, result):
        raise ValidationError(f"第{slide_index}页图片或当前风格依据不匹配；旧记录需主控核对接纳")
    image_path = root / result["image_path"]
    if not image_path.exists():
        raise FileNotFoundError(f"registered image does not exist: {image_path}")
    if result["stage"] != "stage2":
        raise ValidationError("image deck can only use stage2 image results")
    if result.get("purpose") != "full_slide":
        raise ValidationError("image deck can only use full_slide image results")
    return result
