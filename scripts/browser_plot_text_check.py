"""Real-browser regression check for overlapping text inside the AC Bode SVG.

The Bode y-axis titles used to sit at the same x as the tick labels, so Edge
rendered e.g. "4.8" on top of "Gain (dB)". This script POSTs a real AC sweep,
loads the returned page in Edge headless and asserts that no two SVG <text>
boxes overlap. The POST uses Flask's test_client so the check always measures
the current source, not a stale server process.

Usage:
    .\\.venv\\Scripts\\python.exe scripts\\browser_plot_text_check.py
"""

from __future__ import annotations

import html
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from bjt_bias.app import create_app  # noqa: E402

EDGE = os.environ.get(
    "EDGE_PATH",
    r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
)
BASE = os.environ.get("APP_URL", "http://127.0.0.1:5000/").rstrip("/")
TMP = Path(tempfile.gettempdir()) / "bjt_plot_text_check"

FORM = {
    "mode": "divider",
    "vcc": "12",
    "r1": "100", "r1_unit": "kohm",
    "r2": "22", "r2_unit": "kohm",
    "rc": "2.2", "rc_unit": "kohm",
    "re": "1", "re_unit": "kohm",
    "beta": "100", "vbe": "0.7",
    "amplitude_mv": "10",
    "frequency_hz": "1000",
    "ac_start_hz": "10",
    "ac_stop_hz": "1000000",
    "ac_points_dec": "20",
    "analysis": "ac",
}

MEASURE = r"""
<script>
window.addEventListener('load', function () {
  var svg = document.querySelector('.spice-plot svg');
  if (!svg) {
    var missing = document.createElement('pre');
    missing.id = 'plot-text';
    missing.textContent = JSON.stringify({error: 'no SPICE plot'});
    document.body.appendChild(missing);
    return;
  }
  function textBoxes() {
    return Array.from(svg.querySelectorAll('text')).map(function (t, i) {
      var r = t.getBoundingClientRect();
      return {i: i, text: t.textContent.trim(), x: +r.x.toFixed(1), y: +r.y.toFixed(1),
              right: +r.right.toFixed(1), bottom: +r.bottom.toFixed(1)};
    });
  }
  function hit(a, b) {
    return !(a.right <= b.x || b.right <= a.x || a.bottom <= b.y || b.bottom <= a.y);
  }
  var boxes = textBoxes();
  var overlaps = [];
  for (var i = 0; i < boxes.length; i++) {
    for (var j = i + 1; j < boxes.length; j++) {
      if (hit(boxes[i], boxes[j])) {
        overlaps.push(boxes[i].text + ' <> ' + boxes[j].text);
      }
    }
  }
  var pre = document.createElement('pre');
  pre.id = 'plot-text';
  pre.textContent = JSON.stringify({
    desc: svg.querySelector('desc') ? svg.querySelector('desc').textContent : '',
    count: boxes.length, overlaps: overlaps
  });
  document.body.appendChild(pre);
});
</script>
"""


def page_html() -> str:
    TMP.mkdir(parents=True, exist_ok=True)
    shutil.copy(ROOT / "bjt_bias" / "static" / "style.css", TMP / "style.css")
    body = create_app().test_client().post("/", data=FORM).get_data(as_text=True)
    body = body.replace("/static/style.css", "style.css")
    return body.replace("</body>", MEASURE + "</body>")


def main() -> int:
    page = TMP / "ac.html"
    page.write_text(page_html(), encoding="utf-8")
    proc = subprocess.run(
        [
            EDGE, "--headless=new", "--disable-gpu", "--no-first-run",
            f"--user-data-dir={TMP / 'profile'}", "--window-size=1280,1400",
            "--virtual-time-budget=3000", "--dump-dom", page.as_uri(),
        ],
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=120,
    )
    match = re.search(r'<pre id="plot-text">(.*?)</pre>', proc.stdout, re.S)
    if not match:
        print("FAIL no measurement: " + proc.stdout[-800:])
        return 1
    result = json.loads(html.unescape(match.group(1)))
    if "error" in result:
        print(f"FAIL {result['error']}")
        return 1
    ok = not result["overlaps"]
    print(
        f"{'PASS' if ok else 'FAIL'} {result['count']} SVG text boxes - "
        f"overlaps={result['overlaps']} - {result['desc']}"
    )
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
