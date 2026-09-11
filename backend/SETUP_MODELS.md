# Model Setup Guide — Gemini اور Groq

## خلاصہ

یہ ایپلیکیشن دونوں **Gemini** اور **Groq** کو سپورٹ کرتی ہے۔ ہر ماہ quota محدود ہے، تو Groq بہتر ہے بیشتر کے لیے۔

---

## 1. Gemini Setup

### API Key حاصل کریں:
1. https://ai.google.dev/gemini-api/docs/quickstart پر جائیں
2. "Get API key" بٹن دبائیں
3. اپنے Google Account سے sign in کریں
4. API key copy کریں

### .env میں شامل کریں:
```bash
GEMINI_API_KEY=your_api_key_here
GEMINI_MODEL=gemini-3.5-flash-lite
DEFAULT_PROVIDER=gemini
```

### Quota:
- **Free Tier:** 15 درخواستیں فی منٹ
- **Problem:** جب بہت سے tests ایک ساتھ چلیں تو 429 error ہوگا

---

## 2. Groq Setup (بہتر!)

### API Key حاصل کریں:
1. https://console.groq.com پر جائیں
2. Sign up کریں (یا login)
3. "API Keys" میں جائیں
4. نیا key بنائیں اور copy کریں

### .env میں شامل کریں:
```bash
GROQ_API_KEY=your_api_key_here
GROQ_BASE_URL=https://api.groq.com/openai/v1
GROQ_MODEL=llama-3.1-8b-instant
DEFAULT_PROVIDER=groq
```

### Quota:
- **Free Tier:** کوئی hard limit نہیں (لیکن rate limiting ہے)
- **Better:** زیادہ tests ایک ساتھ چلا سکتے ہو
- **Models:** llama-3.1-8b-instant, mixtral-8x7b-32768 (دونوں دستیاب)

---

## 3. Switch کریں Providers کے درمیان

### Gemini استعمال کریں:
```bash
DEFAULT_PROVIDER=gemini
```

### Groq استعمال کریں:
```bash
DEFAULT_PROVIDER=groq
```

---

## 4. Tests کے لیے Pacing

اگر quota issue آئے تو tests میں delay شامل کریں:

```python
import time

for test in tests:
    try:
        await test()
        time.sleep(2)  # 2 سیکنڈ انتظار
    except Exception as e:
        print(f"Failed: {e}")
        time.sleep(2)
```

---

## 5. Troubleshooting

### Error: "GEMINI_API_KEY is not set"
→ .env میں `GEMINI_API_KEY=` شامل کریں (خالی ہو سکتا ہے)

### Error: "429 Too Many Requests"
→ Gemini quota ختم ہوگیا۔ Groq switch کریں یا انتظار کریں۔

### Error: "GROQ_API_KEY is not set"
→ https://console.groq.com سے key حاصل کریں

### Model نہ ملا؟
→ `GROQ_MODEL` صحیح ہے: `llama-3.1-8b-instant` یا `mixtral-8x7b-32768`

---

## 6. تمام Model Options

### Gemini:
- `gemini-3.5-flash-lite` (تیز، مفت)
- `gemini-2.0-flash` (اگر دستیاب)

### Groq:
- `llama-3.1-8b-instant` (سفارش شدہ)
- `mixtral-8x7b-32768` (بڑا، سست)

---

## 7. ٹیسٹ کریں

```bash
# Gemini سے ٹیسٹ کریں
export DEFAULT_PROVIDER=gemini
python tests/test_flight_orchestrator_agent.py

# Groq سے ٹیسٹ کریں
export DEFAULT_PROVIDER=groq
python tests/test_booking_agent.py
```

---

**نوٹ:** .env فائل میں کوئی بھی API keys commit نہ کریں۔ `.gitignore` میں `.env` شامل ہے۔
