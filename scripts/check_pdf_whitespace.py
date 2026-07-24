#!/usr/bin/env python3
"""Measure page whitespace proxy for rendered PDF PNGs.

The measurement compares pixels to the page background. It is a gate, not a
substitute for editorial review: large empty cards or overlays must still be
rejected by Red Team.
"""
from __future__ import annotations

import struct
import sys
import zlib
from pathlib import Path


def read_png(path: Path) -> tuple[int, int, list[list[int]], int]:
    data = path.read_bytes()
    pos = 8
    image = bytearray()
    width = height = channels = 0
    while pos < len(data):
        size = struct.unpack(">I", data[pos : pos + 4])[0]
        kind = data[pos + 4 : pos + 8]
        chunk = data[pos + 8 : pos + 8 + size]
        pos += 12 + size
        if kind == b"IHDR":
            width, height, depth, color_type = struct.unpack(">IIBB", chunk[:10])
            if depth != 8 or color_type not in (2, 6):
                raise ValueError(f"unsupported PNG format: {path}")
            channels = 3 if color_type == 2 else 4
        elif kind == b"IDAT":
            image.extend(chunk)
    raw = zlib.decompress(image)
    stride = width * channels
    rows: list[list[int]] = []
    previous = [0] * stride
    offset = 0
    for _ in range(height):
        filter_type = raw[offset]
        offset += 1
        current = list(raw[offset : offset + stride])
        offset += stride
        for i in range(stride):
            left = current[i - channels] if i >= channels else 0
            up = previous[i]
            upper_left = previous[i - channels] if i >= channels else 0
            if filter_type == 1:
                current[i] = (current[i] + left) & 255
            elif filter_type == 2:
                current[i] = (current[i] + up) & 255
            elif filter_type == 3:
                current[i] = (current[i] + ((left + up) // 2)) & 255
            elif filter_type == 4:
                estimate = left + up - upper_left
                distances = (abs(estimate - left), abs(estimate - up), abs(estimate - upper_left))
                predictor = (left, up, upper_left)[distances.index(min(distances))]
                current[i] = (current[i] + predictor) & 255
        rows.append(current)
        previous = current
    return width, height, rows, channels


def whitespace(path: Path, fuzz: int = 2) -> float:
    width, height, rows, channels = read_png(path)
    # The report uses two explicit page backgrounds. Treat panel fills as
    # occupied layout; only pixels matching the page background are whitespace.
    candidates = ([244, 241, 233], [17, 27, 46])
    corner = rows[0][:channels]
    background = min(candidates, key=lambda c: sum(abs(c[i] - corner[i]) for i in range(3)))
    non_background = 0
    for row in rows:
        for offset in range(0, len(row), channels):
            if max(abs(row[offset + channel] - background[channel]) for channel in range(3)) > fuzz:
                non_background += 1
    return 1 - non_background / (width * height)


def main() -> int:
    if len(sys.argv) != 2:
        print("usage: check_pdf_whitespace.py <rendered-png-dir>", file=sys.stderr)
        return 2
    pages = sorted(Path(sys.argv[1]).glob("page-*.png"))
    if not pages:
        print("no page PNGs found", file=sys.stderr)
        return 2
    failed = False
    for page in pages:
        value = whitespace(page) * 100
        status = "PASS" if value <= 10 else "BLOCK"
        print(f"{page.name}\t{value:.1f}%\t{status}")
        failed |= value > 10
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
