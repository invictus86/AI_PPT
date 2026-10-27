"""Host-native generation, either explicitly selected or a verified relay fallback."""
from __future__ import annotations

from pathlib import Path

from .image_routes import IMAGE_ROUTE_CODEX_IMAGE_GEN, image_size_contract
from .json_io import read_json
from .validation import ValidationError


def validate_native_request(run_dir, packet):
    if "native_fallback" in packet:
        from .image_fallback import validate_native_fallback
        return validate_native_fallback(run_dir, packet)
    selection = packet.get("image_generation_selection", {})
    if (selection.get("mode") != "native" or selection.get("image_generation_route") != IMAGE_ROUTE_CODEX_IMAGE_GEN
            or packet.get("image_generation_route") != IMAGE_ROUTE_CODEX_IMAGE_GEN):
        raise ValidationError("直接内置生图须通过内置模式派发；自动备用仍须核实原中转请求")
    native = packet.get("image_gen_input", {})
    if native.get("tool") != "image_gen.imagegen" or native.get("mode") not in {"generate", "edit"} or "image_api_input" in packet:
        raise ValidationError("内置模式只允许当前聊天的内置生图工具，不尝试中转")
    if native.get("quality") != "high" or native.get("output_format") != "png":
        raise ValidationError("内置生图必须保留 high 与无损PNG要求")
    from .canonical_images import parse_size
    size = native.get("size")
    if not isinstance(size, str) or size != packet.get("target_size"):
        raise ValidationError("内置生图必须保持已批准的目标尺寸")
    width, height = parse_size(size)
    contract = image_size_contract()
    if width < contract["target_width_px"] or height < contract["target_height_px"]:
        raise ValidationError("内置生图不能降低默认目标尺寸")
    from .image_geometry import review_image_aspect_ratio
    if not review_image_aspect_ratio(width, height)["meets_target_aspect_ratio"]:
        raise ValidationError("内置生图目标须保持16:9比例容差")


def native_tool_request(run_dir, packet):
    validate_native_request(run_dir, packet)
    if "native_fallback" in packet:
        from .image_fallback import native_tool_request as fallback_request
        return fallback_request(run_dir, packet)
    root = Path(run_dir).resolve()
    native = packet["image_gen_input"]
    refs = native.get("referenced_image_paths", [])
    args = {"prompt": packet["prompt"], "transparent_background": False}
    if refs:
        args["referenced_image_paths"] = [str((root / path).resolve()) for path in refs]
    return {"status": "awaiting_native_image_generation", "tool_name": "image_gen.imagegen", "tool_arguments": args,
            "requested_parameters": {"size": native["size"], "quality": "high", "output_format": "png"},
            "unexposed_tool_parameters": ["model", "size", "quality", "output_format"],
            "reference_review_required": bool(refs),
            "parameter_note": "由当前聊天的助手实际调用内置工具；尺寸、high、PNG是要求，未冒记为工具已设置参数，不先尝试中转。"}


def require_no_pending_native_request(run_dir, packet):
    """Switching back to auto cannot resubmit a still-pending native image."""
    root = Path(run_dir).resolve()
    for path in (root / "_state/阶段2/prompt_history/requests").glob("*.json"):
        entry = read_json(path)
        if entry.get("status") != "生成中":
            continue
        old_path = root / entry["frozen_request_path"]
        old = read_json(old_path)
        if old.get("image_generation_route") != IMAGE_ROUTE_CODEX_IMAGE_GEN:
            continue
        if all(old.get(k) == packet.get(k) for k in ("purpose", "slide_index", "option_id")):
            raise ValidationError("同页内置生图已提交或结果未知；先恢复原工具结果，切换模式不重复生成")


def require_safe_native_submission(run_dir, packet):
    """No channel switch may bypass an in-flight relay image or a safety refusal."""
    root = Path(run_dir).resolve()
    require_no_pending_native_request(root, packet)
    for path in (root / "_state/阶段2/request_results").glob("*.json"):
        receipt = read_json(path)
        if not receipt.get("packet_path"):
            continue
        old = read_json(root / receipt["packet_path"])
        if any(old.get(k) != packet.get(k) for k in ("purpose", "slide_index", "option_id")):
            continue
        if receipt.get("failure_category") == "content_policy" and old.get("prompt") == packet.get("prompt"):
            raise ValidationError("内容安全拒绝不能通过切换模式规避")
        if receipt.get("status") in {"queued", "submitted", "unknown", "returned_unusable"}:
            raise ValidationError("同页中转请求仍在途或结果未知；先恢复或核实原请求，切换模式不重复生成")
        if receipt.get("status") == "completed":
            entry_path = root / "_state/阶段2/prompt_history/requests" / (str(old.get("generation_request_id")) + ".json")
            if not entry_path.is_file() or not read_json(entry_path).get("results"):
                raise ValidationError("同页中转已有待登记结果；先恢复原结果，切换模式不重复生成")
