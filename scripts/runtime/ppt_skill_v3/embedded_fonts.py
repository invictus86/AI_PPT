"""Decode embedded EOT to original glyph data, with bounded, local execution."""
from __future__ import annotations

import io
import hashlib
from functools import lru_cache
import os
from pathlib import Path
import shutil
import struct
import subprocess
import tempfile
import json

from .validation import ValidationError


class FontReadError(ValidationError):
    def __init__(self, code, message):
        self.code = code
        super().__init__(code + ': ' + message)


def node_runtime():
    portable = Path(__file__).resolve().parents[3] / '_local' / 'node' / 'node.exe'
    configured = os.environ.get('PPT_SKILL_NODE')
    if configured:
        return str(Path(configured)) if Path(configured).is_file() else None
    return str(portable) if portable.is_file() else shutil.which('node')


def decoder_files():
    root = Path(__file__).parent
    return [root/'embedded_fonts.py', root/'source_font_inspection.py', root/'decode_eot.mjs',
            root/'vendor/mtx-decompressor/index.mjs']


@lru_cache(maxsize=48)
def decode_font(raw):
    """Return validated SFNT plus diagnosis; no installation or source mutation."""
    from fontTools.ttLib import TTFont
    if len(raw) < 40:
        raise FontReadError('font_corrupt', '嵌入字体数据截断')
    size = struct.unpack_from('<I', raw, 4)[0]
    if not 0 < size <= len(raw) - 40:
        raise FontReadError('font_corrupt', 'EOT字体数据长度无效')
    data = raw[-size:]
    import fontTools
    info = {'format': 'uncompressed_eot', 'tool': 'fontTools', 'version': fontTools.__version__}
    if data[:4] not in (b'\x00\x01\x00\x00', b'OTTO', b'ttcf'):
        flags = struct.unpack_from('<I', raw, 12)[0]
        if flags & 0x10000000:
            raise FontReadError('xor_obfuscated_font_unsupported', 'EOT含XOR混淆，当前不自动处理；不是文档密码')
        if not flags & 4:
            raise FontReadError('font_corrupt_or_unsupported', '非SFNT数据且未声明MTX压缩')
        node = node_runtime()
        if not node:
            raise FontReadError('mtx_decoder_unavailable', '已识别MTX压缩字体；缺少Node.js运行时')
        with tempfile.TemporaryDirectory(prefix='ppt_eot_') as tmp:
            src = Path(tmp)/'font.eot'; dst = Path(tmp)/'font.ttf'
            src.write_bytes(raw)
            try:
                result = subprocess.run([node, '--max-old-space-size=1024', str(Path(__file__).with_name('decode_eot.mjs')), str(src), str(dst)],
                    capture_output=True, text=True, encoding='utf-8', timeout=90,
                    creationflags=getattr(subprocess, 'CREATE_NO_WINDOW', 0))
            except (OSError, subprocess.TimeoutExpired) as exc:
                raise FontReadError('mtx_decode_failed', str(exc)) from exc
            if result.returncode:
                raise FontReadError('mtx_decode_failed', result.stderr[-1600:])
            info = {'format': 'mtx_eot', **json.loads(result.stdout)}
            data = dst.read_bytes()
    if data[:4] == b'ttcf':
        raise FontReadError('font_collection_unsupported', '嵌入字体集合尚未支持')
    try:
        with TTFont(io.BytesIO(data), recalcBBoxes=False, recalcTimestamp=False) as font:
            flags = font['OS/2'].fsType
            if flags & (2 | 256 | 512):
                raise FontReadError('embedding_restricted', '嵌入许可不允许当前临时渲染方式')
            required = ['cmap', 'head', 'hhea', 'hmtx', 'maxp', 'name', 'OS/2']
            required += ['glyf', 'loca'] if 'glyf' in font else ['CFF '] if 'CFF ' in font else ['CFF2']
            for tag in required:
                _ = font[tag]
            cmap = font.getBestCmap()
            if not cmap:
                raise FontReadError('font_corrupt', '字符映射为空，无法核对内容')
            info.update(fsType=flags, cmap_glyphs=len(cmap), glyphs=font['maxp'].numGlyphs)
    except FontReadError:
        raise
    except Exception as exc:
        raise FontReadError('font_corrupt', str(exc)) from exc
    info.update(source_font_sha256=hashlib.sha256(raw).hexdigest(),
                decoded_font_sha256=hashlib.sha256(data).hexdigest())
    return data, info
