# Lab 03 Bias Modes Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** เพิ่มโหมด Fixed Bias และ Emitter Bias ให้เว็บ Flask เดิม โดยผลของ Voltage Divider ต้องไม่เปลี่ยน

**Architecture:** สมการใหม่อยู่ใน `bjt_bias/bias.py` เป็นฟังก์ชันบริสุทธิ์ที่คืน dict คีย์เดิม 7 ตัว; `bjt_bias/app.py` เลือกโมเดลด้วย `if/elif` จากค่า `mode` ในฟอร์ม, parse เฉพาะช่องของโหมดนั้น, แล้วส่งเข้าเทมเพลตเดียวกันซึ่งแสดงเฉพาะช่องและไดอะแกรมของโหมดที่เลือก

**Tech Stack:** Python 3.14, Flask 3.1.3, Jinja2 templates, `unittest` เดิม

**Spec:** `docs/superpowers/specs/2026-11-17-bjt-bias-modes-design.md`

## Global Constraints

- `requirements.txt` ต้องเหลือ `Flask==3.1.3` อย่างเดียว — ห้ามเพิ่ม dependency
- ห้ามแก้ `analyze_bias`, `solve_method1`, `solve_method2`, `classify_region`, `cutoff_operating_point`
- **ห้ามเขียน unittest ใหม่** — เทสเดิม 62 ตัวต้องผ่านทั้งหมด และใช้ script ชั่วคราวนอก repo สำหรับตรวจผล (ใบงานสั่งให้ตรวจผ่าน browser)
- คีย์ผลลัพธ์ทุกโหมด: `v_b_v, v_e_v, v_c_v, v_ce_v, i_b_a, i_c_a, i_e_a`
- หน่วย SI ภายใน engine; การแปลงหน่วยเกิดที่ `_read_form` จุดเดียว
- `mode` ที่หายไปจาก POST = `divider` (เทสเดิมและ curl ต้องไม่พัง)
- `mode` ที่ไม่รู้จัก = error ห้ามเดาเป็น divider
- ค่าคงที่: `VCC = 12 V`, `RC = 2.2 kΩ`, `β = 100`, `VBE = 0.70 V`, `VCE_SAT_V = 0.2`
- ค่าอ้างอิงที่คำนวณมือ (ใช้ตรวจทุก task): A1 `1.2298 mA / 8.0522 V`, A2 `1.1300 mA / 9.5140 V`, A3 `1.0263 mA / 8.7054 V`, A4 `0.9401 mA / 8.0328 V`

## Review Focus

1. POST ที่ไม่มี `mode` (curl / เทสเดิม) ต้องได้ผล Divider เดิมเป๊ะ รวมถึงแผง verification
2. `mode` ที่ไม่รู้จักต้องขึ้น error และไม่คำนวณอะไรเลย
3. ค่าของช่องที่โหมดนั้นไม่ใช้ (เช่น `re` ค้างจากรอบ Divider) ต้องไม่หลุดเข้า engine หรือไดอะแกรมของโหมด Fixed
4. `RB = 0` ต้องขึ้น error ที่ระบุ RB, ไม่มีผลลัพธ์ค้าง, และหน้ายังเรนเดอร์ครบ
5. โหมดใหม่ที่ได้ `I_B ≤ 0` หรือ `V_CE ≤ 0.2 V` ต้องเตือนและยังโชว์ค่าจากสมการ (ไม่แทนด้วยค่า Cutoff/Saturation)

---

### Task 1: Engine — Fixed และ Emitter

**Files:**
- Modify: `bjt_bias/bias.py` (ต่อท้ายไฟล์ ก่อน `analyze_bias` ไม่ต้องย้ายของเดิม)
- Verify: script ชั่วคราว `%TEMP%\opencode\lab03_check_engine.py` (ไม่ commit)

**Interfaces:**
- Consumes: `_positive_number`, `_finite_number`, `VCE_SAT_V`, `VBE_PLAUSIBLE_RANGE_V`
- Produces:
  - `solve_fixed_bias(vcc, rb, rc, beta, vbe) -> dict[str, float]` — 7 คีย์เดิม
  - `solve_emitter_bias(vcc, rb, re, rc, beta, vbe) -> dict[str, float]` — 7 คีย์เดิม
  - `analyze_fixed_bias(vcc, rb, rc, beta, vbe) -> dict` — `{"operating_point", "region", "warnings", "verification": None}`
  - `analyze_emitter_bias(vcc, rb, re, rc, beta, vbe) -> dict` — รูปเดียวกัน

- [ ] **Step 1: เขียน script ตรวจ (ยังไม่ผ่าน)**

`%TEMP%\opencode\lab03_check_engine.py`:

```python
from bjt_bias.bias import analyze_emitter_bias, analyze_fixed_bias

fixed = analyze_fixed_bias(12, 1e6, 2200, 100, 0.7)
assert abs(fixed["operating_point"]["i_c_a"] * 1e3 - 1.1300) < 0.01
assert abs(fixed["operating_point"]["v_ce_v"] - 9.5140) < 0.02
assert fixed["operating_point"]["v_e_v"] == 0.0
assert fixed["verification"] is None
assert fixed["region"] == "active"

emitter = analyze_emitter_bias(12, 1e6, 1000, 2200, 100, 0.7)
assert abs(emitter["operating_point"]["i_c_a"] * 1e3 - 1.0263) < 0.01
assert abs(emitter["operating_point"]["v_ce_v"] - 8.7054) < 0.02

emitter2 = analyze_emitter_bias(12, 1e6, 2000, 2200, 100, 0.7)
assert emitter2["operating_point"]["i_c_a"] < emitter["operating_point"]["i_c_a"]

sat = analyze_fixed_bias(12, 1e6, 1e6, 100, 0.7)
assert sat["region"] == "saturation"
assert any("may not be valid" in w for w in sat["warnings"])
# ค่าจากสมการต้องไม่ถูกแทนด้วยค่า saturation
assert sat["operating_point"]["v_c_v"] == 12 - 1.13e-3 * 1e6
print("engine OK", sat["region"], sat["warnings"])
```

- [ ] **Step 2: รันให้เห็นว่ายังไม่ผ่าน**

Run: `$env:PYTHONPATH = "C:\Phatcharakan\GitLab1"; .\.venv\Scripts\python.exe "$env:TEMP\opencode\lab03_check_engine.py"`
Expected: `ImportError: cannot import name 'analyze_fixed_bias'`

- [ ] **Step 3: เขียน implementation**

เพิ่มใน `bjt_bias/bias.py` — `solve_*` คืน dict 7 คีย์, `_forward_active_result(operating_point, vbe)` ตัดสิน region (`cutoff` ถ้า `i_b_a <= 0`, `saturation` ถ้า `v_ce_v <= VCE_SAT_V`, ไม่งั้น `active`), ใส่ warning "forward-active model may not be valid" เมื่อไม่ใช่ active และ warning ช่วง VBE จาก `VBE_PLAUSIBLE_RANGE_V`, `analyze_*` validate ด้วย `_positive_number`/`_finite_number` + กติกา `0 <= VBE < VCC` แล้วคืนผลโดย **ไม่แทนที่** operating point

- [ ] **Step 4: รัน script ให้ผ่าน**

Run: same as Step 2
Expected: `engine OK saturation [...]`

- [ ] **Step 5: รันเทสเดิมทั้งชุด**

Run: `.\.venv\Scripts\python.exe -m unittest discover`
Expected: `Ran 62 tests ... OK`

- [ ] **Step 6: Commit**

```bash
git add bjt_bias/bias.py
git commit -m "feat: add fixed and emitter bias equations"
```

---

### Task 2: Route — mode, ช่อง RB, และการตรวจอินพุตตามโหมด

**Files:**
- Modify: `bjt_bias/app.py` (`FIELDS`, `MODES`, `_form_fields`, `_read_form`, `circuit_labels`, `page_context`, `create_app`)
- Verify: script ชั่วคราว `%TEMP%\opencode\lab03_check_app.py` (ไม่ commit)

**Interfaces:**
- Consumes: `analyze_fixed_bias`, `analyze_emitter_bias` (Task 1), `analyze_bias`
- Produces:
  - `MODES: dict[str, dict]` — key `divider|fixed|emitter`, value `{"label": str, "fields": tuple[str, ...]}`
  - `DEFAULT_MODE = "divider"`
  - `FIELDS` แต่ละรายการมี key `modes: tuple[str, ...]` เพิ่ม และมี field ใหม่ `rb`
  - `_form_fields(values, units, mode) -> list[dict]`
  - `_read_form(form, mode) -> tuple[dict, dict, dict, list[str]]`
  - `circuit_labels(parsed, mode) -> dict[str, str]` — คีย์ `vcc, rc, beta` เสมอ; `r1, r2, re` เมื่อ divider; `rb` เมื่อ fixed/emitter; `re` เมื่อ emitter
  - `page_context(...)` เพิ่ม `mode`, `mode_label`, `mode_options`

- [ ] **Step 1: เขียน script ตรวจ (ยังไม่ผ่าน)**

`%TEMP%\opencode\lab03_check_app.py`:

```python
from bjt_bias.app import create_app

client = create_app().test_client()
base = {"vcc": "12", "rc": "2.2", "rc_unit": "kohm", "beta": "100", "vbe": "0.7"}

# A2 fixed
fixed = client.post("/", data={**base, "mode": "fixed", "rb": "1", "rb_unit": "mohm"}).get_data(as_text=True)
assert "Fixed Bias" in fixed and 'name="rb"' in fixed
assert 'name="r1"' not in fixed and 'name="re"' not in fixed
assert "1.130 mA" in fixed and "9.514 V" in fixed

# A3 emitter
emit = client.post("/", data={**base, "mode": "emitter", "rb": "1", "rb_unit": "mohm",
                              "re": "1", "re_unit": "kohm"}).get_data(as_text=True)
assert "Emitter Bias" in emit and "1.026 mA" in emit and "8.705 V" in emit

# A5 fixed RB=0
zero = client.post("/", data={**base, "mode": "fixed", "rb": "0", "rb_unit": "kohm"})
assert zero.status_code == 200
assert "RB" in zero.get_data(as_text=True)

# old form, no mode -> divider unchanged
old = client.post("/", data={"vcc": "12", "r1": "100", "r1_unit": "kohm", "r2": "22",
                             "r2_unit": "kohm", "rc": "2.2", "rc_unit": "kohm",
                             "re": "1", "re_unit": "kohm", "beta": "100", "vbe": "0.7"})
assert "1.230 mA" in old.get_data(as_text=True)

# unknown mode -> error, no compute
bad = client.post("/", data={**base, "mode": "class-a", "rb": "1", "rb_unit": "mohm"}).get_data(as_text=True)
assert "Unknown bias mode" in bad and "1.130 mA" not in bad

print("app OK")
```

- [ ] **Step 2: รันให้เห็นว่ายังไม่ผ่าน**

Run: `$env:PYTHONPATH = "C:\Phatcharakan\GitLab1"; .\.venv\Scripts\python.exe "$env:TEMP\opencode\lab03_check_app.py"`
Expected: AssertionError ตัวแรก (ยังไม่มี `mode` / `rb`)

- [ ] **Step 3: แก้ `bjt_bias/app.py`**

ทำตาม Interfaces: เพิ่ม field `rb` (Ω/kΩ/MΩ, default `1` `mohm`), ใส่ `modes` ให้ทุก field, เพิ่ม `MODES`/`DEFAULT_MODE`, `_resolve_mode(raw)` คืน `(mode, error)`, ให้ `_read_form` วนเฉพาะ field ของโหมด, ให้ `_analyze(mode, parsed)` ใช้ `if/elif` และ raise `ValueError(f"Unknown bias mode: {raw!r}.")` สำหรับโหมดที่ไม่รู้จัก, `page_context` ส่ง `mode`/`mode_label`/`mode_options`

- [ ] **Step 4: รัน script ให้ผ่าน**

Run: same as Step 2
Expected: `app OK`

- [ ] **Step 5: รันเทสเดิมทั้งชุด**

Run: `.\.venv\Scripts\python.exe -m unittest discover`
Expected: `Ran 62 tests ... OK`

- [ ] **Step 6: Commit**

```bash
git add bjt_bias/app.py
git commit -m "feat: select bias mode and validate per-mode inputs"
```

---

### Task 3: Template + CSS — แถบเลือกโหมด, ไดอะแกรมตามโหมด, หัวข้อระบุโหมด

**Files:**
- Modify: `bjt_bias/templates/index.html`
- Modify: `bjt_bias/static/style.css`

**Interfaces:**
- Consumes: `mode`, `mode_label`, `mode_options`, `fields`, `circuit` (Task 2)
- Produces: ไม่มี Python interface ใหม่ — เทมเพลตต้องเรนเดอร์ได้ทั้ง GET และ POST

- [ ] **Step 1: เขียน script ตรวจ (ยังไม่ผ่าน)**

`%TEMP%\opencode\lab03_check_ui.py`:

```python
from bjt_bias.app import create_app

client = create_app().test_client()
get = client.get("/").get_data(as_text=True)
assert 'name="mode"' in get and "Voltage Divider Bias" in get
assert 'value="divider"' in get or "selected" in get

fixed = client.post("/", data={"mode": "fixed", "vcc": "12", "rc": "2.2", "rc_unit": "kohm",
                               "beta": "100", "vbe": "0.7", "rb": "1", "rb_unit": "mohm"}).get_data(as_text=True)
assert "DC Bias Results &mdash; Fixed Bias" in fixed or "DC Bias Results — Fixed Bias" in fixed
assert 'name="mode" value="fixed"' in fixed
assert "R<sub>B</sub>" in fixed and "R<sub>1</sub>" not in fixed
assert "Verification: Method 1 vs Method 2" not in fixed
assert "banner-active" in fixed

divider = client.post("/", data={"vcc": "12", "r1": "100", "r1_unit": "kohm", "r2": "22",
                                 "r2_unit": "kohm", "rc": "2.2", "rc_unit": "kohm",
                                 "re": "1", "re_unit": "kohm", "beta": "100",
                                 "vbe": "0.7"}).get_data(as_text=True)
assert "Verification: Method 1 vs Method 2" in divider

bad = client.post("/", data={"mode": "fixed", "vcc": "12", "rc": "2.2", "beta": "100",
                             "vbe": "0.7", "rb": "0", "rb_unit": "kohm"}).get_data(as_text=True)
assert "Invalid input (Fixed Bias)" in bad and "banner-" not in bad

print("ui OK")
```

- [ ] **Step 2: รันให้เห็นว่ายังไม่ผ่าน**

Run: `$env:PYTHONPATH = "C:\Phatcharakan\GitLab1"; .\.venv\Scripts\python.exe "$env:TEMP\opencode\lab03_check_ui.py"`
Expected: AssertionError เรื่อง `DC Bias Results — Fixed Bias`

- [ ] **Step 3: แก้เทมเพลต**

- แถบ `<form method="get" class="mode-bar">` เหนือฟอร์มค่า: `<select name="mode">` จาก `mode_options` + ปุ่ม `Load form`
- ฟอร์มค่าเพิ่ม `<input type="hidden" name="mode" value="{{ mode }}">`
- หัวข้อผลลัพธ์ `DC Bias Results &mdash; {{ mode_label }}`
- กล่อง error `Invalid input ({{ mode_label }})`
- ไดอะแกรม SVG เดียวแต่มีเงื่อนไข: `divider` วาด R1+R2, `fixed`/`emitter` วาด RB ตัวเดียว; RE วาดเมื่อ `mode != 'fixed'` (โหมด fixed ต่อ emitter ลงกราวด์ตรง ๆ)
- `<details class="verification">` แสดงเฉพาะเมื่อ `result.verification`

- [ ] **Step 4: เพิ่ม CSS**

`.mode-bar` (flex, label + select + ปุ่ม), `.mode-bar select`, `.mode-bar button` (กว้างพอดี ไม่เต็มแถว) ตาม palette เดิม — ห้ามแก้สไตล์เดิม

- [ ] **Step 5: รัน script ให้ผ่าน**

Run: same as Step 2
Expected: `ui OK`

- [ ] **Step 6: รันเทสเดิมทั้งชุด**

Run: `.\.venv\Scripts\python.exe -m unittest discover`
Expected: `Ran 62 tests ... OK`

- [ ] **Step 7: Commit**

```bash
git add bjt_bias/templates/index.html bjt_bias/static/style.css
git commit -m "feat: add mode selector and per-mode schematic"
```

---

### Task 4: เอกสาร, README, และ config ของ Playwright MCP

**Files:**
- Create: `docs/validation.md`
- Create: `opencode.json`
- Modify: `bjt_bias/README.md`

**Interfaces:**
- Consumes: ค่าอ้างอิงใน Global Constraints
- Produces: ตาราง A1–A5 ที่ Task 5 เติมคอลัมน์ "เห็นจริง"

- [ ] **Step 1: เขียน `docs/validation.md`**

ตารางคอลัมน์: `กรณี | เลือกโหมดและกรอกค่า | คาดหมายก่อนรัน | เห็นจริง | วิธีตรวจ | สถานะ` — เติม "คาดหมาย" ตาม Global Constraints พร้อม arithmetic ของแต่ละกรณี และหมายเหตุ A4 ว่า IC ต้องลดลง

- [ ] **Step 2: เขียน `opencode.json`**

```json
{
  "$schema": "https://opencode.ai/config.json",
  "mcp": {
    "servers": {
      "playwright": {
        "type": "local",
        "command": ["npx", "-y", "@playwright/mcp@latest", "--browser", "chrome", "--isolated"]
      }
    }
  }
}
```

- [ ] **Step 3: อัปเดต `bjt_bias/README.md`**

เพิ่มหัวข้อโหมดทั้งสาม, ช่องที่แต่ละโหมดใช้, และที่มาของสมการ

- [ ] **Step 4: ตรวจว่า JSON ถูกต้องและเทสยังผ่าน**

Run: `.\.venv\Scripts\python.exe -c "import json;json.load(open('opencode.json'))"` และ `.\.venv\Scripts\python.exe -m unittest discover`
Expected: ไม่มี output จากคำสั่งแรก, `Ran 62 tests ... OK`

- [ ] **Step 5: Commit**

```bash
git add docs/validation.md opencode.json bjt_bias/README.md
git commit -m "docs: record lab 03 modes and acceptance table"
```

---

### Task 5: Browser acceptance A1–A5

**Files:**
- Modify: `docs/validation.md` (คอลัมน์ "เห็นจริง", "วิธีตรวจ", "สถานะ")

**Interfaces:**
- Consumes: หน้าเว็บจาก Task 3, ตารางจาก Task 4
- Produces: หลักฐาน A1–A5 พร้อม screenshot อย่างน้อยหนึ่งกรณี

- [ ] **Step 1: ตรวจความพร้อมของ Playwright MCP**

Run: `node --version` และ `npx --version`
Expected: มีเลขรุ่นทั้งคู่ ถ้าไม่มี → บันทึก Playwright MCP เป็น **NOT RUN** พร้อมเหตุผล แล้วหยุด task นี้

- [ ] **Step 2: รัน Flask**

Run: `.\.venv\Scripts\python.exe -m bjt_bias.app` (เปิดค้างไว้)
Expected: เปิด `http://127.0.0.1:5000/` ได้

- [ ] **Step 3: ตรวจ A1–A5 ผ่าน browser**

ทำทีละกรณีตามตาราง: navigate → snapshot → เลือกโหมด → กรอกค่าตามหน่วยบนฟอร์ม → คลิก Calculate → snapshot ใหม่ → เก็บค่าที่เห็น ถ้าเปลี่ยนโหมดต้องอ่าน snapshot ใหม่ก่อนกรอก

- [ ] **Step 4: เติมตาราง**

ระบุ `วิธีตรวจ = Playwright MCP`, ค่าที่เห็นพร้อมหน่วย, สถานะ PASS/FAIL/NOT RUN และแนบ screenshot อย่างน้อยหนึ่งกรณี

- [ ] **Step 5: Commit**

```bash
git add docs/validation.md
git commit -m "docs: record lab 03 browser acceptance results"
```
