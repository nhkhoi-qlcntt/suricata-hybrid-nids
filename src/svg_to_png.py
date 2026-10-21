#!/usr/bin/env python3
"""Convert rich-generated terminal SVG screenshots to PNG via headless Chromium."""
import glob
import os
from playwright.sync_api import sync_playwright

HERE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "screenshots")

with sync_playwright() as p:
    browser = p.chromium.launch(executable_path="/opt/pw-browsers/chromium")
    page = browser.new_page(device_scale_factor=2)
    for svg_path in sorted(glob.glob(os.path.join(HERE, "*.svg"))):
        png_path = svg_path.replace(".svg", ".png")
        page.goto("file://" + svg_path)
        page.wait_for_timeout(200)
        el = page.query_selector("svg")
        el.screenshot(path=png_path)
        print("Saved", png_path)
    browser.close()
