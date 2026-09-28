#!/usr/bin/env python3
"""
xray_ascii.py - Root CLI entry point for the ASCII/Binary Character Generator.
Invokes assets/xray_ascii.py to convert source images into dense character matrices.

Usage:
  python xray_ascii.py
  python xray_ascii.py --mode binary
  python xray_ascii.py --mode hybrid
  python xray_ascii.py --cols 125
"""

import sys
from assets.xray_ascii import main

if __name__ == "__main__":
    main()
