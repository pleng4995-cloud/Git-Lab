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

## อินพุต

| ช่อง | ความหมาย | หน่วย | ค่าเริ่มต้น |
|---|---|---|---|
| `VCC` | แหล่งจ่ายไฟ | V | 12 |
| `R1` | ตัวต้านทานตัวบน (VCC → base) | Ω | 47k |
| `R2` | ตัวต้านทานตัวล่าง (base → GND) | Ω | 10k |
| `RC` | ตัวต้านทาน collector | Ω | 2.2k |
| `RE` | ตัวต้านทาน emitter | Ω | 1k |
| `beta` | อัตราขยายกระแส `h_FE` | — | 150 |
| `VBE` | แรงดัน base-emitter | V | 0.7 |

ช่องตัวต้านทานรับ suffix `k` (×1e3) และ `M` (×1e6) เช่น `47000`, `47k`, `2.2k`, `1M`

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
