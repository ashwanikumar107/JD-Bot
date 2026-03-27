# 🤖 Resume Evaluator Telegram Bot

An intelligent chatbot that evaluates resumes against job descriptions, generates match scores, provides suggestions, and creates optimized resumes — all via Telegram.

---

## 📁 Project Structure

```
resume_bot/
├── bot/
│   └── telegram_bot.py        # Telegram bot handler
├── core/
│   ├── pdf_parser.py          # PDF text extraction
│   ├── nlp_engine.py          # NLP matching & scoring
│   ├── suggestion_engine.py   # Improvement suggestions
│   └── resume_generator.py    # PDF resume builder
├── utils/
│   └── helpers.py             # Utility functions
├── config.py                  # Configuration & constants
├── main.py                    # Entry point
├── requirements.txt           # Dependencies
└── .env.example               # Environment variables template
```

---

## ⚙️ Setup Instructions

### 1. Clone / Download the project

### 2. Install dependencies
```bash
pip install -r requirements.txt
```

### 3. Create a Telegram Bot
1. Open Telegram and search for **@BotFather**
2. Send `/newbot` and follow the prompts
3. Copy the **API token** you receive

### 4. Configure environment
```bash
cp .env.example .env
# Edit .env and paste your Telegram bot token
```

### 5. Run the bot
```bash
python main.py
```

---

## 🎮 How to Use the Bot

| Step | Action |
|------|--------|
| 1 | Send `/start` to begin |
| 2 | Upload your **Resume PDF** |
| 3 | Upload the **Job Description PDF** (or paste text) |
| 4 | Receive **match score + suggestions** |
| 5 | Send `/generate` to get an **optimized resume PDF** |

---

## 🧠 Scoring Calculating Formula

```
Score = (Skill Match × 0.50) + (Experience Match × 0.30) + (Keyword Match × 0.20)
```

---

## 🔧 Tech Stack

| Component | Technology |
|-----------|------------|
| Bot Framework | python-telegram-bot |
| PDF Extraction | pdfplumber, pypdf |
| NLP / Matching | scikit-learn (TF-IDF + Cosine), sentence-transformers |
| PDF Generation | reportlab |
| Backend | Python (async) |
| Config | python-dotenv |

---

## 📌 Notes

- Resume PDF must be text-based (not scanned images)
- Job Description can be PDF or plain text
- Generated resume is saved in the `output/` folder
- Bot supports multiple users simultaneously via async handlers
