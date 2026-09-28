#!/usr/bin/env python3
"""
xray_ascii.py - High-Density Terminal Character Matrix Generator
Converts radiographic source images into dense ASCII/Binary luminance fields.

Author: Bishwajit Das (bishwajit5788)
Strictly adheres to the specification:
  - Source image luminance sampling (no vector tracing, no contours)
  - Configurable monospace font aspect-ratio compensation
  - Configurable character ramps: ascii, binary, hybrid
  - Reproducible CLI and importable Python API
  - Dual implementation: Pillow (if available) + Pure Python stdlib PNG reader
"""

from __future__ import annotations

import argparse
import html
import os
import struct
import sys
import zlib
from typing import List, Optional, Tuple

# Pre-defined character density ramps
RAMPS = {
    # Rich ASCII: space -> subtle dots -> mid tones -> high density symbols
    "ascii": " .:-=+*#%@",
    # Pure binary: dark (space/0) -> bright (1)
    "binary": " 01",
    # Hybrid: binary interspersed with punctuation density
    "hybrid": " .:01+*#%@",
}


def decode_png_stdlib(file_path: str) -> Tuple[int, int, List[List[int]]]:
    """
    Pure Python standard library PNG decoder (zero external dependencies).
    Extracts 8-bit luminance values across all pixels.
    """
    with open(file_path, "rb") as f:
        sig = f.read(8)
        if sig != b"\x89PNG\r\n\x1a\n":
            raise ValueError(f"Invalid PNG header in {file_path}")

        idat_chunks = bytearray()
        width = height = None
        color_type = None

        while True:
            chunk_len_bytes = f.read(4)
            if not chunk_len_bytes or len(chunk_len_bytes) < 4:
                break
            length = struct.unpack(">I", chunk_len_bytes)[0]
            chunk_type = f.read(4)
            chunk_data = f.read(length)
            f.read(4)  # CRC

            if chunk_type == b"IHDR":
                width, height, bit_depth, color_type, comp, filt, interlace = struct.unpack(">IIBBBBB", chunk_data)
                if bit_depth != 8 or color_type not in (0, 2, 6):
                    raise ValueError(f"Unsupported PNG bit_depth={bit_depth} or color_type={color_type}")
            elif chunk_type == b"IDAT":
                idat_chunks.extend(chunk_data)
            elif chunk_type == b"IEND":
                break

    if width is None or height is None:
        raise ValueError("Could not read IHDR chunk from PNG")

    raw = zlib.decompress(bytes(idat_chunks))
    bpp = 1 if color_type == 0 else (4 if color_type == 6 else 3)
    stride = width * bpp
    prev_row = bytearray(stride)
    offset = 0
    grid: List[List[int]] = []

    for _ in range(height):
        filter_type = raw[offset]
        offset += 1
        cur_row = bytearray(raw[offset : offset + stride])
        offset += stride

        if filter_type == 1:  # Sub
            for x in range(bpp, stride):
                cur_row[x] = (cur_row[x] + cur_row[x - bpp]) & 0xFF
        elif filter_type == 2:  # Up
            for x in range(stride):
                cur_row[x] = (cur_row[x] + prev_row[x]) & 0xFF
        elif filter_type == 3:  # Average
            for x in range(stride):
                a = cur_row[x - bpp] if x >= bpp else 0
                b = prev_row[x]
                cur_row[x] = (cur_row[x] + ((a + b) >> 1)) & 0xFF
        elif filter_type == 4:  # Paeth
            for x in range(stride):
                a = cur_row[x - bpp] if x >= bpp else 0
                b = prev_row[x]
                c = prev_row[x - bpp] if x >= bpp else 0
                p = a + b - c
                pa, pb, pc = abs(p - a), abs(p - b), abs(p - c)
                pr = a if (pa <= pb and pa <= pc) else (b if pb <= pc else c)
                cur_row[x] = (cur_row[x] + pr) & 0xFF

        prev_row = cur_row

        # Extract luminance
        row_lum: List[int] = []
        if color_type == 0:  # Grayscale
            row_lum = list(cur_row)
        else:  # RGB or RGBA
            for x in range(0, stride, bpp):
                r, g, b = cur_row[x], cur_row[x + 1], cur_row[x + 2]
                lum = int(0.299 * r + 0.587 * g + 0.114 * b)
                row_lum.append(lum)
        grid.append(row_lum)

    return width, height, grid


def load_luminance_grid(file_path: str) -> Tuple[int, int, List[List[int]]]:
    """Attempt loading via Pillow, falling back transparently to stdlib decoder."""
    try:
        from PIL import Image
        img = Image.open(file_path).convert("L")
        w, h = img.size
        pixels = list(img.getdata())
        grid = [pixels[y * w : (y + 1) * w] for y in range(h)]
        return w, h, grid
    except Exception:
        return decode_png_stdlib(file_path)


def generate_ascii_field(
    file_path: str,
    cols: int = 130,
    char_aspect: float = 0.55,
    mode: str = "ascii",
    custom_ramp: Optional[str] = None,
    gamma: float = 0.85,
    crop_active: bool = True,
) -> Tuple[int, int, List[str], List[List[int]]]:
    """
    Sample luminance across the image field and generate a dense character matrix.
    Compensates for the monospace font aspect ratio (char_width / char_height ~0.55).
    
    Returns:
      (cols, rows, lines, sampled_lums)
    """
    w, h, grid = load_luminance_grid(file_path)

    ramp = custom_ramp if custom_ramp else RAMPS.get(mode.lower(), RAMPS["ascii"])
    ramp_len = len(ramp)

    if crop_active:
        # Detect active content boundaries with balanced margins
        non_zeros = [(x, y) for y in range(h) for x in range(w) if grid[y][x] > 10]
        if non_zeros:
            min_x = min(x for x, y in non_zeros)
            max_x = max(x for x, y in non_zeros)
            min_y = min(y for x, y in non_zeros)
            max_y = max(y for x, y in non_zeros)
            pad_x = max(20, int((max_x - min_x) * 0.05))
            pad_y = max(10, int((max_y - min_y) * 0.02))
            x0 = max(0, min_x - pad_x)
            x1 = min(w, max_x + pad_x)
            y0 = max(0, min_y - pad_y)
            y1 = min(h, max_y + pad_y)
        else:
            x0, x1, y0, y1 = 0, w, 0, h
    else:
        x0, x1, y0, y1 = 0, w, 0, h

    crop_w = x1 - x0
    crop_h = y1 - y0

    # dx is horizontal step in source image
    dx = crop_w / cols
    # dy is vertical step, adjusted for non-square monospace aspect ratio
    dy = dx / char_aspect
    rows = max(10, int(crop_h / dy))

    lines: List[str] = []
    matrix_lums: List[List[int]] = []

    for r in range(rows):
        line_chars: List[str] = []
        line_lums: List[int] = []
        sy0 = int(y0 + r * dy)
        sy1 = min(h, int(y0 + (r + 1) * dy))
        if sy1 <= sy0:
            sy1 = min(h, sy0 + 1)

        for c in range(cols):
            sx0 = int(x0 + c * dx)
            sx1 = min(w, int(x0 + (c + 1) * dx))
            if sx1 <= sx0:
                sx1 = min(w, sx0 + 1)

            lum_sum = 0
            cnt = 0
            for py in range(sy0, sy1):
                row_ref = grid[py]
                for px in range(sx0, sx1):
                    lum_sum += row_ref[px]
                    cnt += 1

            avg_lum = lum_sum / max(1, cnt)
            line_lums.append(int(avg_lum))

            # Gamma / contrast curve
            norm = (avg_lum / 255.0) ** gamma
            idx = int(norm * ramp_len)
            idx = min(ramp_len - 1, max(0, idx))
            line_chars.append(ramp[idx])

        lines.append("".join(line_chars))
        matrix_lums.append(line_lums)

    return cols, rows, lines, matrix_lums


def format_svg_tspans(
    lines: List[str],
    matrix_lums: List[List[int]],
    start_x: float = 46.0,
    start_y: float = 142.0,
    line_spacing: float = 5.2,
    accent_color: str = "#700004",
    accent_threshold: int = 190,
) -> str:
    """
    Format ASCII matrix into compact SVG <tspan> rows.
    Selectively styles high-luminance accent clusters with accent_color (#700004).
    The main character structure remains in the default parent <text> color.
    """
    tspans: List[str] = []
    for r_idx, (line, lums) in enumerate(zip(lines, matrix_lums)):
        y_pos = start_y + r_idx * line_spacing
        escaped_line = html.escape(line)

        # Check if there are accent clusters in this line
        has_accents = any(v >= accent_threshold for v in lums)
        if not has_accents:
            tspans.append(f'<tspan x="{start_x:.1f}" y="{y_pos:.1f}">{escaped_line}</tspan>')
        else:
            # Segment into primary text and accent spans for selective clustering
            segments: List[str] = []
            cur_segment: List[str] = []
            is_accent = False

            for ch, lum in zip(line, lums):
                char_is_accent = (lum >= accent_threshold and ch not in " .")
                if char_is_accent != is_accent:
                    if cur_segment:
                        seg_text = html.escape("".join(cur_segment))
                        if is_accent:
                            segments.append(f'<tspan fill="{accent_color}">{seg_text}</tspan>')
                        else:
                            segments.append(seg_text)
                        cur_segment = []
                    is_accent = char_is_accent
                cur_segment.append(ch)

            if cur_segment:
                seg_text = html.escape("".join(cur_segment))
                if is_accent:
                    segments.append(f'<tspan fill="{accent_color}">{seg_text}</tspan>')
                else:
                    segments.append(seg_text)

            tspans.append(f'<tspan x="{start_x:.1f}" y="{y_pos:.1f}">{"".join(segments)}</tspan>')

    return "\n        ".join(tspans)


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate ASCII/Binary matrix from image")
    parser.add_argument("--source", default="assets/xray-profile-reference.png", help="Source image path")
    parser.add_argument("--cols", type=int, default=130, help="Number of character columns (120-180)")
    parser.add_argument("--aspect", type=float, default=0.55, help="Monospace char aspect ratio")
    parser.add_argument("--mode", choices=["ascii", "binary", "hybrid"], default="ascii", help="Character ramp mode")
    parser.add_argument("--ramp", default=None, help="Custom character ramp string")
    parser.add_argument("--gamma", type=float, default=0.85, help="Luminance contrast curve exponent")
    parser.add_argument("--output", default="assets/xray-ascii.txt", help="Output text file path")
    args = parser.parse_args()

    if not os.path.exists(args.source):
        print(f"[ERROR] Source file not found: {args.source}", file=sys.stderr)
        sys.exit(1)

    cols, rows, lines, _ = generate_ascii_field(
        file_path=args.source,
        cols=args.cols,
        char_aspect=args.aspect,
        mode=args.mode,
        custom_ramp=args.ramp,
        gamma=args.gamma,
    )

    print(f"[OK] Generated {cols} cols x {rows} rows character matrix in '{args.mode}' mode.")

    out_dir = os.path.dirname(args.output)
    if out_dir and not os.path.exists(out_dir):
        os.makedirs(out_dir, exist_ok=True)

    with open(args.output, "w", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")

    print(f"[OK] Saved to {args.output}")


if __name__ == "__main__":
    main()
