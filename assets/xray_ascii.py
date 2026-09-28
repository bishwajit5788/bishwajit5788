#!/usr/bin/env python3
"""
xray_ascii.py - Color-Aware Terminal Character Matrix Generator
Converts source images into dense, multi-layered color ASCII/Binary fields.

Author: Bishwajit Das (bishwajit5788)
Strictly adheres to the specification:
  - Source PNG color quantization and mapping:
      SOURCE BLACK -> #FFEB93 (Lemon Meringue)
      SOURCE RED   -> #868B32 (Olive Grove)
      SOURCE WHITE -> #FFFFFF (White)
  - Color-aware classification with tolerance for anti-aliasing
  - Monospace font aspect-ratio compensation
  - Preserves visual separation between artwork and background
  - Large sizing filling 80-90% usable width and 70-85% usable height of left panel
  - Compact SVG text generation using grouped <tspan> runs
"""

from __future__ import annotations

import argparse
import html
import os
import struct
import sys
import zlib
from typing import Dict, List, Optional, Tuple

# Exact mapped color definitions
COLOR_MAP = {
    "black": "#FFEB93",  # Lemon Meringue
    "red": "#868B32",    # Olive Grove
    "white": "#FFFFFF",  # Pure White Highlight
}

# Light mode color mappings ensuring contrast
COLOR_MAP_LIGHT = {
    "black": "#1A2517",  # Dark Olive (high contrast against light background)
    "red": "#868B32",    # Olive Grove
    "white": "#700004",  # Dark Garnet accent highlight for light mode
}


def decode_png_rgb(file_path: str) -> Tuple[int, int, List[List[Tuple[int, int, int]]]]:
    """
    Pure Python standard library PNG RGB decoder (zero external dependencies).
    Extracts 24-bit RGB values across all pixels.
    """
    try:
        from PIL import Image
        img = Image.open(file_path).convert("RGB")
        w, h = img.size
        pixels_flat = list(img.getdata())
        grid = [pixels_flat[y * w : (y + 1) * w] for y in range(h)]
        return w, h, grid
    except Exception:
        pass

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
                width, height, bit_depth, color_type, _, _, _ = struct.unpack(">IIBBBBB", chunk_data)
                if bit_depth != 8 or color_type not in (0, 2, 6):
                    raise ValueError(f"Unsupported PNG bit_depth={bit_depth}, color_type={color_type}")
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
    grid: List[List[Tuple[int, int, int]]] = []

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

        row_pixels: List[Tuple[int, int, int]] = []
        if color_type == 0:
            for x in range(width):
                v = cur_row[x]
                row_pixels.append((v, v, v))
        else:
            for x in range(0, stride, bpp):
                row_pixels.append((cur_row[x], cur_row[x + 1], cur_row[x + 2]))
        grid.append(row_pixels)

    return width, height, grid


def generate_color_aware_ascii(
    file_path: str = "assets/xray-profile-reference.png",
    cols: int = 84,
    char_aspect: float = 0.58,
    mode: str = "ascii",
) -> Tuple[int, int, List[List[Tuple[str, str]]]]:
    """
    Generate color-aware ASCII matrix preserving black, red, and white source layers.
    Returns:
      (cols, rows, matrix) where each row is a list of (character, color_tag) tuples.
      color_tag is one of: 'space', 'black', 'red', 'white'.
    """
    w, h, grid = decode_png_rgb(file_path)

    # Detect the horizontal active silhouette bounds for each row y
    row_env: Dict[int, Tuple[int, int]] = {}
    for y in range(h):
        xs = [x for x in range(w) if grid[y][x][0] > 18 or grid[y][x][1] > 18 or grid[y][x][2] > 18]
        if xs:
            row_env[y] = (min(xs) - 4, max(xs) + 4)

    # Active emblem crop area
    all_active_x = [x for env in row_env.values() for x in env]
    all_active_y = list(row_env.keys())
    if all_active_x and all_active_y:
        x0 = max(0, min(all_active_x) - 4)
        x1 = min(w, max(all_active_x) + 4)
        y0 = max(0, min(all_active_y) - 2)
        y1 = min(h, max(all_active_y) + 2)
    else:
        x0, x1, y0, y1 = 0, w, 0, h

    cw = x1 - x0
    ch = y1 - y0

    # Step sizes with monospace aspect compensation
    dx = cw / cols
    dy = dx / char_aspect
    rows = max(10, int(ch / dy))

    # Character sets
    if mode == "binary":
        ramp_white = ["1", "1", "@"]
        ramp_red = ["1", "0", "1", "+"]
        ramp_black = ["0", "1", "0", "#"]
    elif mode == "hybrid":
        ramp_white = ["@", "#", "1"]
        ramp_red = ["+", "*", "1", "0", "="]
        ramp_black = ["#", "0", "%", "@"]
    else:  # rich ascii (preferred)
        ramp_white = ["@", "#", "%", "*"]
        ramp_red = ["-", "+", "=", "*", "#", "%"]
        ramp_black = ["#", "%", "@", "*", "+"]

    matrix: List[List[Tuple[str, str]]] = []

    for r in range(rows):
        sy0 = int(y0 + r * dy)
        sy1 = min(h, int(y0 + (r + 1) * dy))
        if sy1 <= sy0:
            sy1 = min(h, sy0 + 1)
        mid_y = (sy0 + sy1) // 2
        env = row_env.get(mid_y, (9999, -9999))

        row_cells: List[Tuple[str, str]] = []
        for c in range(cols):
            sx0 = int(x0 + c * dx)
            sx1 = min(w, int(x0 + (c + 1) * dx))
            if sx1 <= sx0:
                sx1 = min(w, sx0 + 1)
            mid_x = (sx0 + sx1) // 2

            # Check if cell is outside the active artwork boundary
            if mid_x < env[0] or mid_x > env[1]:
                row_cells.append((" ", "space"))
                continue

            # Gather cell pixels
            cell_px: List[Tuple[int, int, int]] = []
            for py in range(sy0, sy1):
                row_ref = grid[py]
                for px in range(sx0, sx1):
                    cell_px.append(row_ref[px])

            if not cell_px:
                row_cells.append((" ", "space"))
                continue

            max_val = max(max(px) for px in cell_px)
            if max_val < 18:
                row_cells.append((" ", "space"))
                continue

            # Classify pixel groups inside cell
            w_cnt = sum(1 for cr, cg, cb in cell_px if cr > 130 and cg > 130 and cb > 130 and abs(cr - cg) < 40)
            r_cnt = sum(1 for cr, cg, cb in cell_px if cr > 55 and cr > 1.25 * max(cg, cb) + 8)
            b_cnt = sum(1 for cr, cg, cb in cell_px if max(cr, cg, cb) < 50)
            total = len(cell_px)

            avg_lum = sum(0.299 * cr + 0.587 * cg + 0.114 * cb for cr, cg, cb in cell_px) / total

            # 1. White Highlights (eyes, hood trim, glowing code)
            if w_cnt >= max(2, int(total * 0.05)):
                idx = min(len(ramp_white) - 1, int((avg_lum / 255.0) * len(ramp_white)))
                row_cells.append((ramp_white[idx], "white"))
            # 2. Red Artwork Structure (hood, frame, biohazard rings, red binary stream)
            elif r_cnt > b_cnt or r_cnt >= int(total * 0.20):
                norm_lum = min(1.0, max(0.0, (avg_lum - 20) / 160.0))
                idx = min(len(ramp_red) - 1, int(norm_lum * len(ramp_red)))
                row_cells.append((ramp_red[idx], "red"))
            # 3. Black Inner Artwork (mask, eye cutouts, shadows, inner texture)
            else:
                idx = (c + r) % len(ramp_black)
                row_cells.append((ramp_black[idx], "black"))

        matrix.append(row_cells)

    return cols, rows, matrix


def format_color_svg_tspans(
    matrix: List[List[Tuple[str, str]]],
    start_x: float = 62.8,
    start_y: float = 128.5,
    line_spacing: float = 7.0,
    is_light: bool = False,
) -> str:
    """
    Format color-aware character matrix into compact, valid SVG <tspan> rows.
    Contiguous runs of identical colors are grouped into single <tspan fill="..."> elements.
    """
    color_palette = COLOR_MAP_LIGHT if is_light else COLOR_MAP
    tspans: List[str] = []

    for r_idx, row in enumerate(matrix):
        y_pos = start_y + r_idx * line_spacing
        row_segments: List[str] = []
        cur_color_tag: Optional[str] = None
        cur_chars: List[str] = []

        for ch, tag in row:
            if tag == "space":
                if cur_chars and cur_color_tag:
                    fill = color_palette[cur_color_tag]
                    text = html.escape("".join(cur_chars))
                    row_segments.append(f'<tspan fill="{fill}">{text}</tspan>')
                    cur_chars = []
                    cur_color_tag = None
                row_segments.append(ch)
            else:
                if tag != cur_color_tag:
                    if cur_chars and cur_color_tag:
                        fill = color_palette[cur_color_tag]
                        text = html.escape("".join(cur_chars))
                        row_segments.append(f'<tspan fill="{fill}">{text}</tspan>')
                        cur_chars = []
                    cur_color_tag = tag
                cur_chars.append(ch)

        if cur_chars and cur_color_tag:
            fill = color_palette[cur_color_tag]
            text = html.escape("".join(cur_chars))
            row_segments.append(f'<tspan fill="{fill}">{text}</tspan>')

        line_markup = "".join(row_segments)
        tspans.append(f'<tspan x="{start_x:.1f}" y="{y_pos:.1f}">{line_markup}</tspan>')

    return "\n        ".join(tspans)


def export_ascii_text(matrix: List[List[Tuple[str, str]]]) -> str:
    """Export character matrix to plain text for assets/xray-ascii.txt."""
    lines = []
    for row in matrix:
        lines.append("".join(ch for ch, _ in row))
    return "\n".join(lines)


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate Color-Aware ASCII/Binary matrix")
    parser.add_argument("--source", default="assets/xray-profile-reference.png", help="Source image path")
    parser.add_argument("--cols", type=int, default=84, help="Number of character columns")
    parser.add_argument("--aspect", type=float, default=0.58, help="Monospace char aspect ratio")
    parser.add_argument("--mode", choices=["ascii", "binary", "hybrid"], default="ascii", help="Character ramp mode")
    parser.add_argument("--output", default="assets/xray-ascii.txt", help="Output text file path")
    args = parser.parse_args()

    if not os.path.exists(args.source):
        print(f"[ERROR] Source image not found: {args.source}", file=sys.stderr)
        sys.exit(1)

    cols, rows, matrix = generate_color_aware_ascii(
        file_path=args.source,
        cols=args.cols,
        char_aspect=args.aspect,
        mode=args.mode,
    )

    print(f"[OK] Generated color-aware matrix: {cols} cols x {rows} rows (mode: {args.mode}).")

    text_content = export_ascii_text(matrix)
    out_dir = os.path.dirname(args.output)
    if out_dir and not os.path.exists(out_dir):
        os.makedirs(out_dir, exist_ok=True)

    with open(args.output, "w", encoding="utf-8") as f:
        f.write(text_content + "\n")

    print(f"[OK] Saved to {args.output}")


if __name__ == "__main__":
    main()
