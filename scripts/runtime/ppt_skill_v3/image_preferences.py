"""Image-only preferences, read afresh for each new dispatch; never rewrite batches."""
from __future__ import annotations

from pathlib import Path

from .image_routes import IMAGE_ROUTE_CODEX_IMAGE_GEN, IMAGE_ROUTE_OPENAI_IMAGE_API, normalize_image_generation_route
from .json_io import read_json, write_json
from .time_utils import now_iso
from .validation import ValidationError
from .workspace_paths import resolve_skill_root

MODES = {"native": "内置生图", "auto": "自动备用"}
DEFAULT_MODE = "auto"
PROJECT_CONFIG = Path("_state/image_generation.json")


def local_config_path() -> Path:
    return resolve_skill_root() / "_local/config/image_generation.json"


def _read_mode(path: Path) -> str | None:
    if not path.exists():
        return None
    try:
        value = read_json(path)
    except (OSError, ValueError) as exc:
        raise ValidationError(f"无法读取生图设置：{path}；请修复设置后再派发，不自动改走中转") from exc
    if (not isinstance(value, dict) or value.get("schema_version") != "1.0"
            or not isinstance(value.get("mode"), str) or value["mode"] not in MODES):
        raise ValidationError(f"生图设置无效：{path}；只支持 native（内置生图）或 auto（自动备用）")
    return value["mode"]


def resolve_image_generation(run_dir: str | Path | None = None, *, route: str | None = None) -> dict:
    """Explicit command > project > this computer/workspace > legacy auto default."""
    if route is not None:
        resolved_route = normalize_image_generation_route(route)
        mode = "native" if resolved_route == IMAGE_ROUTE_CODEX_IMAGE_GEN else "auto"
        source = "explicit_route"
    else:
        project_mode = _read_mode(Path(run_dir) / PROJECT_CONFIG) if run_dir is not None else None
        if project_mode is not None:
            mode, source = project_mode, "project"
        else:
            mode = _read_mode(local_config_path())
            mode, source = (mode, "local") if mode is not None else (DEFAULT_MODE, "default")
        resolved_route = IMAGE_ROUTE_CODEX_IMAGE_GEN if mode == "native" else IMAGE_ROUTE_OPENAI_IMAGE_API
    return {"mode": mode, "label": MODES[mode], "source": source,
            "image_generation_route": resolved_route,
            "relay_attempted_first": mode == "auto",
            "native_fallback_allowed": mode == "auto",
            "native_tool": "image_gen.imagegen"}


def image_generation_status(run_dir: str | Path | None = None) -> dict:
    return {"status": "image_generation_settings", **resolve_image_generation(run_dir),
            "local_config_path": str(local_config_path()),
            "project_config_path": str(Path(run_dir) / PROJECT_CONFIG) if run_dir is not None else None,
            "applies_to": "后续新派发生图批次；已派发请求沿用冻结路线，合格图片继续复用",
            "native_execution": "由当前聊天的助手实际调用内置生图工具；脚本不直接调用，工具未开放时报告受影响图片，不尝试中转"}


def configure_image_generation(mode: str | None = None, *, run_dir: str | Path | None = None, inherit: bool = False) -> dict:
    if inherit:
        if run_dir is None or mode is not None:
            raise ValidationError("--inherit 仅用于当前项目恢复跟随本机默认，不能同时指定模式")
    elif not isinstance(mode, str) or mode not in MODES:
        raise ValidationError("只支持 native（内置生图）或 auto（自动备用）")
    if run_dir is not None:
        from .state import read_state
        from .resources import project_lock
        read_state(run_dir)  # Do not silently create a project for a misspelled path.
        with project_lock(run_dir):
            target = Path(run_dir) / PROJECT_CONFIG
            if inherit:
                target.unlink(missing_ok=True)
            else:
                write_json(target, {"schema_version": "1.0", "mode": mode, "updated_at": now_iso()})
    else:
        target = local_config_path()
        write_json(target, {"schema_version": "1.0", "mode": mode, "updated_at": now_iso()})
    return {**image_generation_status(run_dir), "status": "image_generation_configured",
            "configured_scope": "project" if run_dir is not None else "local"}


def image_generation_menu() -> int:
    while True:
        try:
            current = image_generation_status()
            print(f"\n当前默认生图模式：{current['label']}")
        except ValidationError:
            print("\n当前本机生图设置损坏。请选择模式重新保存；退出会保留原设置，不自动改走中转。")
        print("1. 内置生图：直接调用当前聊天的内置生图工具，不尝试中转")
        print("2. 自动备用：中转优先，故障且无可恢复结果时接续内置生图")
        print("0. 退出")
        try:
            choice = input("请选择：").strip()
        except (EOFError, KeyboardInterrupt):
            print("\n已退出，未修改设置。")
            return 0
        if choice == "0":
            return 0
        if choice not in {"1", "2"}:
            print("请输入 1、2 或 0。")
            continue
        result = configure_image_generation("native" if choice == "1" else "auto")
        print(f"已切换为：{result['label']}。后续新批次生效，无需重启或修改 Skill。")
        print("项目单独设置优先；已派发请求继续沿用原路线。")
        return 0
