# AGENTS — กฎการทำงานใน repo นี้

ใช้กับทุกคน/ทุก agent ที่แก้ ENG29 2121 Lab 02–04 ใน repo นี้ อ่านก่อนแก้โค้ด
และก่อนเขียนรายงานผล

## 1. ห้าม fabricate ผล

- ตัวเลขใน `docs/validation.md`, `README.md` และ `docs/evidence/` ต้องมาจากการ
  รันจริง (browser/DOM/ngspice) หรือจากการคำนวณมือที่ระบุสมการไว้ชัดเจนเท่านั้น
- ถ้าไม่ได้รัน ให้เขียน **NOT RUN** พร้อมเหตุผล — ห้ามคาดเดาแล้วเขียนเป็นค่าจริง
- ถ้า run เก่าถูกแทนที่ด้วย run ใหม่ ต้องอัปเดต run id/evidence ให้ตรงกันเสมอ
- ห้ามนำ evidence ของโมเดล/วงจรเก่ามาเป็นหลักฐานของการรันใหม่

## 2. ห้าม hard-code กราฟหรือผล SPICE

- กราฟ Bode/Transient ถูกสร้างจากข้อมูลที่ ngspice เขียนจริง (`ac.txt`,
  `tran.txt`) โดย `bjt_bias/plots.py` → SVG ฝั่ง Python (ไม่เพิ่ม dependency)
- ห้ามใส่ curve ตัวอย่าง, ค่าคงที่แทนการ parse หรือ screenshot ของกราฟเก่าลงใน UI
- ถ้า status ไม่ใช่ `ok` **ต้องไม่มี** ค่า SPICE หรือกราฟปรากฏ (กฎเดียวกับ
  error contract ใน `spice_engine.run_analysis`)

## 3. ห้ามแตะ analytical path เดิม

- ห้ามแก้ `bjt_bias/bias.py` — ผล analytical Lab 02/03 ต้องคงเดิม
  (A1: IC 1.230 mA / VCE 8.052 V)
- ชุดเทสเดิม 62 ตัวต้องผ่านเหมือนเดิม; Lab 04 เพิ่มเทสเท่านั้น
- ห้ามเปลี่ยน `<h1>Lab 02: BJT DC Bias Web App</h1>` และข้อความ `Week 2 Goal`
- SPICE เฉพาะวงจร CE Voltage Divider v1 (`mode == "divider"`); Analytical DC
  ยังใช้ได้ทุกโหมด
- ถ้า POST ไม่มี `analysis` ให้เป็น `analytical` และไม่เรียก ngspice

## 4. ความปลอดภัยของ engine

- เรียก ngspice ด้วย `subprocess.run` แบบ argument list, `shell=False`, มี
  `timeout` เสมอ — ห้ามต่อ string เป็น command line เดียว
- ตรวจ/จำกัดขอบเขต input ก่อนสร้าง netlist (รวมถึง resistance, frequency,
  amplitude, sweep points)
- อ่านผลจากไฟล์ที่ ngspice เขียน ไม่ parse stdout ที่มี warning ปน
- `NGSPICE_BIN` ที่ตั้งค่าจะเป็น **authoritative**: ถ้าชี้ path ผิดให้รายงาน
  `engine_missing` ทันที ห้าม fallback ไปหา engine ตัวอื่นโดยเงียบ ๆ
- เมื่อ engine ไม่พร้อม ต้องแสดงวิธีติดตั้งในแถบ status และไม่มีกราฟ/ค่า SPICE

## 5. ที่มาของ model และ provenance

- model ที่ใช้คือ `bjt_bias/spice_models/2n3904.lib` (2N3904, `.model Q2N3904 NPN`)
  — ไม่มี Instructor Starter Kit ในเครื่องที่ตรวจ
- อย่า fit/copy ค่า model ให้ตรงกับผล analytical; สองฝั่งใช้สมมติฐานต่างกัน
  (`bias.py` ใช้ β/VBE คงที่, model card ใช้ `BF=416.4` ฯลฯ)
- บันทึก SHA256 ของ `.lib` ทุกครั้งที่ตรวจ (`docs/validation.md` และ `meta.json`)
- ถ้าเปลี่ยน model หรือวงจร ต้องรัน B1–B8 ใหม่ทั้งชุด แทนที่ screenshot/JSON
  และอัปเดต SHA256/version ด้วย

## 6. วิธีตรวจที่ทำซ้ำได้

```powershell
.\.venv\Scripts\python.exe -m unittest discover
.\.venv\Scripts\python.exe -m bjt_bias.app          # เซิร์ฟเวอร์ค้างไว้
.\.venv\Scripts\python.exe scripts\browser_acceptance.py          # A1–A5
.\.venv\Scripts\python.exe scripts\browser_acceptance_lab4.py     # B1–B8
.\.venv\Scripts\python.exe scripts\smoke_spice.py                 # smoke engine
```

B7(b) ต้องรีสตาร์ทเซิร์ฟเวอร์ด้วย `NGSPICE_BIN` ที่ชี้ path ที่ไม่มี แล้วรัน
`scripts\browser_acceptance_lab4.py --b7b` กับ port นั้น (ค่าเริ่มต้น 5001)
ห้ามใช้เซิร์ฟเวอร์ port 5000 ที่ engine ปกติ — ผลจะตรงข้าม

Browser ที่ใช้คือ Microsoft Edge headless เพราะเครื่องนี้ไม่มี Node/npx สำหรับ
Playwright MCP; เก็บทั้ง `--dump-dom` และ `--screenshot` ไว้เป็นหลักฐาน ถ้าโมเดล
อ่านภาพไม่ได้ให้ใช้ DOM assertion เป็น proxy และระบุว่ายังต้อง manual audit
โดยนักศึกษา (ห้ามกรอกตาราง "ทวนเองโดยนักศึกษา" แทน)

## 7. git / การส่งงาน

- ทำงานบน `master` ในเครื่อง; **ต้องขออนุมัติก่อน push เสมอ**
  (`git push origin master:main`) — ห้าม push เอง
- ห้าม commit `.venv/`, `.env`, `runs/`, ไบนารี ngspice หรือ credential
  (`.gitignore` มีอยู่แล้ว; ตรวจ `git diff --staged` ก่อน commit ทุกครั้ง)
- เอกสารต้องระบุ repo URL, commit SHA, tested environment และ AI provenance
  ให้ตรงกับสิ่งที่อยู่จริงในเครื่อง
