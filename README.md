# DC Circuit Calculator

วัตถุประสงค์: โปรแกรมคำนวณและวิเคราะห์วงจรไฟฟ้ากระแสตรง (DC) แบบอนุกรม ขนาน และผสม โดยผู้ใช้เพียงระบุค่าความต่างศักย์และแรงต้านทาน ระบบจะคำนวณหาค่ากระแสไฟฟ้ารวม (Current) และกำลังไฟฟ้า (Power) ของแต่ละอุปกรณ์ให้อัตโนมัติ เพื่อช่วยให้ผู้เรียนเข้าใจกฎของโอมห์และวิเคราะห์วงจรได้อย่างแม่นยำ

## BJT Common-Emitter DC Bias — Flask web app (Lab 2–3)

เว็บแอป Flask สำหรับคำนวณ DC operating point ของ BJT common-emitter
รองรับ **3 โหมดไบแอส**: Voltage Divider Bias (ของเดิมจาก Lab 2), Fixed Bias
และ Emitter Bias (เพิ่มใน Lab 3)

- **GitHub:** <https://github.com/pleng4995-cloud/Git-Lab>
- **Commit SHA ของงาน Lab 3:** [`de871dc`](https://github.com/pleng4995-cloud/Git-Lab/commit/de871dccca5f3b9368640ed85cb8057c0e74310a)
  (`de871dccca5f3b9368640ed85cb8057c0e74310a`)
- **ตารางตรวจรับ A1–A5 + หลักฐานจากหน้าเว็บ:** [`docs/validation.md`](docs/validation.md)

### วิธีรัน

ต้องมี Python 3 และติดตั้ง dependency (มีแค่ Flask)

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
```

วิธีที่แนะนำ — ดับเบิลคลิก `start.bat` (ใช้ `.venv` ให้เอง เปิดเซิร์ฟเวอร์ใน
หน้าต่างแยก แล้วเปิดเบราว์เซอร์ที่ <http://127.0.0.1:5000>)
หยุดเซิร์ฟเวอร์ด้วย `stop.bat`

หรือรันเองใน PowerShell:

```powershell
.\.venv\Scripts\python.exe -m bjt_bias.app
```

แล้วเปิด <http://127.0.0.1:5000> — terminal ต้องเปิดค้างไว้ตลอดที่ใช้งาน

> ถ้าเรียก `python -m bjt_bias.app` เฉย ๆ จะได้
> `ModuleNotFoundError: No module named 'flask'` เพราะ Flask อยู่ใน `.venv`
> ต้องเรียกผ่าน `.\.venv\Scripts\python.exe`

### โหมดที่รองรับ

| โหมด | ช่องที่ใช้ | สมการ IB |
|---|---|---|
| Voltage Divider Bias | VCC, R1, R2, RC, RE, β, VBE | `(VTH − VBE) / [RTH + (β+1)·RE]` |
| Fixed Bias | VCC, RB, RC, β, VBE | `(VCC − VBE) / RB` |
| Emitter Bias | VCC, RB, RE, RC, β, VBE | `(VCC − VBE) / [RB + (β+1)·RE]` |

จาก IB: `IC = β·IB`, `IE = (β+1)·IB`, `VE = IE·RE` (Fixed ใช้ `VE = 0`),
`VB = VE + VBE`, `VC = VCC − IC·RC`, `VCE = VC − VE`
รายละเอียดเพิ่มเติม: [`bjt_bias/README.md`](bjt_bias/README.md)

### ค่าอ้างอิงอิสระ (คำนวณมือ ไม่ได้มาจากโปรแกรม)

VCC = 12 V, RC = 2.2 kΩ, β = 100, VBE = 0.70 V

| กรณี | สมการ | ค่าอ้างอิง |
|---|---|---|
| Fixed, RB = 1 MΩ | `IB = (12 − 0.70) / 1 MΩ = 11.3 µA` → `IC = 1.1300 mA`, `VC = 12 − 1.13 mA × 2.2 kΩ = 9.5140 V` | IC = 1.1300 mA, VCE = 9.5140 V |
| Emitter, RB = 1 MΩ, RE = 1 kΩ | `IB = 11.3 / (1 MΩ + 101 × 1 kΩ) = 10.2634 µA` → `IC = 1.02634 mA`, `VE = 1.0366 V`, `VCE = 8.70545 V` | IC = 1.0263 mA, VCE = 8.7054 V |

arithmetic เต็มของ A1–A5 อยู่ใน [`docs/validation.md`](docs/validation.md)

### AI ช่วยสร้างส่วนไหน และนักศึกษาตรวจอะไร

**AI (OpenCode) เขียน:**

- `bjt_bias/bias.py` — `solve_fixed_bias`, `solve_emitter_bias`,
  `analyze_fixed_bias`, `analyze_emitter_bias`, `_validate_common_inputs`,
  `_forward_active_result` (สมการตามใบงาน, คืน dict 7 คีย์เดิม)
- `bjt_bias/app.py` — `MODES`/`MODE_LABELS`, `_resolve_mode`, `_mode_fields`,
  `_read_form(form, mode)`, `_analyze` (if/elif เลือกโมเดล), `page_context`
- `bjt_bias/templates/index.html`, `bjt_bias/static/style.css` — แถบเลือกโหมด,
  ไดอะแกรม SVG ตามโหมด, หัวข้อ/error ที่ระบุโหมด
- `start.bat`, `stop.bat`, `scripts/browser_acceptance.py`, เอกสาร `docs/`

**นักศึกษาตรวจ:**

- รันแอปและเปลี่ยนโหมดทั้งสามด้วยตัวเอง แล้วแจ้งข้อผิดพลาดที่พบ
  (ไดอะแกรมไม่เปลี่ยนตามโหมด, เปิด Flask ไม่ได้) ซึ่งนำไปสู่การแก้ไข
- ตรวจว่าผลของโหมด Divider ยังเท่าเดิมกับ Lab 2 (A1: 1.230 mA / 8.052 V)
  และชุดเทสเดิม 62 ตัวยังผ่าน
- ทวนผลเองอย่างน้อย 1 กรณี — บันทึกในหัวข้อ "ทวนเองโดยนักศึกษา"
  ของ [`docs/validation.md`](docs/validation.md)

**โค้ดเลือกฟังก์ชันตามโหมด:** `bjt_bias/app.py`

- `_resolve_mode()` อ่านค่า `mode` จาก request (หาย → `divider`, ไม่รู้จัก → error)
- `_analyze()` ใช้ `if/elif` เรียก `analyze_bias` / `analyze_fixed_bias` /
  `analyze_emitter_bias`

**โค้ดแปลงหน่วย:** `bjt_bias/app.py` ฟังก์ชัน `_read_form()` — แปลงค่าที่กรอก
(Ω / kΩ / MΩ) เป็น SI (โอห์ม, โวลต์) ด้วย `multiplier` **ที่จุดเดียว**
แล้วส่งเข้า engine; engine ทำงานเป็น SI ทั้งหมด

---

## Lab 04 — CE Voltage-Divider Simulator (SPICE)

ต่อยอด Lab 03 ด้วยการรัน **ngspice จริง** (`.op` / `.ac` / `.tran`) เฉพาะวงจร
CE Voltage Divider v1 ผลที่ได้แสดงคนละป้ายกับ Analytical เสมอ

- **GitHub:** <https://github.com/pleng4995-cloud/Git-Lab.git>
- **Commit SHA ของ Lab 04 (โค้ด + หลักฐาน):**
  [`2c41279`](https://github.com/pleng4995-cloud/Git-Lab/commit/2c4127930ce498af9ddf1d6b5df4a55d722495a1)
  (`2c4127930ce498af9ddf1d6b5df4a55d722495a1`)
- **ตารางตรวจรับ A1–A5 (Lab 03) และ B1–B8 (Lab 04) + หลักฐานจากหน้าเว็บ:**
  [`docs/validation.md`](docs/validation.md)
- **กฎการแก้โค้ด/การส่งงาน:** [`AGENTS.md`](AGENTS.md)
- **ที่มาและวิธีเปลี่ยน BJT model:**
  [`bjt_bias/spice_models/README.md`](bjt_bias/spice_models/README.md)

### ติดตั้ง engine

Dependency ของ Python **ยังมีแค่ Flask** (`requirements.txt`) — ngspice เป็น
โปรแกรมแยก ติดตั้ง portable ไว้นอก repo ได้ด้วย:

```powershell
powershell -ExecutionPolicy Bypass -File scripts\fetch_ngspice.ps1
```

สคริปต์ดาวน์โหลด ngspice-47 ไปที่ `C:\Tools\ngspice-47` (ไม่เขียนอะไรใน repo)
โปรแกรมจะหา `ngspice_con.exe` จาก path นั้นเอง หรือตั้ง `NGSPICE_BIN` ให้ชี้
full path ก็ได้:

```powershell
$env:NGSPICE_BIN = 'C:\Tools\ngspice-47\bin\ngspice_con.exe'
.\.venv\Scripts\python.exe -m bjt_bias.app
```

`NGSPICE_BIN` ที่ตั้งค่าจะเป็น **authoritative** — ถ้าชี้ path ที่ไม่มีอยู่
หน้าเว็บจะขึ้น engine bar สีแดง `ngspice not found` พร้อมวิธีติดตั้ง และ
**ไม่แสดงค่า/กราฟ SPICE** (ไม่มี fallback แบบเงียบ ๆ) Analytical DC ยังใช้ได้
ทุกโหมดแม้ไม่มี ngspice

รันเซิร์ฟเวอร์เหมือนเดิม (`start.bat` หรือ
`.\.venv\Scripts\python.exe -m bjt_bias.app`) แล้วเปิด <http://127.0.0.1:5000>
→ เลือก **Voltage Divider Bias**
จะเห็นแถบ engine status, ช่อง source/sweep และปุ่ม Run เพิ่มขึ้น

### ปุ่ม analysis

| ปุ่ม | ค่า `analysis` | การทำงาน | ผลที่แสดง |
|---|---|---|---|
| Calculate DC Bias | `analytical` (default ถ้าไม่ส่งฟิลด์นี้) | `bjt_bias/bias.py` เท่านั้น ไม่เรียก ngspice | ตาราง Lab 03 เดิม + badge `ANALYTICAL · bias.py` |
| Run SPICE DC | `dc` | netlist `.op` | ตารางเปรียบเทียบ Analytical / SPICE / Δ + model + run id |
| Run AC sweep | `ac` | netlist `.ac dec` 10 Hz–1 MHz, 20 pts/dec | กราฟ Bode (gain dB + phase deg,แกน Hz log) |
| Run Transient | `tran` | netlist `.tran` ตาม amplitude/frequency ที่กรอก | กราฟ Vin/Vout (ms / mV) |

สามปุ่มหลังปรากฏเฉพาะโหมด Divider; โหมด Fixed/Emitter ยังคำนวณ analytical
ได้ตามเดิม ฐานข้อมูลวงจร v1: VCC 12 V, R1 100 kΩ, R2 22 kΩ, RC 2.2 kΩ,
RE 1 kΩ, RL 10 kΩ, Cin/Cout 10 µF, source 10 mV peak @ 1 kHz, **ไม่มี emitter
bypass capacitor** — จุดวัด Vin = โหนด `vin` ฝั่งแหล่งสัญญาณก่อน Cin,
Vout = โหนด `out` หลัง Cout คร่อม RL

กราฟถูกสร้างเป็น SVG จากผลรันจริงฝั่ง Python (`bjt_bias/plots.py`) ไม่ได้เพิ่ม
JavaScript/dependency และไม่มี curve hard-code ทุก request ที่ status ไม่ใช่
`ok` จะไม่มีค่าหรือกราฟ SPICE

ตัวอย่างไฟล์กราฟจากการรันจริง (run ใหม่ แยกจาก B4/B5; รายละเอียดและ run id
อยู่ใน [`docs/validation.md`](docs/validation.md#ไฟล์-simulation--plots-รันใหม่-แยกจาก-b4b5)):

- [Bode — SVG](docs/evidence/lab4/simulation-ac.svg) · [PNG](docs/evidence/lab4/simulation-ac.png)
- [Transient — SVG](docs/evidence/lab4/simulation-tran.svg) · [PNG](docs/evidence/lab4/simulation-tran.png)

### ตรวจซ้ำ

```powershell
.\.venv\Scripts\python.exe -m unittest discover
.\.venv\Scripts\python.exe -m bjt_bias.app                      # ค้างไว้
.\.venv\Scripts\python.exe scripts\browser_layout_check.py      # กันข้อความซ้อนใน SPICE source/sweep
.\.venv\Scripts\python.exe scripts\browser_acceptance_lab4.py   # B1–B8
.\.venv\Scripts\python.exe scripts\browser_acceptance.py        # A1–A5 (Lab 03)
```

ผลที่บันทึกไว้: 98 unit tests PASS, browser checks **76/76** (หลัก) และ **7/7**
(B7(b) จำลอง engine หายด้วย `NGSPICE_BIN` ผิด) — ดู
[`docs/validation.md`](docs/validation.md) และ `docs/evidence/lab4/`
สภาพแวดล้อมที่ตรวจ: Windows 11 `10.0.26300.0` (26H2), Python 3.14.10,
Flask 3.1.3, ngspice-47, model 2N3904
SHA256 `E3B36B89C491C09E24986692E556095403E3D4CCE1EEB1A71DA06DAEA3C5E589`

### AI ช่วยสร้างส่วนไหน และนักศึกษาตรวจอะไร (Lab 04)

**AI (OpenCode) เขียน/แก้:**

- `bjt_bias/spice_engine.py` — `build_netlist`, `locate_engine`, `run_analysis`,
  `parse_op` / `parse_ac` / `parse_tran`, safe parsers, error contract
  (`subprocess.run` argument list, `shell=False`, มี `timeout`)
- `bjt_bias/plots.py` — `bode_svg`, `transient_svg` (SVG จากข้อมูลจริง)
- `bjt_bias/app.py` — `SOURCE_SPECS`, `ANALYSES`, `_resolve_analysis`,
  `_read_source`, `_spice_circuit`, `run_spice_simulation`, `engine_status`
  และ context เพิ่ม (ไม่แตะ `_read_form`/`bias.py` เดิม)
- `bjt_bias/templates/index.html`, `bjt_bias/static/style.css` — engine bar,
  ช่อง source, ปุ่ม Run, SPICE panel, badge, responsive ≤640 px
- `bjt_bias/spice_models/2n3904.lib` + `README.md` — copy model card สาธารณะ
  (ไม่ได้ fit ให้ตรง analytical), บันทึก provenance
- `scripts/fetch_ngspice.ps1`, `scripts/smoke_spice.py`,
  `scripts/browser_acceptance_lab4.py`, `test_spice_engine.py`,
  `test_spice_app.py`, `test_plots.py`
- `docs/evidence/lab4/`, ส่วน Lab 04 ใน `docs/validation.md`, `AGENTS.md`,
  และส่วนนี้ของ `README.md`

**นักศึกษาตรวจ:**

- กดปุ่ม analytical/dc/ac/tran ด้วยตัวเองว่าเปลี่ยนตามโหมด/ค่า input จริง
- เทียบตาราง B1–B8 กับหน้าเว็บของตัวเอง และลดหน้าต่างเหลือ ~390 px (B8)
- กรอกตาราง "ทวนเองโดยนักศึกษา" ใน [`docs/validation.md`](docs/validation.md)
  ให้ครบ — ขณะนี้ช่องนั้นยังว่าง (**NOT RUN**) และ AI ไม่ได้กรอกแทน
- ตรวจว่า `git diff --staged` ไม่มี `.venv`, `.env`, `runs/` หรือ credential
  ก่อนอนุมัติ push (`git push origin master:main`)
