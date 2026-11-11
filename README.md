DC Circuit Calculator

วัตถุประสงค์: โปรแกรมคำนวณและวิเคราะห์วงจรไฟฟ้ากระแสตรง (DC) แบบอนุกรม ขนาน และผสม โดยผู้ใช้เพียงระบุค่าความต่างศักย์และแรงต้านทาน ระบบจะคำนวณหาค่ากระแสไฟฟ้ารวม (Current) และกำลังไฟฟ้า (Power) ของแต่ละอุปกรณ์ให้อัตโนมัติ เพื่อช่วยให้ผู้เรียนเข้าใจกฎของโอมห์และวิเคราะห์วงจรได้อย่างแม่นยำ

## BJT Common-Emitter DC Bias (Flask web app)

โฟลเดอร์ [`bjt_bias/`](bjt_bias/README.md) มีเว็บแอป Flask สำหรับคำนวณ
DC operating point ของ BJT common-emitter แบบ voltage-divider bias
พร้อมตรวจผลด้วย nodal analysis ที่เป็นอิสระจากสูตรหลัก

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe -m bjt_bias.app
```

เปิด <http://127.0.0.1:5000> — รายละเอียดสูตรและข้อจำกัดดูที่
[`bjt_bias/README.md`](bjt_bias/README.md)