# BJT Common-Emitter DC Bias

แอป Flask ขนาดเล็กสำหรับคำนวณ **DC operating point** ของวงจร BJT
Common-Emitter แบบ voltage-divider bias และตรวจผลด้วยการคำนวณวิศวกรรม
อีกวิธีที่เป็นอิสระต่อกัน

## ติดตั้ง

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
```

## รัน

```powershell
.\.venv\Scripts\python.exe -m bjt_bias.app
```

เปิด <http://127.0.0.1:5000>

## หน้าเว็บ (Lab 02 layout)

หน้า `/` แบ่งเป็น

- **Input Parameters** — 7 ช่อง พร้อม unit selector
- **Circuit: Common-Emitter Amplifier** — ไดอะแกรม SVG ที่ label แสดงค่าที่กรอก
  (`R1 100 kΩ`, `VCC 12 V`, `β = 100`) ไม่ใช่ค่าที่คำนวณ
- **DC Bias Results** — ตาราง 7 ค่า เรียง `V_B, V_E, V_C, V_CE, I_B, I_C, I_E`
  พร้อม banner ตาม region: เขียว = active, เหลือง = cutoff, แดง = saturation
- **Verification** — `<details>` ใต้ 3 คอลัมน์ แสดง Method 1 vs Method 2 + PASS/FAIL
- **Week 2 Goal** — แถบเป้าหมายของแล็บ

Layout ยุบเป็นคอลัมน์เดียวเมื่อจอกว้างน้อยกว่า 900px

## อินพุต

| ช่อง | ความหมาย | หน่วยที่เลือกได้ | ค่าเริ่มต้น |
|---|---|---|---|
| `VCC` | แหล่งจ่ายไฟ | V | 12 V |
| `R1` | ตัวต้านทานตัวบน (VCC → base) | Ω / kΩ / MΩ | 100 kΩ |
| `R2` | ตัวต้านทานตัวล่าง (base → GND) | Ω / kΩ / MΩ | 22 kΩ |
| `RC` | ตัวต้านทาน collector | Ω / kΩ / MΩ | 2.2 kΩ |
| `RE` | ตัวต้านทาน emitter | Ω / kΩ / MΩ | 1 kΩ |
| `beta` | อัตราขยายกระแส `h_FE` | – | 100 |
| `VBE` | แรงดัน base-emitter | V | 0.7 V |

ช่องตัวต้านทานยังพิมพ์ suffix `k` (×1e3) และ `M` (×1e6) ได้ เช่น `47000`, `47k`, `2.2k`, `1M`
แต่ถ้าเลือกหน่วยที่ไม่ใช่ Ω ต้องใช้อย่างใดอย่างหนึ่ง (ใส่ suffix พร้อมเลือก kΩ จะได้ error)

## Method 1 — Thevenin divider reduction

```
V_BB = VCC · R2 / (R1 + R2)
R_B  = R1 · R2 / (R1 + R2)
I_B  = (V_BB − VBE) / (R_B + (beta + 1) · RE)
I_C  = beta · I_B
I_E  = (beta + 1) · I_B
V_E  = I_E · RE
V_C  = VCC − I_C · RC
V_CE = V_C − V_E
```

## Method 2 — nodal analysis (independent)

ไม่ใช้ `V_BB` หรือ `R_B` เลย แก้ระบบสมการเชิงเส้น 6 ตัวแปร
`[V_B, V_C, V_E, I_B, I_C, I_E]` จาก KCL ที่แต่ละ node โดยถือ `VBE`
เป็นแหล่งจ่ายแรงดันคงที่ แล้วแก้ด้วย Gaussian elimination + partial pivoting

```
node B: (V_B − VCC)/R1 + V_B/R2 + I_B = 0
node C: (V_C − VCC)/RC + I_C = 0
node E: I_E − V_E/RE = 0
I_E = I_B + I_C
I_C = beta · I_B
V_B − V_E = VBE
```

หน้าเว็บแสดงทั้งสองวิธีเทียบกัน พร้อมส่วนต่างและผล PASS/FAIL
โดยถือว่าตรงกันเมื่อ `|a − b| ≤ 1e-6 · max(1, |a|, |b|)`

## Region

| เงื่อนไข | Region | สิ่งที่รายงาน |
|---|---|---|
| `I_B ≤ 0` | cutoff | กระแสเป็น 0, `V_B = V_BB`, `V_C = VCC`, `V_CE = VCC` |
| `V_CE < 0.2 V` | saturation | ค่าจากสมการ active mode + เตือนว่าใช้ไม่ได้ |
| อื่น ๆ | active | ค่าจากสมการ active mode |

## Validation

- `VCC`, `R1`, `R2`, `RC`, `RE`, `beta` ต้องเป็นจำนวนจริงมากกว่าศูนย์
- `VBE` ต้องอยู่ระหว่าง `0` ถึง `VCC`
- `VBE` นอกช่วง 0.5–0.9 V จะได้ warning แต่ยังคำนวณให้

## ข้อจำกัด

- ใช้ active-mode DC model: `VBE` คงที่ตามอินพุต, `I_C = beta · I_B`, ไม่คิด leakage
- `VCE_sat = 0.2 V` เป็นค่าคงที่ ไม่ได้แก้สมการใหม่เมื่ออิ่มตัว
- ไม่มี AC analysis, transient, load line, circuit editor หรือ FET

## เทส

```powershell
.\.venv\Scripts\python.exe -m unittest discover -v
```
