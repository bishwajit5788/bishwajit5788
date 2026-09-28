#!/usr/bin/env python3
"""
xray_ascii.py - Precision Master ASCII Art Integration & Color Mapping Engine
Preserves the exact visual geometry of the master ASCII artwork and maps
source colors (Black, Red, White) from the reference image.

Author: Bishwajit Das (bishwajit5788)

Color Specification (Strict):
  SOURCE BLACK -> #FFEB93 (Lemon Meringue)
  SOURCE RED   -> #868B32 (Olive Grove)
  SOURCE WHITE -> #FFFFFF (White Highlight Layer)
  UI / SCANNER -> #700004 (Dark Garnet)
  BACKGROUND   -> #1A2517 (Dark Olive)
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

ASCII_TEXT_PATH = "assets/xray-ascii.txt"
COLOR_SOURCE_PATH = "assets/xray-profile-reference.png"


def load_master_ascii_lines(text_path: str = ASCII_TEXT_PATH) -> List[str]:
    """Load the master ASCII text lines, ensuring uniform padded width."""
    if not os.path.exists(text_path):
        raise FileNotFoundError(f"Master ASCII text file not found: {text_path}")
    with open(text_path, "r", encoding="utf-8") as f:
        lines = [line.rstrip("\r\n") for line in f if line.strip() or len(line) > 0]
    if not lines:
        raise ValueError(f"Master ASCII file is empty: {text_path}")
    max_len = max(len(l) for l in lines)
    return [l.ljust(max_len) for l in lines]


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
            for i in range(bpp, stride):
                cur_row[i] = (cur_row[i] + cur_row[i - bpp]) & 0xFF
        elif filter_type == 2:  # Up
            for i in range(stride):
                cur_row[i] = (cur_row[i] + prev_row[i]) & 0xFF
        elif filter_type == 3:  # Average
            for i in range(stride):
                left = cur_row[i - bpp] if i >= bpp else 0
                up = prev_row[i]
                cur_row[i] = (cur_row[i] + ((left + up) >> 1)) & 0xFF
        elif filter_type == 4:  # Paeth
            for i in range(stride):
                a = cur_row[i - bpp] if i >= bpp else 0
                b = prev_row[i]
                c = prev_row[i - bpp] if i >= bpp else 0
                p = a + b - c
                pa = abs(p - a)
                pb = abs(p - b)
                pc = abs(p - c)
                pr = a if (pa <= pb and pa <= pc) else (b if pb <= pc else c)
                cur_row[i] = (cur_row[i] + pr) & 0xFF

        prev_row = cur_row

        row_pixels: List[Tuple[int, int, int]] = []
        if color_type == 0:
            for i in range(width):
                g = cur_row[i]
                row_pixels.append((g, g, g))
        elif color_type == 2:
            for i in range(0, stride, 3):
                row_pixels.append((cur_row[i], cur_row[i + 1], cur_row[i + 2]))
        elif color_type == 6:
            for i in range(0, stride, 4):
                row_pixels.append((cur_row[i], cur_row[i + 1], cur_row[i + 2]))
        grid.append(row_pixels)

    return width, height, grid


def sample_patch_rgb(
    grid: List[List[Tuple[int, int, int]]],
    center_y: int,
    center_x: int,
    max_h: int,
    max_w: int,
    radius: int = 1,
) -> Tuple[float, float, float]:
    """Sample an average RGB value around a neighborhood patch."""
    r_sum = g_sum = b_sum = 0
    count = 0
    for y in range(max(0, center_y - radius), min(max_h, center_y + radius + 1)):
        for x in range(max(0, center_x - radius), min(max_w, center_x + radius + 1)):
            rgb = grid[y][x]
            r_sum += rgb[0]
            g_sum += rgb[1]
            b_sum += rgb[2]
            count += 1
    if count == 0:
        return 0.0, 0.0, 0.0
    return r_sum / count, g_sum / count, b_sum / count


def classify_source_color(cr: float, cg: float, cb: float) -> str:
    """Classify sampled RGB into one of the three primary source groups: white, red, black."""
    # White highlight layer: high brightness across channels
    if cr > 175 and cg > 175 and cb > 175:
        return "white"
    # Red layer: strong red prominence
    elif cr > 80 and cr > cg * 1.35 and cr > cb * 1.35:
        return "red"
    # Black layer: dark shadows, inner silhouette, and background cutouts
    else:
        return "black"


def generate_color_aware_ascii(
    file_path: str = COLOR_SOURCE_PATH,
    ascii_path: str = ASCII_TEXT_PATH,
    cols: Optional[int] = None,
    char_aspect: float = 0.58,
    mode: str = "ascii",
) -> Tuple[int, int, List[List[Tuple[str, str]]]]:
    """
    Generate the color-aware character matrix using the master ASCII geometry
    and sampling colors from the reference image.
    Returns:
      (cols, rows, matrix) where matrix[r][c] = (char, color_key)
    """
    lines = load_master_ascii_lines(ascii_path)
    num_rows = len(lines)
    num_cols = len(lines[0])

    w_img, h_img, grid = decode_png_rgb(file_path)

    matrix: List[List[Tuple[str, str]]] = []

    for r in range(num_rows):
        row_cells: List[Tuple[str, str]] = []
        line = lines[r]
        frac_y = r / (num_rows - 1) if num_rows > 1 else 0.0
        # Reference artwork bounding box is rows 1..843, cols 104..919
        y_ref = int(round(1.0 + frac_y * (843.0 - 1.0)))
        y_ref = max(0, min(h_img - 1, y_ref))

        for c in range(num_cols):
            ch = line[c]
            if ch == " ":
                row_cells.append((" ", "space"))
                continue

            frac_x = c / (num_cols - 1) if num_cols > 1 else 0.0
            x_ref = int(round(104.0 + frac_x * (919.0 - 104.0)))
            x_ref = max(0, min(w_img - 1, x_ref))

            cr, cg, cb = sample_patch_rgb(grid, y_ref, x_ref, h_img, w_img, radius=1)
            color_group = classify_source_color(cr, cg, cb)
            row_cells.append((ch, color_group))

        matrix.append(row_cells)

    return num_cols, num_rows, matrix


def export_ascii_text(matrix: List[List[Tuple[str, str]]]) -> str:
    """Export the character matrix to clean plain text format."""
    lines = []
    for row in matrix:
        lines.append("".join(char for char, _ in row))
    return "\n".join(lines)


def format_color_svg_tspans(
    matrix: List[List[Tuple[str, str]]],
    start_x: float = 55.0,
    start_y: float = 134.0,
    line_spacing: float = 1.84,
    target_width: float = 250.0,
    is_light: bool = False,
) -> str:
    """
    Format the multi-colored character matrix into optimized SVG <tspan> elements.
    Contiguous characters of the same color are grouped into compact runs.
    """
    color_palette = COLOR_MAP_LIGHT if is_light else COLOR_MAP
    lines_markup: List[str] = []

    for r, row in enumerate(matrix):
        curr_y = start_y + (r * line_spacing)
        current_color_key: Optional[str] = None
        current_chars: List[str] = []
        row_tspans: List[str] = []

        for ch, color_key in row:
            if ch == "&":
                esc_ch = "&amp;"
            elif ch == "<":
                esc_ch = "&lt;"
            elif ch == ">":
                esc_ch = "&gt;"
            else:
                esc_ch = ch

            if color_key == current_color_key:
                current_chars.append(esc_ch)
            else:
                if current_chars:
                    run_text = "".join(current_chars)
                    if current_color_key == "space":
                        row_tspans.append(run_text)
                    else:
                        fill_color = color_palette.get(current_color_key, color_palette["black"])
                        row_tspans.append(f'<tspan fill="{fill_color}">{run_text}</tspan>')
                current_color_key = color_key
                current_chars = [esc_ch]

        if current_chars:
            run_text = "".join(current_chars)
            if current_color_key == "space":
                row_tspans.append(run_text)
            else:
                fill_color = color_palette.get(current_color_key, color_palette["black"])
                row_tspans.append(f'<tspan fill="{fill_color}">{run_text}</tspan>')

        line_content = "".join(row_tspans)
        lines_markup.append(
            f'<tspan x="{start_x:.1f}" y="{curr_y:.2f}" textLength="{target_width:.1f}" lengthAdjust="spacingAndGlyphs">{line_content}</tspan>'
        )

    return "\n        ".join(lines_markup)


def main() -> None:
    parser = argparse.ArgumentParser(description="Master ASCII Character Field Generator")
    parser.add_argument("--source", default=COLOR_SOURCE_PATH, help="Color reference image path")
    parser.add_argument("--ascii", default=ASCII_TEXT_PATH, help="Master ASCII text file path")
    parser.add_argument("--export-text", action="store_true", help="Export to plain text")
    args = parser.parse_args()

    print(f"[INFO] Generating master ASCII matrix from {args.ascii} with colors from {args.source}...")
    cols, rows, matrix = generate_color_aware_ascii(
        file_path=args.source,
        ascii_path=args.ascii,
    )
    print(f"[OK] Generated {cols} columns x {rows} rows character matrix.")

    if args.export_text:
        text = export_ascii_text(matrix)
        with open("assets/xray-ascii.txt", "w", encoding="utf-8") as f:
            f.write(text + "\n")
        print("[OK] Saved to assets/xray-ascii.txt")


if __name__ == "__main__":
    main()
