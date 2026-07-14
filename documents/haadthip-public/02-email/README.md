# 02 — Email

Email setup, configuration, and management Documents for Microsoft Exchange / O365.

## Documents

| File | Content |
|------|---------|
| `Eng_Manual Import Email backup for Exchange profile.pdf` | Import email backup for Exchange |
| `Eng_Microsoft Exchange Email Setup Guide on your iPhone_Eng.pdf` | Exchange email setup on iPhone |
| `คู่มือ Setup Email O365 บนมือถือ_Android.pdf` | O365 email setup on Android (TH) |
| `คู่มือ Setup Email O365 บนมือถือ_IOS.pdf` | O365 email setup on iOS (TH) |
| `คู่มือการเพิ่มโฟลเดอร์อีเมลเก่ามาเก็บไว.pdf` | Archive old email folders (TH) |
| `คู่มือการใช้งานระบบคัดกรองอีเมล #SpamTitan.pdf` | SpamTitan email filter guide (TH) |
| `คู่มือใช้งานระบบ Email ฉบับ TH.pdf` | Email system usage guide (TH) |

**Total: 7 Documents**

## Pipeline Notes

- Heavily bilingual (2 EN, 5 TH) → test Pipeline with Thai-language Content Understanding.
- Many Documents share overlapping topics (O365 mobile setup for iOS vs Android) → expect similar **Summary** outputs; consider deduplication at the Data Hook layer.
- **Data Hook** opportunity: extract platform-specific setup steps into a structured FAQ table for an IT self-service portal.
