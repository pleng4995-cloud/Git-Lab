# BJT Lab UI Redesign Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** เปลี่ยนหน้า `/` ของ `bjt_bias/` ให้เป็น layout แบบ Lab 02 (header + 3 คอลัมน์ + verification + Week 2 Goal) โดยตัวเลขทุกตัวมาจาก engine เดิม

**Architecture:** restyle in place — ขยาย `bjt_bias/app.py` ให้รับ unit selector และเตรียมข้อมูลสำหรับ template, เขียน `templates/index.html` + `static/style.css` ใหม่, ไม่แตะ `bjt_bias/bias.py`

**Tech Stack:** Python 3.14, Flask 3.1.3, Jinja2, `unittest`, inline SVG, CSS (ไม่มี dependency ใหม่)

**Spec:** `docs/superpowers/specs/2026-11-11-bjt-lab-ui-redesign-design.md`

## Global Constraints

- `bjt_bias/bias.py` ห้ามแก้ — `analyze_bias`, `OPERATING_POINT_FIELDS`, `VCE_SAT_V` ใช้ตามที่มี
- dependency มีแค่ `flask` (ตาม `requirements.txt` เดิม) — ห้ามเพิ่ม
- ใช้ `unittest` เท่านั้น
- ไม่ใช้ CDN / web font / icon library ภายนอก
- เทสเดิม 43 ตัวต้องผ่านทุก task
- ค่า default ฟอร์ม: `VCC=12 V`, `R1=100 kΩ`, `R2=22 kΩ`, `RC=2.2 kΩ`, `RE=1 kΩ`, `beta=100`, `VBE=0.7 V`
- unit key: `ohm`=1, `kohm`=1e3, `mohm`=1e6, `v`=1, `none`=1; ไม่มี key → 1
- ตัวเลขที่แสดงต้องมาจาก `analyze_bias` เท่านั้น (ห้าม hardcode ค่าจาก mockup)

## Review Focus

1. **พิมพ์ suffix พร้อมเลือก unit** (`r1="47k"` + `r1_unit=kohm`) — ต้องได้ error ที่อ่านรู้เรื่อง ไม่ใช่ 47 MΩ เงียบ ๆ → Task 1
2. **POST ที่ไม่มี `*_unit` key** (curl/ฟอร์มเก่า) — ต้องใช้หน่วยฐานและคำนวณได้ ไม่ 500 → Task 1
3. **กรอกค่าผิดช่องเดียว** — หน้าต้องยัง render unit select และวงจรได้ ไม่ 500 และไม่โชว์ banner → Task 4
4. **Banner ต้องตรงกับ region จาก engine** รวมถึง `V_CE = 0.2 V` ที่ต้องเป็น active → Task 4 (และ boundary เดิมใน `test_bjt_bias`)
5. **หน่วยในตารางผลลัพธ์** — `V_CE` ต้องเป็น V, `I_B` ต้องเป็น µA, `I_C/I_E` ต้องเป็น mA → Task 4

---

### Task 1: Unit-aware parsing

**Files:**
- Modify: `bjt_bias/app.py` (`MULTIPLIERS` ด้านล่าง, `_read_form`)
- Test: `test_bjt_app.py`

**Interfaces:**
- Consumes: `parse_resistance(text, label)`, `parse_number(text, label)`, `RESISTANCE_FIELDS`
- Produces:
  - `UNIT_MULTIPLIERS: dict[str, float]` — `{"": 1.0, "ohm": 1.0, "kohm": 1e3, "mohm": 1e6, "v": 1.0, "none": 1.0}`
  - `unit_multiplier(unit: str) -> float` — key ที่ไม่รู้จัก/ว่าง คืน `1.0`
  - `_read_form` คูณค่าที่ parse ได้ด้วย `unit_multiplier(form.get(f"{name}_unit", ""))`

- [ ] **Step 1: เขียนเทสที่ยังไม่ผ่าน**

```python
from bjt_bias.app import create_app, format_value, parse_resistance, unit_multiplier

class TestUnits(unittest.TestCase):
    def test_unit_multiplier_known_and_unknown_keys(self):
        self.assertEqual(unit_multiplier(""), 1.0)
        self.assertEqual(unit_multiplier("ohm"), 1.0)
        self.assertEqual(unit_multiplier("kohm"), 1e3)
        self.assertEqual(unit_multiplier("mohm"), 1e6)
        self.assertEqual(unit_multiplier("v"), 1.0)
        self.assertEqual(unit_multiplier("none"), 1.0)
        self.assertEqual(unit_multiplier("xyz"), 1.0)

    def test_route_applies_unit_selector(self):
        client = create_app().test_client()
        with_unit = client.post("/", data={**VALID_FORM, "r1": "47", "r1_unit": "kohm"})
        self.assertIn("1.324", with_unit.get_data(as_text=True))

    def test_route_rejects_suffix_plus_unit_selector(self):
        client = create_app().test_client()
        response = client.post("/", data={**VALID_FORM, "r1": "47k", "r1_unit": "kohm"})
        body = response.get_data(as_text=True)
        self.assertEqual(response.status_code, 200)
        self.assertIn("not both", body)
```

- [ ] **Step 2: รันเทสให้เห็นว่า fail**

Run: `.\.venv\Scripts\python.exe -m unittest test_bjt_app.TestUnits -v`
Expected: FAIL — `ImportError: cannot import name 'unit_multiplier'`

- [ ] **Step 3: เพิ่ม `UNIT_MULTIPLIERS` / `unit_multiplier` และคูณใน `_read_form`**

ใน `bjt_bias/app.py` หลัง `MULTIPLIERS`:

```python
UNIT_MULTIPLIERS = {
    "": 1.0,
    "ohm": 1.0,
    "kohm": 1e3,
    "mohm": 1e6,
    "v": 1.0,
    "none": 1.0,
}


def unit_multiplier(unit):
    """Return the multiplier for a unit key; unknown or absent keys mean base units."""
    return UNIT_MULTIPLIERS.get((unit or "").strip().lower(), 1.0)
```

ใน `_read_form` ก่อน parse:

```python
multiplier = unit_multiplier(form.get(f"{name}_unit", ""))
if (
    name in RESISTANCE_FIELDS
    and multiplier != 1.0
    and (raw or "").strip()
    and (raw or "").strip()[-1] in MULTIPLIERS
):
    errors.append(f"{label}: use either a unit selector or a k/M suffix, not both.")
    continue
```

แล้วคูณผลลัพธ์: `parsed[name] = parse_resistance(raw, label) * multiplier` และ `parsed[name] = parse_number(raw, label) * multiplier`

- [ ] **Step 4: รันเทสให้ผ่าน**

Run: `.\.venv\Scripts\python.exe -m unittest test_bjt_app -v`
Expected: PASS ทุกตัว (รวมเทสเดิม)

- [ ] **Step 5: Commit**

```bash
git add bjt_bias/app.py test_bjt_app.py
git commit -m "feat: apply unit selector to parsed bias inputs"
```

---

### Task 2: Field metadata + unit select ในฟอร์ม

**Files:**
- Modify: `bjt_bias/app.py` (`FIELDS`, `_form_fields`, `_read_form` return, `create_app`)
- Modify: `bjt_bias/templates/index.html` (ฟอร์มเดิม — ยังไม่เปลี่ยน layout)
- Test: `test_bjt_app.py`

**Interfaces:**
- Consumes: `unit_multiplier` (Task 1)
- Produces:
  - `FIELDS: tuple[dict, ...]` — แต่ละ dict มี key: `name`, `label` (plain สำหรับ error), `display` (HTML เช่น `"V<sub>CC</sub>"`), `description`, `units` (`tuple[tuple[str, str], ...]` คู่ `(unit_label, unit_key)`), `default_value`, `default_unit`
  - `_read_form(form) -> tuple[dict, dict, dict, list[str]]` — `(values, units, parsed, errors)`; `values[name]` เป็นข้อความดิบ, `units[name]` เป็น unit key
  - `_form_fields(values: dict, units: dict) -> list[dict]` — เพิ่ม key `display`, `description`, `units`, `selected_unit` นอกเหนือจาก `name`, `label`, `value`
  - template context: `fields` ยังเป็น list ของ dict เดิม

- [ ] **Step 1: เขียนเทสที่ยังไม่ผ่าน**

```python
class TestFieldMetadata(unittest.TestCase):
    def setUp(self):
        self.client = create_app().test_client()

    def test_get_renders_unit_selector_with_kilo_ohm_default(self):
        body = self.client.get("/").get_data(as_text=True)
        self.assertIn('name="r1_unit"', body)
        self.assertIn('<option value="kohm" selected>', body)
        for label in ("Ω", "kΩ", "MΩ"):
            self.assertIn(label, body)

    def test_post_echoes_selected_unit(self):
        body = self.client.post(
            "/", data={**VALID_FORM, "r1": "100", "r1_unit": "mohm"}
        ).get_data(as_text=True)
        self.assertIn('<option value="mohm" selected>', body)

    def test_defaults_match_lab_example(self):
        body = self.client.get("/").get_data(as_text=True)
        for value in ('value="12"', 'value="100"', 'value="22"',
                      'value="2.2"', 'value="1"', 'value="100"', 'value="0.7"'):
            self.assertIn(value, body)
```

- [ ] **Step 2: รันเทสให้เห็นว่า fail**

Run: `.\.venv\Scripts\python.exe -m unittest test_bjt_app.TestFieldMetadata -v`
Expected: FAIL — ไม่พบ `name="r1_unit"`

- [ ] **Step 3: เปลี่ยน `FIELDS` เป็น metadata และปรับ `_form_fields` / `_read_form` / route**

`FIELDS` (ค่าตาม Global Constraints):

| name | label | display | description | units | default_value | default_unit |
|---|---|---|---|---|---|---|
| vcc | VCC | `V<sub>CC</sub>` | Supply Voltage | `(("V","v"),)` | `12` | `v` |
| r1 | R1 | `R<sub>1</sub>` | Upper Divider | `(("Ω","ohm"),("kΩ","kohm"),("MΩ","mohm"))` | `100` | `kohm` |
| r2 | R2 | `R<sub>2</sub>` | Lower Divider | เหมือน r1 | `22` | `kohm` |
| rc | RC | `R<sub>C</sub>` | Collector Resistor | เหมือน r1 | `2.2` | `kohm` |
| re | RE | `R<sub>E</sub>` | Emitter Resistor | เหมือน r1 | `1` | `kohm` |
| beta | beta | `β` | Current Gain | `(("–","none"),)` | `100` | `none` |
| vbe | VBE | `V<sub>BE</sub>` | Base–Emitter Voltage | `(("V","v"),)` | `0.7` | `v` |

ใน template ฟอร์มเดิม เพิ่ม select ใน label:

```html
<select name="{{ f.name }}_unit">
  {% for unit_label, unit_key in f.units %}
  <option value="{{ unit_key }}"{% if unit_key == f.selected_unit %} selected{% endif %}>{{ unit_label }}</option>
  {% endfor %}
</select>
```

และใช้ `{{ f.display|safe }}` แทน `{{ f.label }}` (label plain ยังใช้ใน error message)

GET: `values = {spec["name"]: spec["default_value"] for spec in FIELDS}`, `units = {spec["name"]: spec["default_unit"] for spec in FIELDS}`

- [ ] **Step 4: รันเทสให้ผ่าน**

Run: `.\.venv\Scripts\python.exe -m unittest test_bjt_app -v`
Expected: PASS ทุกตัว

- [ ] **Step 5: Commit**

```bash
git add bjt_bias/app.py bjt_bias/templates/index.html test_bjt_app.py
git commit -m "feat: add unit selectors to the bias form"
```

---

### Task 3: Display helpers + result ordering

**Files:**
- Modify: `bjt_bias/app.py`
- Test: `test_bjt_app.py`

**Interfaces:**
- Consumes: `OPERATING_POINT_FIELDS`, `FIELDS`, `parse_resistance`, `parse_number`, `unit_multiplier`
- Produces:
  - `RESULT_ORDER: tuple[str, ...]` — `("v_b_v", "v_e_v", "v_c_v", "v_ce_v", "i_b_a", "i_c_a", "i_e_a")`
  - `ordered_operating_point_fields() -> tuple[tuple, ...]` — เรียงตาม `RESULT_ORDER`
  - `trim_number(number: float) -> str` — 3 ตำแหน่งทศนิยม ตัดศูนย์ท้าย, `"-0"` → `"0"`
  - `format_ohms(value: float) -> str` — `≥1e6` → `"… MΩ"`, `≥1e3` → `"… kΩ"`, อื่น ๆ → `"… Ω"`
  - `format_volts(value: float) -> str` — `"… V"`
  - `format_symbol(symbol: str) -> str` — `"V_CE"` → `"V<sub>CE</sub>"`, `"I_B"` → `"I<sub>B</sub>"`
  - `DEFAULT_INPUTS: dict[str, float]` — ค่า SI ของ default ทุกช่อง
  - `circuit_labels(parsed: dict) -> dict[str, str]` — key `vcc, r1, r2, rc, re, beta`; ใช้ `DEFAULT_INPUTS` เติมช่องที่ parse ไม่ได้

- [ ] **Step 1: เขียนเทสที่ยังไม่ผ่าน**

```python
from bjt_bias.app import (
    circuit_labels,
    format_ohms,
    format_symbol,
    format_volts,
    ordered_operating_point_fields,
)


class TestDisplayHelpers(unittest.TestCase):
    def test_result_order_starts_with_voltages(self):
        keys = [field[0] for field in ordered_operating_point_fields()]
        self.assertEqual(
            keys,
            ["v_b_v", "v_e_v", "v_c_v", "v_ce_v", "i_b_a", "i_c_a", "i_e_a"],
        )

    def test_ohms_auto_scales(self):
        self.assertEqual(format_ohms(470), "470 Ω")
        self.assertEqual(format_ohms(2_200), "2.2 kΩ")
        self.assertEqual(format_ohms(100_000), "100 kΩ")
        self.assertEqual(format_ohms(1e6), "1 MΩ")

    def test_volts_trim_trailing_zeros(self):
        self.assertEqual(format_volts(12), "12 V")
        self.assertEqual(format_volts(0.7), "0.7 V")

    def test_symbol_renders_subscript(self):
        self.assertEqual(format_symbol("V_CE"), "V<sub>CE</sub>")
        self.assertEqual(format_symbol("I_B"), "I<sub>B</sub>")

    def test_circuit_labels_use_lab_defaults(self):
        labels = circuit_labels({})
        self.assertEqual(labels["vcc"], "12 V")
        self.assertEqual(labels["r1"], "100 kΩ")
        self.assertEqual(labels["r2"], "22 kΩ")
        self.assertEqual(labels["rc"], "2.2 kΩ")
        self.assertEqual(labels["re"], "1 kΩ")
        self.assertEqual(labels["beta"], "100")
```

- [ ] **Step 2: รันเทสให้เห็นว่า fail**

Run: `.\.venv\Scripts\python.exe -m unittest test_bjt_app.TestDisplayHelpers -v`
Expected: FAIL — `ImportError: cannot import name 'ordered_operating_point_fields'`

- [ ] **Step 3: เพิ่ม helper ใน `bjt_bias/app.py`**

```python
RESULT_ORDER = ("v_b_v", "v_e_v", "v_c_v", "v_ce_v", "i_b_a", "i_c_a", "i_e_a")


def ordered_operating_point_fields():
    by_key = {field[0]: field for field in OPERATING_POINT_FIELDS}
    return tuple(by_key[key] for key in RESULT_ORDER)


def trim_number(number):
    text = f"{number:.3f}".rstrip("0").rstrip(".")
    return "0" if text in ("", "-0") else text


def format_ohms(value):
    if abs(value) >= 1e6:
        return f"{trim_number(value / 1e6)} MΩ"
    if abs(value) >= 1e3:
        return f"{trim_number(value / 1e3)} kΩ"
    return f"{trim_number(value)} Ω"


def format_volts(value):
    return f"{trim_number(value)} V"


def format_symbol(symbol):
    head, _, tail = symbol.partition("_")
    return f"{head}<sub>{tail}</sub>"


def _default_value(spec):
    if spec["name"] in RESISTANCE_FIELDS:
        value = parse_resistance(spec["default_value"], spec["label"])
    else:
        value = parse_number(spec["default_value"], spec["label"])
    return value * unit_multiplier(spec["default_unit"])


DEFAULT_INPUTS = {spec["name"]: _default_value(spec) for spec in FIELDS}


def circuit_labels(parsed):
    inputs = {**DEFAULT_INPUTS, **parsed}
    return {
        "vcc": format_volts(inputs["vcc"]),
        "r1": format_ohms(inputs["r1"]),
        "r2": format_ohms(inputs["r2"]),
        "rc": format_ohms(inputs["rc"]),
        "re": format_ohms(inputs["re"]),
        "beta": trim_number(inputs["beta"]),
    }
```

- [ ] **Step 4: รันเทสให้ผ่าน**

Run: `.\.venv\Scripts\python.exe -m unittest test_bjt_app -v`
Expected: PASS ทุกตัว

- [ ] **Step 5: Commit**

```bash
git add bjt_bias/app.py test_bjt_app.py
git commit -m "feat: add display formatting and result ordering helpers"
```

---

### Task 4: Lab layout — template + CSS

**Files:**
- Modify: `bjt_bias/templates/index.html` (เขียนใหม่ทั้งไฟล์)
- Modify: `bjt_bias/static/style.css` (เขียนใหม่ทั้งไฟล์)
- Modify: `bjt_bias/app.py` (route context: `result_fields`, `circuit`, `vce_sat`)
- Test: `test_bjt_app.py`

**Interfaces:**
- Consumes: `ordered_operating_point_fields()`, `circuit_labels()`, `format_symbol()`, `VCE_SAT_V`
- Produces: template context เพิ่ม `result_fields`, `circuit`, `vce_sat`, `symbol_html`; คง `fields`, `errors`, `result`, `op_fields`, `fmt` เดิม

- [ ] **Step 1: เขียนเทสที่ยังไม่ผ่าน**

```python
from flask import render_template

from bjt_bias.app import (
    circuit_labels,
    create_app,
    format_symbol,
    format_value,
    ordered_operating_point_fields,
)
from bjt_bias.bias import OPERATING_POINT_FIELDS, VCE_SAT_V


class TestLabLayout(unittest.TestCase):
    def setUp(self):
        self.client = create_app().test_client()

    def test_get_shows_lab_header_and_goal_strip(self):
        body = self.client.get("/").get_data(as_text=True)
        for text in ("Lab 02: BJT DC Bias Web App", "ENG29 2121",
                     "Week 2 Goal", "<svg"):
            self.assertIn(text, body)

    def test_circuit_labels_use_default_values(self):
        body = self.client.get("/").get_data(as_text=True)
        for text in ("12 V", "100 kΩ", "22 kΩ", "2.2 kΩ", "1 kΩ"):
            self.assertIn(text, body)

    def test_results_show_voltages_before_currents(self):
        body = self.client.post("/", data=VALID_FORM).get_data(as_text=True)
        self.assertLess(body.index("V<sub>CE</sub>"), body.index("I<sub>B</sub>"))

    def test_active_banner(self):
        body = self.client.post("/", data=VALID_FORM).get_data(as_text=True)
        self.assertIn("banner-active", body)
        self.assertIn("Active region approximation OK", body)

    def test_cutoff_banner(self):
        body = self.client.post(
            "/", data={**VALID_FORM, "r2": "2.2k"}
        ).get_data(as_text=True)
        self.assertIn("banner-cutoff", body)
        self.assertIn("Cutoff", body)

    def test_saturation_banner(self):
        body = self.client.post(
            "/", data={**VALID_FORM, "rc": "10k"}
        ).get_data(as_text=True)
        self.assertIn("banner-saturation", body)
        self.assertIn("Saturation", body)

    def test_error_keeps_form_and_hides_banner(self):
        body = self.client.post(
            "/", data={**VALID_FORM, "r1": "0"}
        ).get_data(as_text=True)
        self.assertIn("greater than zero", body)
        self.assertIn('name="r1_unit"', body)
        self.assertNotIn("banner-", body)

    def test_banner_text_follows_engine_region(self):
        point = {key: 0.0 for key, *_ in OPERATING_POINT_FIELDS}
        point["v_ce_v"] = 0.2
        result = {
            "operating_point": point,
            "region": "active",
            "warnings": [],
            "verification": {
                "method1": dict(point), "method2": dict(point),
                "max_difference": 0.0, "agrees": True,
            },
        }
        app = create_app()
        with app.test_request_context("/"):
            html = render_template(
                "index.html", fields=[], errors=[], result=result,
                op_fields=OPERATING_POINT_FIELDS,
                result_fields=ordered_operating_point_fields(),
                circuit=circuit_labels({}), vce_sat=VCE_SAT_V,
                symbol_html=format_symbol, fmt=format_value,
            )
        self.assertIn("banner-active", html)
```

- [ ] **Step 2: รันเทสให้เห็นว่า fail**

Run: `.\.venv\Scripts\python.exe -m unittest test_bjt_app.TestLabLayout -v`
Expected: FAIL — ไม่พบ "Lab 02: BJT DC Bias Web App"

- [ ] **Step 3: เขียน template และ CSS ใหม่ + ต่อ context**

Template ต้องมี (ข้อความ/คลาสตามนี้เป๊ะ):

- `<header class="lab-header">` — `<h1>Lab 02: BJT DC Bias Web App</h1>`, `<p class="lab-subtitle">ENG29 2121 – Common Emitter (Voltage Divider Bias)</p>`, `<div class="course-badge">Computer Programming for Electrical Engineers</div>`, ไอคอนชิป inline SVG
- `<div class="layout">` — สาม `<section class="panel panel-input|panel-circuit|panel-results">`
- Input panel: `<form method="post">` 7 แถว (display, description, input, select), ปุ่ม `Calculate DC Bias`, และ `{% if errors %}<section class="errors" role="alert">` อยู่ใน panel นี้
- Circuit panel: `<svg class="schematic">` วาด VCC rail, R1, R2, RC, RE, Q1 NPN, ground; `<text>` ใช้ `{{ circuit.vcc }}`, `{{ circuit.r1 }}`, `{{ circuit.r2 }}`, `{{ circuit.rc }}`, `{{ circuit.re }}`, `β = {{ circuit.beta }}`
- Results panel: `{% if result %}` `<table class="results">` วน `result_fields` แสดง `{{ symbol_html(symbol)|safe }}` (ได้ `V<sub>CE</sub>`) และค่า `{{ fmt(result.operating_point[key], scale) }} {{ unit }}`; ถ้าไม่มี result แสดงข้อความ `Enter parameters and press Calculate`
- Banner ใน results panel: `<div class="banner banner-{{ result.region }}">` — active: `Active region approximation OK` + `V_CE = {{ fmt(result.operating_point.v_ce_v, 1.0) }} V > {{ vce_sat }} V (transistor in active region)`; cutoff: `Cutoff region` + `I_B ≤ 0 — transistor is off; V_CE = VCC`; saturation: `Saturation region` + `V_CE = … V < {{ vce_sat }} V — active-mode equations are not valid`
- Warnings section (เดิม) ใต้ results
- `<details class="verification" open>` — `<summary>Verification: Method 1 vs Method 2 — PASS|FAIL</summary>` + ตารางเดิม (ใช้ `op_fields` และ `fmt`; ส่วนต่างคูณ `scale` แล้ว)
- `<footer class="goal-strip">` — `<strong>Week 2 Goal</strong>` + `Build a Flask web app that takes the circuit parameters, computes the BJT DC bias (V_B, V_E, V_C, V_CE, I_B, I_C, I_E) for a common-emitter amplifier with voltage-divider bias, and displays the results.`

route: import `VCE_SAT_V` จาก `bjt_bias.bias`; ส่ง `result_fields=ordered_operating_point_fields()`, `circuit=circuit_labels(parsed)`, `vce_sat=VCE_SAT_V`, `symbol_html=format_symbol` ทั้ง GET และ POST (GET ใช้ `parsed=dict(DEFAULT_INPUTS)`)

CSS: palette ใกล้ mockup — พื้นหลัง `#eef4f8`, panel ขาว `border-radius: 12px`, accent teal `#0f7c8a`, badge น้ำเงินอ่อน, banner เขียว/เหลือง/แดง; 3 คอลัมน์ด้วย `grid-template-columns: 1fr 1.15fr 1fr`; `@media (max-width: 900px)` ยุบเป็น 1 คอลัมน์; ตัวอักษร system-ui

- [ ] **Step 4: รันเทสให้ผ่าน**

Run: `.\.venv\Scripts\python.exe -m unittest discover -v`
Expected: PASS ทุกตัว

- [ ] **Step 5: Commit**

```bash
git add bjt_bias/app.py bjt_bias/templates/index.html bjt_bias/static/style.css test_bjt_app.py
git commit -m "feat: rebuild the bias page as the Lab 02 layout"
```

---

### Task 5: Live run + docs

**Files:**
- Modify: `bjt_bias/README.md`

**Interfaces:**
- Consumes: ทุกอย่างจาก Task 1–4

- [ ] **Step 1: อัปเดต `bjt_bias/README.md`**

เพิ่มหัวข้อสั้น ๆ ว่า: หน้า `/` เป็น layout Lab 02 (Input / Circuit / Results), ตัวต้านทานเลือกหน่วย Ω/kΩ/MΩ ได้, ตัวเลขบนวงจรเป็นค่าที่กรอก, ผลลัพธ์เรียง V ก่อน I, banner ตาม region, verification อยู่ใน `<details>`

- [ ] **Step 2: รันเทสทั้งหมด**

Run: `.\.venv\Scripts\python.exe -m unittest discover -v`
Expected: PASS (43 + เทสใหม่)

- [ ] **Step 3: รัน server จริงและยิง request จริง**

```powershell
Start-Process -FilePath ".\.venv\Scripts\python.exe" -ArgumentList "-m","bjt_bias.app" -WindowStyle Hidden
Start-Sleep -Seconds 4
$p = Invoke-WebRequest -Uri "http://127.0.0.1:5000/" -Method POST -Body @{vcc="12";r1="100";r1_unit="kohm";r2="22";r2_unit="kohm";rc="2.2";rc_unit="kohm";re="1";re_unit="kohm";beta="100";vbe="0.7"} -UseBasicParsing
$t = ($p.Content -replace '<[^>]+>',' ') -replace '\s+',' '
$t.Substring($t.IndexOf('DC Bias Results'), 260)
```

Expected: `V_B 1.942 V`, `V_E 1.242 V`, `V_C 9.294 V`, `V_CE 8.052 V`, `I_B 12.299 µA`, `I_C 1.230 mA`, `I_E 1.242 mA`, banner active

- [ ] **Step 4: หยุด server**

```powershell
Get-Process python -ErrorAction SilentlyContinue | Where-Object { $_.Path -like "*\.venv\*" } | Stop-Process -Force
```

- [ ] **Step 5: Commit**

```bash
git add bjt_bias/README.md
git commit -m "docs: describe the Lab 02 page layout"
```

---

## Self-Review

- Spec §2 ทุกข้อมี task รองรับ: header/3 คอลัมน์ → Task 4, unit selector → Task 1–2, circuit label → Task 3–4, results order → Task 3–4, banner → Task 4, verification → Task 4, เทสเดิม + เทสใหม่ → ทุก task
- Spec §4 "POST ไม่มี unit key" → Task 1 (default 1) และ Review Focus 2
- Spec §6 builder calls ครบ: Ω/kΩ/MΩ, V, –, default ชุดแล็บ, SVG label จากค่าที่กรอก, display order, `<details open>`, error ใน input panel, responsive 900px
- ชื่อ/ชนิดข้อมูลตรงกันทุก task: `unit_multiplier`, `_read_form` 4-tuple, `_form_fields(values, units)`, `ordered_operating_point_fields`, `circuit_labels`, `DEFAULT_INPUTS`, `format_symbol`/`symbol_html`
- Review Focus ทั้ง 5 ข้อมีเทสใน task ที่รับผิดชอบ (ข้อ 4 ใช้เทส boundary เดิมใน `test_bjt_bias` + synthetic render ใน Task 4)
