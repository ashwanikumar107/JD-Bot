"""
config.py – Central configuration for Resume Evaluator Bot
"""

import os
from dotenv import load_dotenv

load_dotenv()

# ── Telegram ──────────────────────────────────────────────────────────────────
TELEGRAM_BOT_TOKEN: str = os.getenv("TELEGRAM_BOT_TOKEN", "")

if not TELEGRAM_BOT_TOKEN:
    raise EnvironmentError(
        "TELEGRAM_BOT_TOKEN is not set.\n"
        "1. Create a bot via @BotFather on Telegram.\n"
        "2. Copy the token into your .env file:\n"
        "   TELEGRAM_BOT_TOKEN=<your_token>"
    )

# ── Scoring ───────────────────────────────────────────────────────────────────
SCORE_THRESHOLD: int = int(os.getenv("SCORE_THRESHOLD", "70"))

SKILL_WEIGHT: float = 0.50
EXPERIENCE_WEIGHT: float = 0.30
KEYWORD_WEIGHT: float = 0.20

# ── NLP ───────────────────────────────────────────────────────────────────────
NLP_BACKEND: str = os.getenv("NLP_BACKEND", "tfidf")   # "tfidf" | "sbert"
SBERT_MODEL: str = "all-MiniLM-L6-v2"

# ── File handling ─────────────────────────────────────────────────────────────
OUTPUT_DIR: str = os.getenv("OUTPUT_DIR", "output")
os.makedirs(OUTPUT_DIR, exist_ok=True)

MAX_FILE_SIZE_MB: int = 10

# ── Common tech / skill keywords ─────────────────────────────────────────────
TECH_SKILLS_KEYWORDS = [
    # Languages
    "python", "java", "javascript", "typescript", "c++", "c#", "golang", "rust",
    "ruby", "php", "swift", "kotlin", "scala", "r", "matlab",
    # Web
    "react", "angular", "vue", "node.js", "django", "flask", "fastapi", "spring",
    "express", "next.js", "rest api", "graphql", "html", "css",
    # Data / ML
    "machine learning", "deep learning", "nlp", "tensorflow", "pytorch",
    "scikit-learn", "pandas", "numpy", "spark", "hadoop", "data analysis",
    "sql", "nosql", "mongodb", "postgresql", "mysql", "redis",
    # Cloud / DevOps
    "aws", "azure", "gcp", "docker", "kubernetes", "ci/cd", "terraform",
    "jenkins", "github actions", "linux",
    # Soft skills
    "communication", "leadership", "teamwork", "problem solving",
    "agile", "scrum", "project management",
]

EXPERIENCE_KEYWORDS = [
    "years of experience", "year experience", "years experience",
    "senior", "junior", "mid-level", "lead", "principal", "staff",
    "manager", "director", "architect", "engineer", "developer",
    "intern", "associate",
]

ACTION_VERBS = [
    "developed", "implemented", "designed", "built", "created",
    "optimized", "improved", "increased", "reduced", "delivered",
    "managed", "led", "architected", "automated", "deployed",
    "maintained", "collaborated", "analyzed", "migrated", "scaled",
]
