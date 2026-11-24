"""Real-browser regression check for the SPICE source/sweep field layout.

The source fields live inside a two-column fieldset; each field must keep its
label and input inside its own column. This script measures the rendered boxes
in Microsoft Edge headless and fails when one field overlaps its neighbour.

Usage (normal server on port 5000):
    .\\.venv\\Scripts\\python.exe -m bjt_bias.app
    .\\.venv\\Scripts\\python.exe scripts\\browser_layout_check.py
"""

from __future__ import annotations

import html
import json
import os
import re
import shutil
import subprocess
import tempfile
import urllib.request
from pathlib import Path

EDGE = os.environ.get(
    "EDGE_PATH",
    r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
)
BASE = os.environ.get("APP_URL", "http://127.0.0.1:5000/").rstrip("/")
ROOT = Path(__file__).resolve().parent.parent
TMP = Path(tempfile.gettempdir()) / "bjt_layout_check"
VIEWPORTS = ("1280,1400", "390,900")

MEASURE = r"""
<script>
window.addEventListener('load', function () {
  function box(el) {
    var r = el.getBoundingClientRect();
    return {x: +r.x.toFixed(1), right: +r.right.toFixed(1),
            y: +r.y.toFixed(1), bottom: +r.bottom.toFixed(1)};
  }
  var fields = [].map.call(document.querySelectorAll('.source-field'), function (field, i) {
    return {
      i: i,
      label: field.querySelector('label').textContent.trim().replace(/\s+/g, ' '),
      field: box(field),
      labelBox: box(field.querySelector('label')),
      inputBox: box(field.querySelector('input'))
    };
  });
  function hit(a, b) {
    return !(a.right <= b.x || b.right <= a.x || a.bottom <= b.y || b.bottom <= a.y);
  }
  var conflicts = [];
  var overflows = [];
  fields.forEach(function (a) {
    if (a.inputBox.right > a.field.right + 1) {
      overflows.push(a.i + ' input right=' + a.inputBox.right + ' field right=' + a.field.right);
    }
    if (a.labelBox.right > a.field.right + 1) {
      overflows.push(a.i + ' label right=' + a.labelBox.right + ' field right=' + a.field.right);
    }
    fields.forEach(function (b) {
      if (a.i >= b.i) return;
      if (hit(a.inputBox, b.labelBox)) conflicts.push(a.i + ' input <> ' + b.i + ' label');
      if (hit(a.inputBox, b.inputBox)) conflicts.push(a.i + ' input <> ' + b.i + ' input');
      if (hit(a.labelBox, b.inputBox)) conflicts.push(a.i + ' label <> ' + b.i + ' input');
    });
  });
  var pre = document.createElement('pre');
  pre.id = 'layout';
  pre.textContent = JSON.stringify({
    viewport: window.innerWidth + 'x' + window.innerHeight,
    sourceFieldDisplay: getComputedStyle(document.querySelector('.source-field')).display,
    fields: fields,
    conflicts: conflicts,
    overflows: overflows
  });
  document.body.appendChild(pre);
});
</script>
"""


def page_html() -> str:
    TMP.mkdir(parents=True, exist_ok=True)
    shutil.copy(ROOT / "bjt_bias" / "static" / "style.css", TMP / "style.css")
    with urllib.request.urlopen(f"{BASE}/?mode=divider", timeout=10) as response:
        body = response.read().decode("utf-8")
    body = body.replace("/static/style.css", "style.css")
    return body.replace("</body>", MEASURE + "</body>")


def measure(viewport: str, body: str) -> dict:
    page = TMP / f"layout-{viewport.replace(',', 'x')}.html"
    page.write_text(body, encoding="utf-8")
    proc = subprocess.run(
        [
            EDGE, "--headless=new", "--disable-gpu", "--no-first-run",
            f"--user-data-dir={TMP / ('profile-' + viewport.replace(',', 'x'))}",
            f"--window-size={viewport}", "--virtual-time-budget=3000",
            "--dump-dom", page.as_uri(),
        ],
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=120,
    )
    match = re.search(r'<pre id="layout">(.*?)</pre>', proc.stdout, re.S)
    if not match:
        raise RuntimeError(f"no layout result for {viewport}: {proc.stdout[-800:]}")
    return json.loads(html.unescape(match.group(1)))


def main() -> int:
    body = page_html()
    failed = False
    for viewport in VIEWPORTS:
        result = measure(viewport, body)
        ok = not result["conflicts"] and not result["overflows"]
        print(
            f"{'PASS' if ok else 'FAIL'} {viewport} "
            f"display={result['sourceFieldDisplay']} "
            f"conflicts={result['conflicts']} overflows={result['overflows']}"
        )
        failed |= not ok
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
