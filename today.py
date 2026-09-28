#!/usr/bin/env python3
"""
today.py - Automated GitHub Profile Interface Generator & Telemetry Synchronizer
Author: Bishwajit Das (bishwajit5788)

Generates and maintains the dual-mode cybersecurity technical console
for dark_mode.svg and light_mode.svg, dynamically fetching real telemetry
from the GitHub REST API.

Palette (Semantic Specification):
  MAIN BACKGROUND:     #2F3A2E (Dark Forest/Slate)
  BORDER / FRAME:      #700004 (Dark Garnet)
  SCANNER:             #8D8A84 (Subtle Tech Metallic)
  ASCII PRIMARY:       #1C1714 (Deep Base Character Ink)
  ASCII SECONDARY:     #700004 (Structural Red/Garnet Accent)
  ASCII WHITE SHADING: #FFFFFF (Luminous Highlight Layer)
  GITHUB INFORMATION:  #FFB35A (Warm Amber Information)
  PROFILE NAME:        #A9CBEE (Prestige Ice Blue - ONLY Bishwajit Das)
  TITLE:               #700004 (Dark Garnet Title)
"""

from __future__ import annotations

import argparse
import html
import json
import os
import re
import ssl
import sys
import tempfile
import xml.etree.ElementTree as ET
from typing import Any, Dict, List, Optional, Tuple

try:
    import requests
    HAS_REQUESTS = True
except ImportError:
    import urllib.request
    import urllib.parse
    import urllib.error
    HAS_REQUESTS = False


def safe_urlopen(req: Any, timeout: int = 15) -> Any:
    """Execute urlopen with fallback to unverified SSL context if OS cert store is missing."""
    try:
        return urllib.request.urlopen(req, timeout=timeout)
    except urllib.error.URLError as err:
        if "CERTIFICATE_VERIFY_FAILED" in str(err) or "certificate verify failed" in str(err):
            ctx = ssl._create_unverified_context()
            return urllib.request.urlopen(req, context=ctx, timeout=timeout)
        raise


from assets.xray_ascii import (
    export_ascii_text,
    format_color_svg_tspans,
    generate_color_aware_ascii,
)

USER_NAME = os.environ.get("USER_NAME", "bishwajit5788")
GITHUB_TOKEN = os.environ.get("GITHUB_TOKEN") or os.environ.get("ACCESS_TOKEN") or ""
API_BASE = "https://api.github.com"
REQUEST_TIMEOUT = 15

HEADERS: Dict[str, str] = {
    "Accept": "application/vnd.github+json",
    "User-Agent": f"github-profile-sync/{USER_NAME}",
}
if GITHUB_TOKEN:
    HEADERS["Authorization"] = f"Bearer {GITHUB_TOKEN}"

# Parameters for master ASCII artwork in Left Panel
DEFAULT_COLS = 319
DEFAULT_SOURCE = "assets/xray-profile-reference.png"
DEFAULT_ASCII = "assets/xray-ascii.txt"


def build_svg_template(mode: str = "dark", ascii_markup: Optional[str] = None) -> str:
    """
    Build the precision technical console SVG for dark or light mode.
    Strictly constrained to the professional semantic palette:
      - Background:       #2F3A2E (Dark Forest/Slate)
      - Border / Frame:   #700004 (Dark Garnet)
      - Scanner:          #8D8A84 (Subtle Tech Metallic)
      - ASCII Primary:    #1C1714 (Deep Base Character Ink)
      - ASCII Secondary:  #700004 (Structural Red/Garnet Accent)
      - ASCII White:      #FFFFFF (Luminous Highlight Layer)
      - GitHub Info:      #FFB35A (Warm Amber Information)
      - Profile Name:     #A9CBEE (Prestige Ice Blue - ONLY Bishwajit Das)
      - Title:            #700004 (Dark Garnet Title)

    Layer Hierarchy (Strictly Enforced):
      1. Canvas Background
      2. Technical Grid & Radar Reticles
      3. Physical Scanner Glow & Scanning Beam (Behind ASCII)
      4. Master 4:3 Native ASCII Character Field (Dominant, On Top of Scanner)
      5. Frame & Interface Details (Borders, Status, Labels)
    """
    is_dark = (mode == "dark")

    if is_dark:
        bg_canvas = "#2F3A2E"
        bg_panel = "#2F3A2E"
        grid_stroke = "#8D8A84"
        grid_opacity = "0.04"
        border_color = "#700004"
        scanner_color = "#8D8A84"
        info_color = "#FFB35A"
        name_color = "#A9CBEE"
        title_color = "#700004"
        panel_border_op = "0.55"
    else:
        bg_canvas = "#DCE3D8"
        bg_panel = "#DCE3D8"
        grid_stroke = "#8D8A84"
        grid_opacity = "0.05"
        border_color = "#700004"
        scanner_color = "#8D8A84"
        info_color = "#8A4800"
        name_color = "#174E82"
        title_color = "#700004"
        panel_border_op = "0.55"

    if ascii_markup is None:
        ascii_markup = '<tspan x="105.0" y="384.0">[RECON MATRIX ACTIVE]</tspan>'

    return f"""<?xml version="1.0" encoding="UTF-8"?>
<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 1060 600" width="100%" height="100%">
  <defs>
    <!-- Background Technical Grid -->
    <pattern id="techGrid_{mode}" width="36" height="36" patternUnits="userSpaceOnUse">
      <path d="M 36 0 L 0 0 0 36" fill="none" stroke="{grid_stroke}" stroke-opacity="{grid_opacity}" stroke-width="1"/>
      <circle cx="18" cy="18" r="0.8" fill="{grid_stroke}" fill-opacity="{float(grid_opacity)*1.5:.4f}"/>
    </pattern>

    <!-- Subtle Scanline Micro-Texture -->
    <pattern id="scanlines_{mode}" width="4" height="4" patternUnits="userSpaceOnUse">
      <line x1="0" y1="0" x2="4" y2="0" stroke="{grid_stroke}" stroke-opacity="{float(grid_opacity)*0.6:.4f}" stroke-width="1"/>
    </pattern>

    <!-- Physical Scanning Beam Gradients (Strictly #8D8A84 with Opacity Variations) -->
    <!-- 1. Soft Wide Glow (90px height) -->
    <linearGradient id="scanGlowWide_{mode}" x1="0" y1="0" x2="0" y2="1">
      <stop offset="0%" stop-color="{scanner_color}" stop-opacity="0"/>
      <stop offset="25%" stop-color="{scanner_color}" stop-opacity="0.06"/>
      <stop offset="50%" stop-color="{scanner_color}" stop-opacity="0.12"/>
      <stop offset="75%" stop-color="{scanner_color}" stop-opacity="0.06"/>
      <stop offset="100%" stop-color="{scanner_color}" stop-opacity="0"/>
    </linearGradient>

    <!-- 2. Medium Glow (38px height) -->
    <linearGradient id="scanGlowMed_{mode}" x1="0" y1="0" x2="0" y2="1">
      <stop offset="0%" stop-color="{scanner_color}" stop-opacity="0"/>
      <stop offset="20%" stop-color="{scanner_color}" stop-opacity="0.15"/>
      <stop offset="50%" stop-color="{scanner_color}" stop-opacity="0.32"/>
      <stop offset="80%" stop-color="{scanner_color}" stop-opacity="0.15"/>
      <stop offset="100%" stop-color="{scanner_color}" stop-opacity="0"/>
    </linearGradient>

    <!-- 3. Core Aura Falloff (12px height) -->
    <linearGradient id="scanGlowCore_{mode}" x1="0" y1="0" x2="0" y2="1">
      <stop offset="0%" stop-color="{scanner_color}" stop-opacity="0"/>
      <stop offset="35%" stop-color="{scanner_color}" stop-opacity="0.35"/>
      <stop offset="47%" stop-color="{scanner_color}" stop-opacity="0.65"/>
      <stop offset="50%" stop-color="{scanner_color}" stop-opacity="0.90"/>
      <stop offset="53%" stop-color="{scanner_color}" stop-opacity="0.65"/>
      <stop offset="65%" stop-color="{scanner_color}" stop-opacity="0.35"/>
      <stop offset="100%" stop-color="{scanner_color}" stop-opacity="0"/>
    </linearGradient>

    <!-- Scope Clip Path to ensure beam remains strictly within internal monitor -->
    <clipPath id="scopeClip_{mode}">
      <rect x="42" y="86" width="344" height="428" rx="4"/>
    </clipPath>
  </defs>

  <style>
    .mono {{ font-family: "JetBrains Mono", "SFMono-Regular", Menlo, Consolas, "Roboto Mono", monospace; }}
    .ascii {{
      font-family: "JetBrains Mono", Consolas, "SFMono-Regular", Menlo, Monaco, monospace;
      font-size: 7.5px;
      font-weight: 700;
      white-space: pre;
    }}
    .profile-name {{ font-size: 20px; font-weight: 700; fill: {name_color}; }}
    .profile-title {{ font-size: 13.5px; font-weight: 600; fill: {title_color}; letter-spacing: 0.5px; }}
    .desc {{ font-size: 12px; fill: {info_color}; fill-opacity: 0.82; }}
    .label {{ font-size: 12px; font-weight: 600; fill: {info_color}; }}
    .dots {{ font-size: 12px; fill: {info_color}; fill-opacity: 0.40; letter-spacing: 1px; }}
    .val {{ font-size: 12px; fill: {info_color}; }}
    .val-num {{ font-size: 13.5px; font-weight: 700; fill: {info_color}; }}
    .sec-rule {{ font-size: 12px; font-weight: 600; fill: {border_color}; letter-spacing: -0.5px; }}
    .meta-tag {{ font-size: 9.5px; font-weight: 600; fill: {info_color}; fill-opacity: 0.85; letter-spacing: 1px; }}
    .status-text {{ font-size: 10px; font-weight: 700; fill: {border_color}; letter-spacing: 1.5px; }}
    .footer-meta {{ font-size: 9.5px; fill: {info_color}; fill-opacity: 0.65; letter-spacing: 1px; }}
  </style>

  <!-- Canvas Background -->
  <rect width="1060" height="600" fill="{bg_canvas}"/>
  <rect width="1060" height="600" fill="url(#techGrid_{mode})"/>
  <rect width="1060" height="600" fill="url(#scanlines_{mode})"/>

  <!-- Outer Master Chassis Frame -->
  <rect x="16" y="16" width="1028" height="568" rx="8" fill="none" stroke="{border_color}" stroke-width="1.5" stroke-opacity="0.65"/>

  <!-- Outer Corner Reinforcement Brackets -->
  <path d="M 16 36 L 16 16 L 36 16" fill="none" stroke="{border_color}" stroke-width="3"/>
  <path d="M 1024 16 L 1044 16 L 1044 36" fill="none" stroke="{border_color}" stroke-width="3"/>
  <path d="M 16 564 L 16 584 L 36 584" fill="none" stroke="{border_color}" stroke-width="3"/>
  <path d="M 1024 584 L 1044 584 L 1044 564" fill="none" stroke="{border_color}" stroke-width="3"/>

  <!-- Top Frame Coordinates & Status -->
  <text x="42" y="28" class="mono meta-tag">CONSOLE // RED-TEAM RECON STATION</text>
  <text x="1018" y="28" text-anchor="end" class="mono meta-tag">NODE_01 // SECURE CH: 0x7F</text>

  <!-- ============================================================ -->
  <!-- LEFT PANEL: X-RAY / RECON VISUAL (364px wide: x=32 to 396)   -->
  <!-- ============================================================ -->
  <g id="left_panel">
    <!-- 1. Left Panel Housing -->
    <rect x="32" y="32" width="364" height="536" rx="6" fill="{bg_panel}" stroke="{border_color}" stroke-width="1.2" stroke-opacity="{panel_border_op}"/>

    <!-- 2. Technical Grid & Radar Reticles (Behind Scanner & ASCII) -->
    <g id="technical_grid">
      <rect x="42" y="86" width="344" height="428" fill="url(#techGrid_{mode})"/>
      <rect x="42" y="86" width="344" height="428" fill="url(#scanlines_{mode})"/>
      <circle cx="214" cy="300" r="150" fill="none" stroke="{border_color}" stroke-width="0.7" stroke-opacity="0.22" stroke-dasharray="2 6"/>
      <circle cx="214" cy="300" r="106" fill="none" stroke="{border_color}" stroke-width="0.7" stroke-opacity="0.10"/>
      <circle cx="214" cy="300" r="66" fill="none" stroke="{border_color}" stroke-width="0.7" stroke-opacity="0.25" stroke-dasharray="3 4"/>
      <line x1="48" y1="300" x2="380" y2="300" stroke="{border_color}" stroke-width="0.7" stroke-opacity="0.25" stroke-dasharray="4 4"/>
      <line x1="214" y1="92" x2="214" y2="508" stroke="{border_color}" stroke-width="0.7" stroke-opacity="0.25" stroke-dasharray="4 4"/>
    </g>

    <!-- 3. SCANNER GLOW & SCANNING BEAM (BEHIND ASCII CHARACTER FIELD) -->
    <g id="scanner_layer" clip-path="url(#scopeClip_{mode})">
      <g id="scanner_beam" transform="translate(0, 300)">
        <!-- Layer 1: Very soft wide glow -->
        <rect x="42" y="-45" width="344" height="90" fill="url(#scanGlowWide_{mode})"/>
        <!-- Layer 2: Medium glow -->
        <rect x="42" y="-19" width="344" height="38" fill="url(#scanGlowMed_{mode})"/>
        <!-- Layer 3: Controlled core falloff -->
        <rect x="42" y="-6" width="344" height="12" fill="url(#scanGlowCore_{mode})"/>
        <!-- Layer 4: Thin bright scanning core -->
        <rect x="42" y="-1" width="344" height="2" fill="{scanner_color}" fill-opacity="0.88"/>
        <!-- Beam Edge Locator Ticks -->
        <line x1="42" y1="0" x2="52" y2="0" stroke="{scanner_color}" stroke-width="1.8" stroke-opacity="0.95"/>
        <line x1="376" y1="0" x2="386" y2="0" stroke="{scanner_color}" stroke-width="1.8" stroke-opacity="0.95"/>

        <!-- Smooth vertical scan motion: 10s indefinite linear loop (top -> bottom -> top) -->
        <animateTransform
          attributeName="transform"
          type="translate"
          values="0 102; 0 498; 0 102"
          keyTimes="0; 0.5; 1"
          dur="10s"
          repeatCount="indefinite"/>
      </g>
    </g>

    <!-- 4. MASTER 4:3 NATIVE ASCII FIELD (RENDERED ON TOP OF SCANNER) -->
    <!-- Native 4:3 Viewport: 320px x 240px (93% usable width), centered at x=54, y=180 -->
    <g id="ascii_layer">
      <svg x="54" y="180" width="320" height="240" viewBox="0 0 1024 768" preserveAspectRatio="xMidYMid meet">
        <text class="ascii" xml:space="preserve">
          {ascii_markup}
        </text>
      </svg>
    </g>

    <!-- 5. FRAME / SCOPE OVERLAYS / UI DETAILS (FRAMING THE FIELD) -->
    <g id="interface_layer">
      <!-- Internal Scope Dashed Border -->
      <rect x="42" y="86" width="344" height="428" rx="4" fill="none" stroke="{border_color}" stroke-width="1.2" stroke-opacity="0.45" stroke-dasharray="4 4"/>
      <!-- Reticle Corner Precision Brackets -->
      <path d="M 48 98 L 48 92 L 54 92" fill="none" stroke="{border_color}" stroke-width="1.6"/>
      <path d="M 380 98 L 380 92 L 374 92" fill="none" stroke="{border_color}" stroke-width="1.6"/>
      <path d="M 48 502 L 48 508 L 54 508" fill="none" stroke="{border_color}" stroke-width="1.6"/>
      <path d="M 380 502 L 380 508 L 374 508" fill="none" stroke="{border_color}" stroke-width="1.6"/>

      <!-- Header Badges -->
      <rect x="42" y="42" width="168" height="22" rx="3" fill="{border_color}" fill-opacity="0.18" stroke="{border_color}" stroke-width="1"/>
      <text x="48" y="57" class="mono" font-size="10px" font-weight="700" fill="{info_color}" letter-spacing="1px">THREAT SURFACE // RECON</text>

      <rect x="316" y="42" width="70" height="22" rx="3" fill="{border_color}" fill-opacity="0.18" stroke="{border_color}" stroke-width="1"/>
      <text x="351" y="57" text-anchor="middle" class="mono" font-size="10px" font-weight="700" fill="{info_color}">NODE_01</text>

      <!-- Sub-header Telemetry -->
      <text x="44" y="78" class="mono meta-tag">LAT 28.6139° N / LON 77.2090° E</text>
      <text x="384" y="78" text-anchor="end" class="mono meta-tag">FREQ: 2.4/5.8 GHz</text>

      <!-- Footer / Telemetry Status -->
      <line x1="42" y1="520" x2="386" y2="520" stroke="{border_color}" stroke-width="1" stroke-opacity="0.45"/>
      <text x="44" y="536" class="mono meta-tag">THREAT SIGNATURE // VISUAL MAP (4:3 NATIVE)</text>

      <!-- Pulsing Scan Active Beacon -->
      <circle cx="50" cy="552" r="4.5" fill="{border_color}">
        <animate attributeName="opacity" values="1;0.35;1" dur="2s" repeatCount="indefinite"/>
      </circle>
      <text x="62" y="556" class="mono status-text">SCAN STATUS // ACTIVE</text>

      <!-- RF Waveform / Telemetry Signal Bars -->
      <g transform="translate(322, 544)" fill="{border_color}" opacity="0.85">
        <rect x="0" y="8" width="3" height="4" rx="1"/>
        <rect x="5" y="5" width="3" height="7" rx="1"/>
        <rect x="10" y="2" width="3" height="10" rx="1"/>
        <rect x="15" y="0" width="3" height="12" rx="1"/>
        <rect x="20" y="4" width="3" height="8" rx="1"/>
        <rect x="25" y="7" width="3" height="5" rx="1"/>
        <rect x="30" y="3" width="3" height="9" rx="1"/>
        <rect x="35" y="1" width="3" height="11" rx="1"/>
        <rect x="40" y="6" width="3" height="6" rx="1"/>
        <rect x="45" y="9" width="3" height="3" rx="1"/>
      </g>
    </g>
  </g>

  <!-- ============================================================ -->
  <!-- RIGHT PANEL: PROFILE INFORMATION (x=416 to 1028)             -->
  <!-- ============================================================ -->
  <g id="right_panel" class="mono">
    <!-- Panel Housing -->
    <rect x="416" y="32" width="612" height="536" rx="6" fill="{bg_panel}" stroke="{border_color}" stroke-width="1.2" stroke-opacity="{panel_border_op}"/>

    <!-- Technical Framing Corner Brackets -->
    <path d="M 426 48 L 426 40 L 434 40" fill="none" stroke="{border_color}" stroke-width="2.5"/>
    <path d="M 1018 48 L 1018 40 L 1010 40" fill="none" stroke="{border_color}" stroke-width="2.5"/>
    <path d="M 426 552 L 426 560 L 434 560" fill="none" stroke="{border_color}" stroke-width="2.5"/>
    <path d="M 1018 552 L 1018 560 L 1010 560" fill="none" stroke="{border_color}" stroke-width="2.5"/>

    <!-- 1. Identity Line -->
    <g transform="translate(436, 66)">
      <text x="0" y="0" class="label" font-size="16px">$ whoami</text>
      <text x="82" y="0" fill="{border_color}" font-size="16px">→</text>
      <text x="104" y="0" class="profile-name">Bishwajit Das</text>
      <line x1="262" y1="-6" x2="572" y2="-6" stroke="{border_color}" stroke-width="1.2" stroke-opacity="0.5"/>
    </g>

    <!-- 2. Primary Title / Headline -->
    <text x="436" y="96" class="profile-title">Cybersecurity • Embedded Systems • Red Team Research</text>

    <!-- 3. Supporting Description -->
    <text x="436" y="118" class="desc">Building hardware/software security projects, embedded systems,</text>
    <text x="436" y="136" class="desc">wireless research tools, and isolated security research sandboxes.</text>

    <!-- Section Separator Line -->
    <line x1="436" y1="152" x2="1008" y2="152" stroke="{border_color}" stroke-width="1" stroke-opacity="0.35"/>

    <!-- 4. Technical Build Matrix -->
    <!-- Row: Builds -->
    <g transform="translate(436, 175)">
      <text x="0" y="0" class="label">Builds:</text>
      <text x="95" y="0" class="dots">................</text>
      <text x="180" y="0" class="val">SliverOS, PondEyes, EchoNode</text>
    </g>
    <g transform="translate(436, 195)">
      <text x="95" y="0" class="dots">................</text>
      <text x="180" y="0" class="val">Red-Team-Packet-Sniffer, OSINT Threat Mapper</text>
    </g>

    <!-- Row: Radios -->
    <g transform="translate(436, 217)">
      <text x="0" y="0" class="label">Radios:</text>
      <text x="95" y="0" class="dots">................</text>
      <text x="180" y="0" class="val">Wi-Fi, BLE, Sub-GHz</text>
    </g>

    <!-- Row: Tools -->
    <g transform="translate(436, 239)">
      <text x="0" y="0" class="label">Tools:</text>
      <text x="95" y="0" class="dots">................</text>
      <text x="180" y="0" class="val">Blender, Arduino IDE, VS Code</text>
    </g>

    <!-- Row: Languages -->
    <g transform="translate(436, 261)">
      <text x="0" y="0" class="label">Languages:</text>
      <text x="95" y="0" class="dots">................</text>
      <text id="lang_data" x="180" y="0" class="val">C, C++, Python, JavaScript, TypeScript</text>
    </g>

    <!-- 5. Contact Section -->
    <g transform="translate(436, 287)">
      <text x="0" y="0" class="sec-rule">─ Contact ─────────────────────────────────────────────────────────</text>
    </g>

    <g transform="translate(436, 311)">
      <text x="0" y="0" class="label">Email:</text>
      <text x="95" y="0" class="dots">................</text>
      <text x="180" y="0" class="val">dbishwajit305@gmail.com</text>
    </g>
    <g transform="translate(436, 331)">
      <text x="0" y="0" class="label">Instagram:</text>
      <text x="95" y="0" class="dots">................</text>
      <text x="180" y="0" class="val">@bishwajit5788</text>
    </g>
    <g transform="translate(436, 351)">
      <text x="0" y="0" class="label">GitHub:</text>
      <text x="95" y="0" class="dots">................</text>
      <text x="180" y="0" class="val">bishwajit5788</text>
    </g>

    <!-- 6. Live GitHub Telemetry -->
    <g transform="translate(436, 377)">
      <text x="0" y="0" class="sec-rule">─ Live GitHub Telemetry ───────────────────────────────────────────</text>
    </g>

    <!-- Stats Grid: 2 Columns with Leader Dots -->
    <g transform="translate(436, 401)">
      <!-- Left Column: Repos -->
      <text x="0" y="0" class="label">Repos:</text>
      <text x="65" y="0" class="dots">........</text>
      <text id="repo_data" x="140" y="0" class="val-num">13</text>

      <!-- Right Column: Stars -->
      <text x="280" y="0" class="label">| Stars:</text>
      <text x="375" y="0" class="dots">........</text>
      <text id="star_data" x="450" y="0" class="val-num">0</text>
    </g>

    <g transform="translate(436, 423)">
      <!-- Left Column: Commits -->
      <text x="0" y="0" class="label">Commits:</text>
      <text x="65" y="0" class="dots">........</text>
      <text id="commit_data" x="140" y="0" class="val-num">102+</text>

      <!-- Right Column: Followers -->
      <text x="280" y="0" class="label">| Followers:</text>
      <text x="375" y="0" class="dots">........</text>
      <text id="follower_data" x="450" y="0" class="val-num">0</text>
    </g>

    <!-- 7. Recent Repositories Matrix -->
    <g transform="translate(436, 449)">
      <text x="0" y="0" class="sec-rule">─ Recent Repositories ─────────────────────────────────────────────</text>
    </g>

    <g transform="translate(436, 473)">
      <text x="0" y="0" class="label">01:</text>
      <text id="recent_1" x="32" y="0" class="val">SliverOS</text>

      <text x="280" y="0" class="label">| 02:</text>
      <text id="recent_2" x="325" y="0" class="val">PondEyes-Omni-Lighthouse</text>
    </g>

    <g transform="translate(436, 497)">
      <text x="0" y="0" class="label">03:</text>
      <text id="recent_3" x="32" y="0" class="val">EchoNode0.1</text>

      <text x="280" y="0" class="label">| 04:</text>
      <text id="recent_4" x="325" y="0" class="val">Automated-OSINT-Threat-Mapper</text>
    </g>

    <!-- System Footer Metadata -->
    <line x1="436" y1="518" x2="1008" y2="518" stroke="{border_color}" stroke-width="1" stroke-opacity="0.35"/>
    <text x="436" y="538" class="footer-meta">ARCH: EMBEDDED-X86 // RADIO: MULTI-BAND // AUTH: VERIFIED SECURE</text>
    <text x="1008" y="538" text-anchor="end" class="footer-meta">STATUS: OPERATIONAL</text>
  </g>
</svg>"""


def github_get(endpoint: str, params: Optional[Dict[str, Any]] = None) -> Any:
    """Safely execute a GET request against the GitHub REST API."""
    url = f"{API_BASE}{endpoint}" if endpoint.startswith("/") else endpoint
    if HAS_REQUESTS:
        response = requests.get(url, headers=HEADERS, params=params, timeout=REQUEST_TIMEOUT)
        if response.status_code == 404:
            raise ValueError(f"GitHub resource not found: {url}")
        if response.status_code == 403 and "rate limit exceeded" in response.text.lower():
            print(f"[WARN] GitHub API rate limit reached on {url}", file=sys.stderr)
            return None
        response.raise_for_status()
        return response.json()
    else:
        full_url = url
        if params:
            full_url = f"{url}?{urllib.parse.urlencode(params)}"
        req = urllib.request.Request(full_url, headers=HEADERS)
        try:
            with safe_urlopen(req, timeout=REQUEST_TIMEOUT) as response:
                return json.loads(response.read().decode("utf-8"))
        except urllib.error.HTTPError as err:
            if err.code == 404:
                raise ValueError(f"GitHub resource not found: {url}")
            if err.code in (403, 409):
                print(f"[WARN] GitHub API notice ({err.code}) on {url}", file=sys.stderr)
                return None
            raise


def fetch_user_profile(user: str) -> Dict[str, Any]:
    """Retrieve the primary profile metadata for the specified user."""
    data = github_get(f"/users/{user}")
    if not isinstance(data, dict):
        raise RuntimeError(f"Unexpected API response for user profile: {data}")
    return data


def fetch_user_repositories(user: str) -> List[Dict[str, Any]]:
    """Retrieve all non-fork public repositories owned by the user."""
    repos: List[Dict[str, Any]] = []
    page = 1
    while True:
        params = {
            "per_page": 100,
            "page": page,
            "type": "owner",
            "sort": "pushed",
            "direction": "desc",
        }
        batch = github_get(f"/users/{user}/repos", params=params)
        if not batch or not isinstance(batch, list):
            break
        owned_batch = [
            r for r in batch
            if isinstance(r, dict)
            and r.get("owner", {}).get("login", "").lower() == user.lower()
            and not r.get("fork", False)
        ]
        repos.extend(owned_batch)
        if len(batch) < 100:
            break
        page += 1
    return repos


def calculate_total_stars(repos: List[Dict[str, Any]]) -> int:
    """Calculate the total number of stargazers across all owned repositories."""
    return sum(int(r.get("stargazers_count", 0)) for r in repos)


def fetch_total_commits(user: str, repos: List[Dict[str, Any]]) -> int:
    """
    Calculate the total number of commits authored by user across owned repositories.
    Handles empty repositories (409 Conflict) and rate limiting gracefully.
    """
    total_commits = 0
    for r in repos:
        repo_name = r.get("name")
        if not repo_name:
            continue
        try:
            commits_url = f"{API_BASE}/repos/{user}/{repo_name}/commits"
            params = {"author": user, "per_page": 100}
            if HAS_REQUESTS:
                resp = requests.get(commits_url, headers=HEADERS, params=params, timeout=REQUEST_TIMEOUT)
                if resp.status_code == 200:
                    commits_list = resp.json()
                    if isinstance(commits_list, list):
                        total_commits += len(commits_list)
                elif resp.status_code == 409:
                    continue
                elif resp.status_code == 403:
                    print(f"[WARN] Rate limited while fetching commits for {repo_name}", file=sys.stderr)
                    break
            else:
                full_url = f"{commits_url}?{urllib.parse.urlencode(params)}"
                req = urllib.request.Request(full_url, headers=HEADERS)
                try:
                    with safe_urlopen(req, timeout=REQUEST_TIMEOUT) as resp:
                        commits_list = json.loads(resp.read().decode("utf-8"))
                        if isinstance(commits_list, list):
                            total_commits += len(commits_list)
                except urllib.error.HTTPError as err:
                    if err.code in (403, 409):
                        continue
                    raise
        except Exception as err:
            print(f"[INFO] Skipping commits for {repo_name}: {err}", file=sys.stderr)
            continue
    return total_commits


def extract_top_languages(repos: List[Dict[str, Any]], limit: int = 5) -> str:
    """Gather unique programming languages across owned repositories."""
    seen_langs = []
    for r in repos:
        lang = r.get("language")
        if lang and lang not in seen_langs:
            seen_langs.append(lang)
    if seen_langs:
        return ", ".join(seen_langs[:limit])
    return "C, C++, Python, JavaScript, TypeScript"


def extract_recent_repositories(
    repos: List[Dict[str, Any]],
    count: int = 4,
    exclude_profile_repo: bool = True,
) -> List[str]:
    """Return the most recently pushed repository names, formatted cleanly."""
    filtered = []
    for r in repos:
        name = r.get("name", "")
        if exclude_profile_repo and name.lower() == USER_NAME.lower():
            continue
        filtered.append(name)
    formatted = [name[:25] for name in filtered[:count]]
    while len(formatted) < count:
        formatted.append("—")
    return formatted


def replace_svg_placeholder(svg_content: str, element_id: str, new_value: Any) -> str:
    """
    Safely replace text within a <text> or <tspan> tag containing id="element_id".
    Preserves all XML attributes, escapes content, and ensures zero corruption.
    """
    escaped_val = html.escape(str(new_value))
    pattern = rf'(<(?:text|tspan)[^>]*\bid=["\']{re.escape(element_id)}["\'][^>]*>)(.*?)(</(?:text|tspan)>)'
    new_svg, count = re.subn(pattern, rf'\g<1>{escaped_val}\g<3>', svg_content, count=1)
    if count == 0:
        placeholder = f"{{{{{element_id}}}}}"
        if placeholder in svg_content:
            new_svg = svg_content.replace(placeholder, escaped_val)
    return new_svg


def update_svg_file(file_path: str, stats: Dict[str, Any], mode: str, ascii_markup: Optional[str] = None) -> None:
    """Atomically generate or update an SVG file and validate XML."""
    svg_content = build_svg_template(mode, ascii_markup)

    for element_id, value in stats.items():
        svg_content = replace_svg_placeholder(svg_content, element_id, value)

    # Validate XML before writing to disk
    try:
        ET.fromstring(svg_content)
    except ET.ParseError as err:
        raise ValueError(f"Corrupted SVG XML generated for {file_path}: {err}") from err

    dir_name = os.path.dirname(os.path.abspath(file_path)) or "."
    with tempfile.NamedTemporaryFile("w", dir=dir_name, delete=False, encoding="utf-8") as tf:
        tf.write(svg_content)
        temp_name = tf.name

    os.replace(temp_name, file_path)
    print(f"[OK] Successfully refreshed and validated: {file_path}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Refresh GitHub profile SVG telemetry")
    parser.add_argument("--cols", type=int, default=DEFAULT_COLS, help="Columns in character matrix")
    parser.add_argument("--mode", choices=["ascii", "binary", "hybrid"], default="ascii", help="Character ramp mode")
    parser.add_argument("--regenerate", action="store_true", help="Force template regeneration before syncing")
    args = parser.parse_args()

    print(f"[INFO] Synchronizing GitHub profile statistics for user '{USER_NAME}'...")

    # Generate Color-Aware ASCII character matrix (Source Black -> #FFEB93, Red -> #868B32, White -> #FFFFFF)
    print(f"[INFO] Generating master color-aware ASCII character matrix from {DEFAULT_ASCII}...")
    cols, rows, matrix = generate_color_aware_ascii(
        file_path=DEFAULT_SOURCE,
        ascii_path=DEFAULT_ASCII,
    )
    print(f"[OK] Master ASCII matrix loaded ({cols}x{rows} cells).")

    # Format markup for dark and light modes
    dark_ascii_markup = format_color_svg_tspans(
        matrix=matrix,
        is_light=False,
    )
    light_ascii_markup = format_color_svg_tspans(
        matrix=matrix,
        is_light=True,
    )

    try:
        profile = fetch_user_profile(USER_NAME)
        repos = fetch_user_repositories(USER_NAME)
    except Exception as err:
        print(f"[WARN] Live API notice ({err}). Proceeding with current profile baseline.", file=sys.stderr)
        profile = {"public_repos": 13, "followers": 0}
        repos = [
            {"name": "PondEyes-Omni-Lighthouse", "stargazers_count": 0, "language": "C++"},
            {"name": "SliverOS", "stargazers_count": 0, "language": "C"},
            {"name": "EchoNode0.1", "stargazers_count": 0, "language": "Python"},
            {"name": "Automated-OSINT-Threat-Mapper", "stargazers_count": 0, "language": "Python"},
            {"name": "RECONSTRUCTA", "stargazers_count": 0, "language": "TypeScript"},
            {"name": "HOMSPY-CAM", "stargazers_count": 0, "language": "TypeScript"},
        ]

    public_repos = profile.get("public_repos", len(repos))
    followers = profile.get("followers", 0)
    total_stars = calculate_total_stars(repos)
    total_commits = fetch_total_commits(USER_NAME, repos)
    recent_repos = extract_recent_repositories(repos, count=4)
    languages = extract_top_languages(repos)

    commit_display = f"{total_commits}+" if total_commits > 0 else "102+"

    stats: Dict[str, Any] = {
        "repo_data": public_repos,
        "star_data": total_stars,
        "follower_data": followers,
        "commit_data": commit_display,
        "lang_data": languages,
        "recent_1": recent_repos[0],
        "recent_2": recent_repos[1],
        "recent_3": recent_repos[2],
        "recent_4": recent_repos[3],
    }

    print("[INFO] Live Profile Metrics:")
    for k, v in stats.items():
        print(f"  • {k}: {v}")

    update_svg_file("dark_mode.svg", stats, "dark", dark_ascii_markup)
    update_svg_file("light_mode.svg", stats, "light", light_ascii_markup)

    print("[SUCCESS] All profile SVG interfaces updated and validated successfully.")


if __name__ == "__main__":
    main()
