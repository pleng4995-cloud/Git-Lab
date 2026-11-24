# Design — Lab 04: SPICE Simulator สำหรับ CE Voltage Divider v1

วันที่: 2026-11-24
สถานะ: อนุมัติแล้ว (2026-11-24) — กำลังเข้าสู่ขั้นวางแผน implement
งานที่ต่อยอด: Lab 03 (`bjt_bias/` @ `9345fa9`) — Flask + Analytical DC Bias 3 โหมด
ผู้เขียน: AI (OpenCode) ร่วมกับนักศึกษา

## Intent

Lab 04 ต้องพิสูจน์ว่าแอปเดิมเรียก **โปรแกรมจำลองวงจรจริง** ได้ ไม่ใช่คำนวณซ้ำ
ใน Python แล้ววาดกราฟสวย ๆ ผลทุกตัวที่แสดงต้องมาจาก ngspice ที่รันบนเครื่อง
มี netlist, run log, และ run directory ที่เปิดตรวจย้อนได้

โจทย์กำหนดขอบเขตชัด: SPICE ทำเฉพาะ **CE Voltage Divider วงจรอ้างอิงเดียว (v1)**
ส่วน Analytical DC Bias 3 โหมดของ Lab 03 ต้องอยู่ครบและไม่เปลี่ยนพฤติกรรม

### ทำไมต้องแยก Flask / ngspice / ค่าเปรียบเทียบ

สามชั้นนี้มีความน่าเชื่อถือคนละระดับ และการรวมมันเข้าด้วยกันจะทำให้ตรวจไม่ได้ว่า
ตัวเลขมาจากไหน

- **Flask (`app.py`)** ทำหน้าที่รับฟอร์ม, ตรวจ input, แปลงหน่วย, ประกอบ netlist
  และเลือกว่าจะเรียก engine ตัวไหน — ไม่คำนวณฟิสิกส์ของวงจร SPICE เอง
- **ngspice (external process)** เป็นโปรแกรมภายนอกที่ **อาจไม่มี, crash, หรือค้าง**
  จึงต้องมีสถานะ engine, timeout, return code และ log ของจริง ถ้า Flask
  "คำนวณแทน" เมื่อ engine ไม่พร้อม นั่นคือการปลอมผล
- **`bias.py` (Analytical)** ใช้สมการประมาณ β คงที่และ VBE = 0.7 V ซึ่งเป็น
  คนละสมมติฐานกับ Gummel-Poon model ของ ngspice ตัวเลขจึงไม่จำเป็นต้องเท่ากัน
  ทุกหลัก และต้องมีป้ายบอกที่มาแยกกัน ไม่ใช่เอามารวมเป็นค่าเดียว

## Goals

1. `bjt_bias/spice_engine.py` เป็น adapter เดียวที่สร้าง netlist, เรียก ngspice
   ผ่าน `subprocess.run` (argument list, ไม่ใช้ `shell=True`, มี timeout),
   และ parse ผลเป็น list/dict ของตัวเลขพร้อมหน่วย
2. รองรับ 3 analysis บนวงจร CE Voltage Divider v1: `.op`, `.ac`, `.tran`
3. หน้าเว็บแสดง **engine status** (พบ/ไม่พบ + version + path), **analysis selector**,
   **SPICE results** พร้อมป้ายที่มา, **กราฟจากข้อมูลจริง**, **netlist**, **run id**,
   และ **log tail**
4. โหมด DC แสดง Analytical กับ SPICE **คู่กันคนละคอลัมน์พร้อมป้ายที่มา**
   และคำนวณส่วนต่าง (Δ) ให้เห็น แต่ไม่เฉลี่ย/ไม่รวมเป็นค่าเดียว
5. กราฟทุกเส้นสร้างจาก array ที่ parse จากผลรันใน request นั้น — เปลี่ยน RE,
   amplitude หรือ frequency แล้วกราฟ/ตัวเลขต้องเปลี่ยนตาม
6. ทุก error path (engine ไม่มี, exit code ≠ 0, timeout, output ว่าง, parse ไม่ได้,
   input ผิด) แสดง error ที่อ่านรู้เรื่องและ **ไม่มีกราฟ/ผลรอบก่อนค้าง**
7. `docs/validation.md` มีตาราง B1–B8 ตามแม่แบบใบงาน + เวอร์ชัน ngspice +
   ชื่อและที่มาของ BJT model
8. `README.md`, `AGENTS.md`, และหลักฐานใน `docs/evidence/lab4/` ครบตามเกณฑ์ส่งงาน

## Non-goals

- ไม่ทำ Emitter bypass capacitor (CE), ไม่ทำ multi-stage, ไม่ทำ circuit editor
- ไม่รองรับ BJT หลายรุ่นใน UI (model เดียว, เปลี่ยนไฟล์ได้)
- ไม่ทำ interactive chart (zoom/pan/hover) — กราฟเป็น SVG ที่ server เรนเดอร์
- ไม่แตะสมการหรือผลของ Analytical DC Bias ทั้งสามโหมด
- ไม่เขียน framework ใหม่หรือย้ายโปรเจกต์
- ไม่ทำ Monte Carlo / temperature sweep / DC sweep ใน v1

## Anti-goals

- กราฟหรือตัวเลขที่ hard-code ไว้ในเทมเพลต/โมดูล แล้วเรียกตัวเองว่า "ผล ngspice"
- แสดงกราฟรอบก่อนพร้อมสถานะ Success เมื่อรอบล่าสุดล้มเหลว
- ซ่อน stderr/stdout ของ ngspice จนผู้ใช้หาสาเหตุไม่ได้
- ปล่อยให้ข้อความจากฟอร์มไปต่อ string เข้า netlist หรือ command โดยไม่ผ่านการแปลงเป็น float
- เรียก ngspice ผ่าน `shell=True` หรือปล่อยให้ค้างโดยไม่มี timeout
- อ้างว่าผ่าน B1–B8 ทั้งที่ browser/tool ไม่ได้รันจริง

## Constraints

- Windows 11 Home (build 26300), ไม่ใช่ administrator, ไม่มี Node.js/npx
- Python 3.14.10, Flask 3.1.3, venv เดิม (`.venv`)
- **ไม่มี Instructor Starter Kit** และ **ไม่มี ngspice** ในเครื่อง ณ วันออกแบบ
- เทสเดิม 62 ตัว (`test_bjt_app.py`, `test_bjt_bias.py`) ต้องผ่านทั้งหมดและห้ามแก้
- `bjt_bias/bias.py` และ `bjt_bias/app.py` ส่วน analytical ต้องคงพฤติกรรมเดิม
- Playwright MCP และ Impeccable ใช้ไม่ได้ (ไม่มี Node) → ใช้ Edge headless
  และ manual UI audit ตาม checklist เดียวกัน พร้อมบันทึกเหตุผลตรง ๆ
- ค่าตัวเลขทั้งหมดในเอกสารนี้เป็น **ค่าประมาณเพื่อ sanity check** ไม่ใช่ผลรัน
  ผลจริงจะบันทึกใน `docs/validation.md` หลังรันเสร็จ

## Approaches ที่พิจารณา

### 1. การติดตั้งและค้นหา ngspice

- **A. Portable 7z ไว้ที่ `C:\Tools\ngspice-47\` + env `NGSPICE_BIN` (เลือกแล้ว)**
  — ไม่ต้อง admin, repo ไม่แบกไบนารี, ย้ายเครื่องง่าย, ตรวจ version ได้จากโปรแกรมจริง
- B. ติดตั้งผ่าน installer/PATH เท่านั้น — เครื่องนี้ไม่ใช่ admin และไม่มีแพ็กเกจใน winget
- C. commit `ngspice.exe` เข้า repo — repo บวม, license/ขนาดไม่เหมาะ, ผูกกับเครื่องเดียว

### 2. วิธีสั่ง ngspice และอ่านผล

- **A. Batch netlist + `.control` block ที่ `wrdata` เป็น text (เลือกแล้ว)**
  — ได้ ASCII ที่ parse ง่าย, แยกไฟล์ต่อ analysis, debug ได้จาก log
- B. `ngspice -b -r run.raw` แล้ว parse binary raw — ต้องเขียน raw parser เอง
  และเสี่ยงต่อ layout ต่าง version
- C. interactive pipe ผ่าน stdin/stdout — เปราะ, คุม timeout ยาก, ไม่ใช่ batch

> ข้อควรระวังจากใบงาน: การผสม `.control ... .endc` กับ batch ต้องตรวจเอกสาร
> และทดสอบก่อน — แผนนี้จึงมี **smoke run** เป็นขั้นแรกก่อนต่อ UI และถ้า layout
> ของ `wrdata` ไม่ตรงสมมติฐาน จะปรับ parser ตามที่สังเกตจริงและบันทึกไว้

### 3. การวาดกราฟ

- **A. สร้าง SVG ด้วย Python จาก array ที่ parse มา (เลือกแล้ว)**
  — ไม่เพิ่ม dependency, path ทุกจุดคำนวณจากข้อมูลจริง, ตรวจใน DOM/เทสได้
- B. matplotlib — สวยและคุ้นเคย แต่เพิ่ม dependency หนัก และหลักฐานกลายเป็นไฟล์ภาพ
- C. JS canvas — โต้ตอบได้ แต่ต้องเขียน chart เองหรือเพิ่ม library และเทสยาก

### 4. BJT model

- **A. 2N3904 โมเดลผู้ผลิต (IS=6.734f, BF=416.4, VAF=74.03, …) (เลือกแล้ว)**
  — มีที่มา, เผยแพร่ซ้ำในคลังโมเดลสาธารณะ, ตรวจซ้ำได้ด้วยค่า parameter
- B. โมเดล generic ที่ตั้ง BF=100 ให้ตรง analytical — เป็นการเดาค่าเพื่อให้ตัวเลขตรง
  ขัดกับข้อกำหนด "ห้ามเดาค่าเฉพาะรุ่น"
- C. ข้ามการใช้ model (BJT อุดมคติ) — ไม่ใช่การจำลองที่ยอมรับได้

### 5. รูปแบบการสั่งรันใน UI

- **A. เลือก analysis ทีละโหมดแล้วกด Run (เลือกแล้ว)** — ตรงกับ B2–B7
  ที่ต้องเปลี่ยนค่าแล้วรันซ้ำ และบอกได้ชัดว่าโหมดไหนล้ม
- B. ปุ่มเดียวรันทั้งสาม — ช้า, error รวมกันอ่านยาก, timeout คุมยาก

## Design

### 1. โครงไฟล์ที่เปลี่ยน

```
bjt_bias/
├── app.py                     # + analysis dispatch, + validation, + page context
├── bias.py                    # ไม่แก้ (Analytical reference)
├── spice_engine.py            # ใหม่: netlist / run / parse / engine status
├── plots.py                   # ใหม่: SVG จาก array (bode, transient)
├── spice_models/
│   └── 2n3904.lib             # ใหม่: BJT model + provenance header
├── templates/index.html       # + analysis selector, engine bar, SPICE panel
└── static/style.css           # + สไตล์ panel/badge/กราฟ (ไม่แตะของเดิม)
scripts/
├── fetch_ngspice.ps1          # ใหม่: ดาวน์โหลด+แตก portable (ไม่ commit ไบนารี)
├── smoke_spice.py             # ใหม่: รัน .op/.ac/.tran ตรง ๆ เพื่อตรวจ layout
└── browser_acceptance_lab4.py # ใหม่: B1–B8 ด้วย Edge headless
test_spice_engine.py           # ใหม่: unit test parser/netlist/validation
test_spice_app.py             # ใหม่: Flask error paths + provenance separation
AGENTS.md                      # ใหม่: กฎการทำงาน + provenance
docs/validation.md             # + B1–B8, environment, model
docs/evidence/lab4/            # ใหม่: screenshot + netlist + log ที่คัดแล้ว
runs/                          # สร้างตอนรัน, gitignore
```

### 2. Engine discovery — `spice_engine.py`

```python
def locate_engine() -> dict:
    """คืน {"available", "path", "version", "source", "error"}"""
```

ลำดับการค้นหา:

1. env `NGSPICE_BIN` (path ไปที่ `ngspice.exe` หรือโฟลเดอร์)
2. `shutil.which("ngspice")`
3. path ที่รู้จัก: `C:\Tools\ngspice-47\*\Spice64_dll\...` ตามด้วย `Spice64\bin`,
   `C:\Program Files\ngspice*` (best effort, ไม่ scan ทั้งไดรฟ์)

`version` มาจาก `subprocess.run([exe, "--version"], timeout=10)` แล้ว parse
บรรทัดแรกที่ขึ้นต้นด้วย `ngspice`; ถ้าเรียกไม่ได้ → `available=False` พร้อม error

`scripts/fetch_ngspice.ps1`:

- ดาวน์โหลด `ngspice-47_64.7z` จาก SourceForge (URL เดียว, pin version)
- แตกด้วย `tar -xf` (bsdtar อ่าน 7z ได้) และ fallback `7zr.exe`
- แตกไป `C:\Tools\ngspice-47\`
- ตั้ง `NGSPICE_BIN` ระดับ user (หรือพิมพ์คำสั่งให้ผู้ใช้ตั้ง)
- แสดง SHA256 ของไฟล์ที่ดาวน์โหลด เพื่อให้บันทึกใน README
- **ไม่แตะ repo** และไม่ commit ไบนารี; `.gitignore` เพิ่ม `runs/`

### 3. Netlist — วงจรอ้างอิง v1

โหนด: `vin, base, coll, emit, out, vcc, 0`

```
* CE voltage-divider amplifier v1 (Lab 04)
* Generated by bjt_bias.spice_engine -- values from validated form input only
.include <abs path to bjt_bias/spice_models/2n3904.lib>
VCC  vcc  0   12
R1   vcc  base 100k
R2   base 0   22k
RC   vcc  coll 2.2k
RE   emit 0   1k
Q1   coll base emit Q2N3904
CIN  vin  base 10u
COUT coll out  10u
RL   out  0    10k
VIN  vin  0   DC 0 AC 1 SIN(0 10m 1k)
.control
<คำสั่งของ analysis ที่เลือก>
.endc
```

- ค่าตัวต้านทาน/ตัวเก็บประจุเขียนจาก float ที่ตรวจแล้วด้วยตัวจัดรูปแบบเดียว
  (`100k` → `100000` หรือ `100k`; เลือกเขียนเป็นตัวเลข SI ตรง ๆ เช่น `100000`)
- ชื่อโหนด/อุปกรณ์เป็นค่าคงที่ในโค้ด ไม่ได้มาจากผู้ใช้
- `CIN`/`COUT` เปิดวงจรเองเมื่อ `.op` (DC) — ไม่ต้องใส่ directive พิเศษ
- `VIN` มีทั้ง `AC 1` และ `SIN()` เพื่อให้ netlist เดียวรองรับได้ทั้งสามโหมด
  แต่ **แต่ละ request สร้าง netlist ใหม่ที่มีเฉพาะคำสั่งของ analysis นั้น**

คำสั่งใน `.control` ต่อ analysis:

| analysis | คำสั่ง | ไฟล์ผล |
|---|---|---|
| `dc` | `set units=degrees` + `op` + `wrdata op.txt v(base) v(emit) v(coll) @q1[ic] @q1[ib] @q1[ie]` | `op.txt` |
| `ac` | `ac dec <pts> <fstart> <fstop>` + `wrdata ac.txt vdb(out) vp(out)` | `ac.txt` |
| `tran` | `tran <step> <stop>` + `wrdata tran.txt v(vin) v(out)` | `tran.txt` |

- AC: `VIN` มี `AC 1` → `v(out)` คือ gain (V/V) เทียบกับ **โหนด `vin`**
  ซึ่งเป็นจุดหลังแหล่งจ่ายในอุดมคติ (source impedance 0) — ต้องระบุใน UI ว่า
  "Gain = 20·log10(|V(out)|/|V(vin)|), reference = node vin"
- Tran: `stop = 5 / f`, `step = stop / 1000`, แสดงค่า stop/step ที่คำนวณได้บนหน้าเว็บ
- ทุกครั้งที่รัน: สร้าง `runs/<UTC timestamp>-<6 hex>/` เก็บ `circuit.cir`,
  `run.log`, ไฟล์ `.txt`, `meta.json` (input ที่ใช้, version, model sha256,
  คำสั่งที่รัน, exit code, เวลา)

### 4. การรัน — `run_analysis()`

```python
SpiceResult = {
  "status": "ok" | "engine_missing" | "failed" | "timeout" | "parse_error",
  "analysis": "dc" | "ac" | "tran",
  "run_id": "...", "run_dir": "...",
  "command": ["C:\\Tools\\...\\ngspice.exe", "-b", "-o", "run.log", "circuit.cir"],
  "returncode": int | None,
  "duration_s": float,
  "engine": {"path": ..., "version": ...},
  "model": {"name": "2N3904", "file": "2n3904.lib", "sha256": "..."},
  "data": {...},          # ว่างเสมอเมื่อ status != "ok"
  "warnings": [...],
  "stdout_tail": "...", "stderr_tail": "...",
}
```

- `subprocess.run(cmd, cwd=run_dir, capture_output=True, text=True,
  encoding="utf-8", errors="replace", timeout=60, shell=False)`
- `cmd` เป็น list เสมอ
- หลังรัน: ตรวจ `returncode == 0`, ไฟล์ผลมีอยู่, ขนาด ≤ 20 MB, จำนวนบรรทัด ≤ 200k
- `run.log` ของ ngspice เก็บไว้ทั้งไฟล์; หน้าเว็บแสดง 40 บรรทัดท้าย
- เก็บ run ล่าสุดไว้ 50 ชุด แล้วลบเก่าที่สุด (ไม่ลบไฟล์ที่ผู้ใช้คัดลอกไปแล้ว)

### 5. Parsing

- อ่านทีละบรรทัด, `split()`, `float()`; ข้ามบรรทัดว่าง/คอมเมนต์
- คาดหวังคอลัมน์: `op.txt` = 6 ค่า, `ac.txt` = 3 (freq, gain_dB, phase_deg),
  `tran.txt` = 3 (time, vin, vout) — **ยืนยันด้วย smoke run ก่อน**
- ตรวจ: จำนวนแถวขั้นต่ำ (ac ≥ 10, tran ≥ 100), ค่า finite ทั้งหมด,
  frequency/time ต้องเพิ่มขึ้น monotonically
- คำนวณเพิ่ม: `VCE = v(coll) − v(emit)`;
  cross-check `IC` จาก `(VCC − v(coll)) / RC` เทียบกับ `@q1[ic]`
  ถ้าต่างเกิน 2% → ใส่ warning (ไม่ล้มทั้ง run แต่บอกผู้ใช้)
- ถ้า parse ไม่ได้ตามสัญญา → `status="parse_error"`, `data={}`

### 6. กราฟ — `plots.py`

- ฟังก์ชันบริสุทธิ์: `bode_svg(freq, gain_db, phase_deg, *, width=720)` และ
  `transient_svg(t, vin, vout, *, width=720)` คืน string SVG
- แกน X ของ Bode เป็น log10, มี tick 10/100/1k/10k/100k/1M
- Bode = 2 panel ซ้อน (magnitude dB, phase องศา), legend + unit ครบ
- Transient: แกน ms, สองเส้น (`vin` เส้นประ, `vout` เส้นทึบ), legend + unit mV
- ทุก path สร้างจาก array; ถ้าจุดเกิน 1200 จุด ใช้ min/max decimation
  เฉพาะตอนวาด (ข้อมูลเต็มยังอยู่ในไฟล์ผลและตาราง)
- ใส่ `<desc>` เป็นข้อความสรุป (run id, จำนวนจุด, ค่าสูงสุด/ต่ำสุด)
  เพื่อให้เทส/ตรวจ DOM ยืนยันได้ว่ากราฟสัมพันธ์กับข้อมูลจริง
- ถ้าไม่มีจุดตัด −3 dB ในช่วง sweep → แสดง "not determined in sweep range"
  ไม่คำนวณตัวเลข cutoff ขึ้นมาเอง

### 7. `app.py` — validation และ dispatch

ช่องใหม่ (แยกกลุ่ม "Source & sweep"):

| ชื่อ | หน่วย | ค่าเริ่มต้น | ช่วงที่ยอมรับ |
|---|---|---|---|
| `amplitude_mv` | mV peak | 10 | 0.001–1000 |
| `frequency_hz` | Hz | 1000 | 1–1,000,000 |
| `ac_start_hz` | Hz | 10 | 0.1–1e9 และ < stop |
| `ac_stop_hz` | Hz | 1,000,000 | > start และ ≤ 1e9 |
| `ac_points_dec` | points/decade | 20 | 5–200 |

- `analysis` ∈ {`analytical`, `dc`, `ac`, `tran`}
  - **หายไปจาก POST → `analytical`** = ทำเฉพาะ Lab 03 เดิม ไม่เรียก engine เลย
    (เทสเดิม 62 ตัว POST โดยไม่ส่ง `analysis` จึงไม่ช้าลงและไม่ขึ้นกับ ngspice)
  - หน้าฟอร์มส่ง `analysis` มาเสมอเมื่อผู้ใช้กด Run
- **SPICE ใช้ได้เฉพาะ `mode = divider`** (วงจร v1) — ถ้า `mode` เป็น `fixed`
  หรือ `emitter` และ `analysis` เป็น `dc`/`ac`/`tran` → error
  "SPICE analysis is available for the Voltage Divider reference only"
  และไม่เรียก engine; UI ซ่อน/disable analysis selector ในสองโหมดนั้น
- ตรวจ `stop = 5/f ≤ 2 s` มิฉะนั้นแจ้ง error บอกให้เพิ่ม frequency
- ค่า `beta`/`vbe` ในฟอร์มยังใช้กับ **Analytical เท่านั้น** — ติดป้ายใน UI
  ว่า SPICE ใช้ค่าจาก BJT model
- **ตรวจเฉพาะช่องที่ analysis นั้นใช้** (ช่องของ analysis อื่นไม่ถูกอ่านและไม่ทำให้ error):

  | analysis | ช่อง bias | amplitude/frequency | AC sweep |
  |---|---|---|---|
  | `analytical` | ตามโหมด | ไม่ตรวจ | ไม่ตรวจ |
  | `dc` | divider | ไม่ตรวจ | ไม่ตรวจ |
  | `ac` | divider | ไม่ตรวจ | ต้องถูกต้อง |
  | `tran` | divider | ต้องถูกต้อง | ไม่ตรวจ |

- ถ้ามี error ใด ๆ → ทั้ง analytical และ SPICE ของ request นั้นเป็น `None`
- ถ้า `analysis` เป็น `dc`/`ac`/`tran` → ยังคำนวณ analytical DC เพื่อแสดงเป็น
  reference (ป้าย Analytical ชัดเจน) แต่ไม่เอามาแทนผล SPICE

### 8. เทมเพลตและ UI

- **Engine bar** ใต้ header: `ngspice-47 · C:\Tools\...` (เขียว) หรือ
  `ngspice not found` + วิธีติดตั้ง (แดง) — แสดงทุกหน้า
- **Analysis selector**: ใช้ปุ่ม submit หลายปุ่มในฟอร์มเดียว โดยตั้ง
  `name="analysis"` ที่ตัวปุ่ม (ไม่ต้องใช้ JavaScript) — `Analytical DC only`
  (`analytical`), `Run SPICE DC` (`dc`), `Run AC sweep` (`ac`),
  `Run Transient` (`tran`); สามปุ่มหลังซ่อนเมื่อ `mode != divider`
  พร้อมข้อความ "SPICE is available for the Voltage Divider reference only"
- **ผลลัพธ์** แบ่งเป็น 2 การ์ด:
  1. `ANALYTICAL · bias.py` — ตารางเดิมของ Lab 03 พร้อม β/VBE ที่ใช้
  2. `SPICE · ngspice <version> · run <id>` — แสดงเฉพาะเมื่อ status = ok
     พร้อม model, วันเวลา, ระยะเวลารัน, ปุ่ม `<details>` ดู netlist/คำสั่ง/log
- **DC compare table**: `Quantity | Analytical | SPICE (.op) | Δ`
- **Error card**: หัวข้อตาม status + ข้อความจาก engine + log tail
  ไม่มีกราฟและไม่มีตัวเลขผล
- มือถือ (≤ 640 px): ฟอร์มเป็นคอลัมน์เดียว, กราฟกว้าง 100%, ตารางเลื่อนแนวนอนได้
- ไม่แตะ h1 "Lab 02: BJT DC Bias Web App" และ "Week 2 Goal"
  เพราะ `test_bjt_app.py` assert ข้อความเหล่านี้ (คงไว้ตามเดิม)

### 9. ตาราง error path

| สภาพ | status | ผู้ใช้เห็น |
|---|---|---|
| ไม่พบ ngspice | `engine_missing` | badge แดง + วิธีติดตั้ง + ไม่มีกราฟ |
| เรียกไม่ขึ้น/permission | `failed` | path ที่ลอง + stderr |
| exit code ≠ 0 | `failed` | return code + 40 บรรทัดท้ายของ log |
| เกิน 60 วินาที | `timeout` | "ngspice did not finish within 60 s" |
| ไฟล์ผลว่าง/ผิดรูป | `parse_error` | บรรทัดแรกที่ parse ไม่ได้ + จำนวนแถวที่อ่านได้ |
| input ผิด | ไม่รัน engine | ข้อความระบุช่องและช่วงที่ยอมรับ |

### 10. Security / resource limits

- `subprocess.run` แบบ list, `shell=False`, `cwd` = run dir ที่สร้างเอง
- ค่าตัวเลขเข้า netlist ผ่าน `float` + formatter เท่านั้น; ไม่มี string จากผู้ใช้
- ชื่อไฟล์/โฟลเดอร์สร้างจาก timestamp + `secrets.token_hex(3)`
- timeout 60 s, ไฟล์ผล ≤ 20 MB, จำนวนแถว ≤ 200k, เก็บ 50 run
- ไม่รันพร้อมกันแบบขนานใน v1 (Flask dev server + request เดียว)

### 11. เทส

- คงเทสเดิม 62 ตัวโดยไม่แก้
- `test_spice_engine.py` (ไม่ต้องมี ngspice):
  - netlist มีค่าที่แปลงแล้วและไม่มีข้อความผู้ใช้หลุด
  - formatter ตัวเลข SI ถูกต้อง (1k, 2.2k, 10u, 0.01)
  - parser อ่าน fixture ที่คัดจากผลจริงได้ (op/ac/tran)
  - parser ปฏิเสธคอลัมน์ผิด/NaN/แถวไม่พอ → `parse_error`
  - status contract: `data == {}` เมื่อไม่ ok
- `test_spice_app.py`:
  - `analysis` หาย → `analytical` และ **ไม่เรียก engine** (เทสเดิม 62 ตัวยังเร็วเท่าเดิม)
  - input ผิด (amplitude 0, freq 0, start ≥ stop, points 0) → error ไม่เรียก engine
  - engine ไม่มี → หน้าเว็บแสดง engine_missing และไม่มี `<svg` ของกราฟ
  - analytical ยังแสดงและป้ายถูกแยก
- integration test (ข้ามถ้าไม่มี engine): รัน `.op` จริงแล้วเทียบค่ากับ analytical
  ในระดับที่สมเหตุสมผล (IC ต่าง ≤ 20%) พร้อมเหตุผลเรื่อง model

### 12. เอกสารและหลักฐาน

- `README.md`: วิธีติดตั้ง ngspice (portable), วิธีรัน, tested environment,
  repo URL + commit SHA, AI provenance, จุดเลือกฟังก์ชัน/แปลงหน่วย
- `AGENTS.md`: กฎ (ห้าม fabricate, ห้ามแตะ analytical path, provenance,
  ห้าม shell=True, ต้องบันทึกผล NOT RUN ตามจริง)
- `docs/validation.md`: คง A1–A5 ของ Lab 03 แล้วเพิ่ม B1–B8
  (Method / Input / Expected · Reference / Observed / Evidence / Status)
  + ngspice version + model + ข้อจำกัด
- `docs/evidence/lab4/`: screenshot desktop/mobile, netlist ที่รันจริง,
  excerpt ของ `op.txt`/`ac.txt`/`tran.txt`, log ที่มี error case
- `scripts/browser_acceptance_lab4.py`: Edge headless รัน B1–B8
  (ฟอร์ม POST จริง, อ่าน DOM, screenshot 1280 และ 390)

### 13. ค่าประมาณเพื่อ sanity check (ยังไม่ใช่ผลรัน)

VCC 12 V, R1 100k, R2 22k, RC 2.2k, RE 1k, RL 10k, Cin/Cout 10 µF, 2N3904 (BF 416.4)

| ปริมาณ | ค่าประมาณ | ที่มา |
|---|---|---|
| IC (SPICE) | ≈ 1.4 mA | β ของ model (416.4) สูงกว่า 100 → IB สูงขึ้น |
| VCE (SPICE) | ≈ 7.4 V | ยังอยู่ใน forward active |
| \|Av\| midband | **≈ 1.8** (≈ 5.1 dB) | RE **ไม่มี bypass** → Av = (RC∥RL)/(RE + re), re = VT/IE ≈ 18 Ω |
| fL | ≈ 1.5 Hz | ประมาณจาก Cin (Rin ≈ 17k) และ Cout (RC+RL = 12.2k) |
| Vout peak (10 mV, 1 kHz) | ≈ 18 mV, กลับเฟส 180° | Av × input |

สูตรที่ใช้กะ (ต้องยืนยันด้วยผลรัน):

```
re   = VT / IE,  VT = 25.85 mV
Av   = −(RC ∥ RL) / (RE + re)          # RE ไม่มี bypass ตาม baseline
fCin = 1 / (2π · Rin · Cin),  Rin = R1 ∥ R2 ∥ (rπ + (β+1)·RE)
fCout= 1 / (2π · (RC + RL) · Cout)
```

> ค่า gain ที่สูงกว่านี้ (หลักสิบ–ร้อย) จะเกิดเมื่อมี emitter bypass capacitor
> ซึ่ง **ไม่อยู่ใน baseline ของใบงาน** — v1 จึงไม่ใส่ CE และกราฟควรได้ gain
> หลักหน่วย ไม่ใช่หลักร้อย

ค่าจริงจะถูกบันทึกจาก run และใช้เป็น observed ใน `docs/validation.md`
ถ้าต่างจากประมาณนี้มากจนอธิบายไม่ได้ → ต้องตรวจ netlist ก่อนสรุป

### 14. ชุดตรวจ B1–B8 (นิยามในเอกสารนี้ ไม่ต้องรอใบงาน)

ใบงานให้ตาราง B1–B8 มาแล้ว แต่เพื่อให้สร้าง acceptance script ได้ตรง
จึงเขียนกรณีและค่าที่ใช้จริงไว้ที่นี่

| Case | Action ใน browser | Input ที่ใช้ | Expected | หลักฐาน |
|---|---|---|---|---|
| B1 | เปิด Divider / Fixed / Emitter ตามชุด Lab 03 | A1–A4 ของ `docs/validation.md` | ผล analytical เท่า Lab 03 (1.230/8.052, 1.130/9.514, 1.026/8.705, 0.940/8.033) และสลับโหมดได้ | ค่าที่อ่านจาก DOM + screenshot |
| B2 | Divider + Run DC | baseline v1 | SPICE panel มี VB/VE/VC/VCE/IC จาก `.op`, แสดง model 2N3904 + run id + status ok | หน้าเว็บ + `op.txt` + log |
| B3 | เปลี่ยน RE 1k → 2k แล้ว Run DC ซ้ำ | เดิม | IC/VE/VCE เปลี่ยนตามผลจำลอง (ไม่ใช่ค่าเดิม) | ผลก่อน/หลัง + run id ต่างกัน |
| B4 | Run AC | sweep 10 Hz–1 MHz, 20 pts/dec | กราฟ Bode: แกน Hz (log), gain dB, phase องศา, legend, run id | screenshot + `ac.txt` |
| B5 | Run Transient | 10 mV peak, 1 kHz | กราฟ time (ms) + Vin/Vout (mV), เห็นการกลับเฟส 180° | screenshot + `tran.txt` |
| B6 | เปลี่ยน amplitude 10 → 20 mV (หรือ f 1k → 2k) แล้ว Run Tran ซ้ำ | เดิม | รูปคลื่น/amplitude เปลี่ยนตาม input และ Vout ≈ 2 เท่า | ภาพก่อน/หลัง |
| B7 | (a) RE = 0 แล้ว Run (b) ปิด engine ชั่วคราวแล้ว Run | (a) RE 0 (b) `NGSPICE_BIN` ชี้ path ที่ไม่มี | (a) error ระบุ RE ไม่เรียก engine (b) engine_missing + วิธีติดตั้ง ไม่มีกราฟ | screenshot + ข้อความ |
| B8 | เปิด desktop 1280 px และ mobile 390 px แล้วสลับโหมด | — | กราฟ/หน่วย/ปุ่มไม่ถูกตัด, ตารางเลื่อนได้ | screenshot 2 ขนาด |

หมายเหตุวิธีตรวจ B7(b): ต้องรีสตาร์ท Flask ด้วย `NGSPICE_BIN` ที่ชี้ไปยัง path
ที่ไม่มีอยู่ แล้วเปิดหน้าเว็บ — บันทึกใน validation ว่าเป็นวิธีจำลอง engine ไม่พร้อม
ตามที่ใบงานอนุญาต ไม่ใช่การปิด ngspice จริงทั้งเครื่อง

## ความเสี่ยงและวิธีรับมือ

| ความเสี่ยง | ผลกระทบ | ทางรับมือ |
|---|---|---|
| `tar` แตก 7z ไม่ได้ | ติดตั้งไม่ได้ | fallback `7zr.exe` (ไม่ต้องติดตั้ง) |
| `wrdata` คอลัมน์ไม่ตรงสมมติฐาน | parse ผิด | smoke run ก่อน + fixture จากผลจริง + parse_error ที่อ่านรู้เรื่อง |
| ngspice พิมพ์ warning ปนใน log | parse สับสน | อ่านผลจากไฟล์ `.txt` เท่านั้น ไม่ parse stdout |
| console encoding เพี้ยน | ข้อความ error อ่านไม่ได้ | decode `errors="replace"` + แสดงเฉพาะ ASCII ที่จำเป็น |
| เครื่องอื่นไม่มี ngspice | ตรวจซ้ำไม่ได้ | `fetch_ngspice.ps1` + README + engine_missing ที่อธิบายชัด |

## สิ่งที่เหลือให้ผู้สร้างตัดสิน

- รายละเอียด tick/legend ของกราฟ (ความสวย)
- ข้อความ warning เมื่อ IC จาก `@q1[ic]` กับ `(VCC−VC)/RC` ต่างกันเกิน 2%
- SHA256 จริงของ archive ที่ดาวน์โหลด (บันทึกหลังตรวจครั้งแรก)
- รูปแบบการ์ดผลลัพธ์บนมือถือ (สแตกหรือ accordion)
