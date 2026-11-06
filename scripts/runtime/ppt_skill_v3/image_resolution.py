"""Local resolution presets for new image requests; frozen packets stay unchanged."""
from __future__ import annotations

from pathlib import Path

from .json_io import read_json, write_json
from .time_utils import now_iso
from .validation import ValidationError
from .workspace_paths import resolve_skill_root

RESOLUTIONS = {"1k": "1672x941", "2k": "2560x1440", "4k": "3840x2160"}
DEFAULT_RESOLUTION = "1k"


def local_config_path() -> Path:
    return resolve_skill_root() / "_local/config/image_resolution.json"


def resolve_image_resolution() -> dict:
    path = local_config_path()
    resolution, source = DEFAULT_RESOLUTION, "default"
    if path.exists():
        try:
            data = read_json(path)
        except (OSError, ValueError) as exc:
            raise ValidationError("无法读取分辨率设置；请使用分辨率切换脚本重新保存") from exc
        if (not isinstance(data, dict) or data.get("schema_version") != "1.0"
                or not isinstance(data.get("resolution"), str) or data["resolution"] not in RESOLUTIONS):
            raise ValidationError("分辨率设置无效；只支持 1k、2k、4k，不自动降低分辨率")
        resolution, source = data["resolution"], "local"
    return {"resolution": resolution, "label": resolution.upper(),
            "size": RESOLUTIONS[resolution], "source": source, "target_aspect_ratio": "16:9"}


def image_resolution_status() -> dict:
    return {"status": "image_resolution_settings", **resolve_image_resolution(),
            "presets": dict(RESOLUTIONS), "local_config_path": str(local_config_path()),
            "applies_to": "后续新派发生图批次；已派发请求沿用冻结尺寸，已有图片不变",
            "aspect_ratio_note": "1K保留原1672x941及现有16:9容差；2K、4K为精确16:9"}


def configure_image_resolution(resolution: str) -> dict:
    if not isinstance(resolution, str) or resolution not in RESOLUTIONS:
        raise ValidationError("只支持 1k（1672x941）、2k（2560x1440）、4k（3840x2160）")
    write_json(local_config_path(), {"schema_version": "1.0", "resolution": resolution, "updated_at": now_iso()})
    return {**image_resolution_status(), "status": "image_resolution_configured"}


def image_resolution_menu() -> int:
    while True:
        try:
            current = resolve_image_resolution()
            print(f"\n当前默认生图分辨率：{current['label']}（{current['size']}）")
        except ValidationError:
            print("\n当前分辨率设置损坏。请选择一档重新保存；退出保留原设置。")
        print("1. 1K：1672x941（保持现有尺寸及16:9容差）")
        print("2. 2K：2560x1440（精确16:9）")
        print("3. 4K：3840x2160（精确16:9）")
        print("0. 退出")
        try:
            choice = input("请选择：").strip()
        except (EOFError, KeyboardInterrupt):
            print("\n已退出，未修改设置。")
            return 0
        if choice == "0":
            return 0
        if choice not in {"1", "2", "3"}:
            print("请输入 1、2、3 或 0。")
            continue
        result = configure_image_resolution({"1": "1k", "2": "2k", "3": "4k"}[choice])
        print(f"已切换为：{result['label']}（{result['size']}）。后续新批次生效，无需重启。")
        print("模型、质量、格式、并发、超时和生图渠道均不变；已派发请求继续沿用原尺寸。")
        return 0
