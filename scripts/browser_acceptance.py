"""Run the Lab 03 browser acceptance cases A1-A5 with Microsoft Edge.

Why Edge instead of Playwright MCP: this machine has no Node.js/npx, so the
Playwright MCP server cannot start. Edge is a real Chromium browser, so the
cases still run in a browser (form POST + rendered DOM + screenshot).

Usage:
    .\\.venv\\Scripts\\python.exe -m bjt_bias.app    # keep this running
    .\\.venv\\Scripts\\python.exe scripts\\browser_acceptance.py

Environment:
    EDGE_PATH  full path to msedge.exe (default: Program Files (x86))
    APP_URL    app root URL (default: http://127.0.0.1:5000/)
"""

import json
import os
import re
import subprocess
import sys
import tempfile
from pathlib import Path

EDGE = os.environ.get(
    "EDGE_PATH",
    r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
)
BASE = os.environ.get("APP_URL", "http://127.0.0.1:5000/")
TMP = Path(tempfile.gettempdir()) / "bjt_acceptance"
EVIDENCE = Path(__file__).resolve().parent.parent / "docs" / "evidence"
PROFILE = TMP / "edgeprofile"

CASES = [
    ("A1", "divider", {
        "mode": "divider", "vcc": "12",
        "r1": "100", "r1_unit": "kohm", "r2": "22", "r2_unit": "kohm",
        "rc": "2.2", "rc_unit": "kohm", "re": "1", "re_unit": "kohm",
        "beta": "100", "vbe": "0.7",
    }),
    ("A2", "fixed", {
        "mode": "fixed", "vcc": "12", "rc": "2.2", "rc_unit": "kohm",
        "beta": "100", "vbe": "0.7", "rb": "1", "rb_unit": "mohm",
    }),
    ("A3", "emitter", {
        "mode": "emitter", "vcc": "12", "rc": "2.2", "rc_unit": "kohm",
        "beta": "100", "vbe": "0.7", "rb": "1", "rb_unit": "mohm",
        "re": "1", "re_unit": "kohm",
    }),
    ("A4", "emitter", {
        "mode": "emitter", "vcc": "12", "rc": "2.2", "rc_unit": "kohm",
        "beta": "100", "vbe": "0.7", "rb": "1", "rb_unit": "mohm",
        "re": "2", "re_unit": "kohm",
    }),
    ("A5", "fixed", {
        "mode": "fixed", "vcc": "12", "rc": "2.2", "rc_unit": "kohm",
        "beta": "100", "vbe": "0.7", "rb": "0", "rb_unit": "kohm",
    }),
]


def form_html(case_id, fields):
    inputs = "\n".join(
        f'  <input name="{k}" value="{v}">' for k, v in fields.items()
    )
    return f"""<!doctype html>
<meta charset="utf-8">
<title>{case_id}</title>
<form id="f" method="post" action="{BASE}">
{inputs}
</form>
<script>document.getElementById('f').submit();</script>
"""


def strip_tags(text):
    return re.sub(r"<[^>]+>", "", text).strip()


def run_edge(args):
    cmd = [
        EDGE, "--headless=new", "--disable-gpu", "--no-first-run",
        f"--user-data-dir={PROFILE}", "--virtual-time-budget=8000",
        *args,
    ]
    proc = subprocess.run(cmd, capture_output=True, text=True,
                          encoding="utf-8", errors="replace", timeout=120)
    return proc.stdout


def parse(dom):
    out = {}
    table = re.search(r'<table class="results">(.*?)</table>', dom, re.S)
    values = []
    if table:
        for sym, val in re.findall(
            r"<tr>\s*<td>(.*?)</td>\s*<td>(.*?)</td>", table.group(1), re.S
        ):
            values.append((strip_tags(sym), strip_tags(val)))
    out["values"] = values
    banner = re.search(r'class="banner banner-(\w+)"', dom)
    out["banner"] = banner.group(1) if banner else None
    heading = re.search(r"DC Bias Results\s*(?:&mdash;|—)\s*([^<]+)", dom)
    out["heading"] = heading.group(1).strip() if heading else None
    err = re.search(r"<h2>Invalid input \(([^)]*)\)</h2>", dom)
    out["error_title"] = err.group(1) if err else None
    if err:
        block = dom[dom.index('<section class="errors"'):]
        block = block[:block.index("</section>")]
        out["errors"] = [
            strip_tags(x) for x in re.findall(r"<li>(.*?)</li>", block, re.S)
        ]
    else:
        out["errors"] = []
    svg = re.search(r'<svg class="schematic".*?</svg>', dom, re.S)
    texts = []
    if svg:
        texts = [
            strip_tags(t)
            for t in re.findall(r"<text[^>]*>(.*?)</text>", svg.group(0), re.S)
        ]
    out["svg"] = [t for t in texts if t]
    return out


def main():
    if not Path(EDGE).exists():
        print(f"Edge not found at {EDGE}; set EDGE_PATH.")
        return 2
    EVIDENCE.mkdir(parents=True, exist_ok=True)
    TMP.mkdir(parents=True, exist_ok=True)
    summary = {}
    for case_id, mode, fields in CASES:
        html_path = TMP / f"accept_{case_id}.html"
        html_path.write_text(form_html(case_id, fields), encoding="utf-8")
        uri = html_path.as_uri()
        parsed = parse(run_edge(["--dump-dom", uri]))
        parsed["mode"] = mode
        summary[case_id] = parsed

        shot = EVIDENCE / f"{case_id.lower()}.png"
        run_edge([f"--screenshot={shot}", "--window-size=1280,1400", uri])

        print(f"=== {case_id} ({mode}) ===")
        print("  heading:", parsed["heading"])
        print("  banner :", parsed["banner"])
        print("  values :", parsed["values"])
        print("  errors :", parsed["errors"])
        print("  svg    :", parsed["svg"])
        print("  shot   :", shot.exists())

    out_json = TMP / "acceptance.json"
    out_json.write_text(
        json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print("saved", out_json)
    return 0


if __name__ == "__main__":
    sys.exit(main())
