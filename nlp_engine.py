"""
core/nlp_engine.py – NLP matching and scoring engine.

Supports two backends:
  - tfidf  : TF-IDF + Cosine similarity (lightweight, no GPU needed)
  - sbert  : Sentence-BERT embeddings (higher accuracy, needs sentence-transformers)
"""

import re
import logging
from typing import Optional

from config import (
    NLP_BACKEND, SBERT_MODEL,
    SKILL_WEIGHT, EXPERIENCE_WEIGHT, KEYWORD_WEIGHT,
    TECH_SKILLS_KEYWORDS, EXPERIENCE_KEYWORDS,
)

logger = logging.getLogger(__name__)


# ── Lazy-loaded SBERT model ───────────────────────────────────────────────────
_sbert_model = None

def _get_sbert_model():
    global _sbert_model
    if _sbert_model is None:
        try:
            from sentence_transformers import SentenceTransformer
            _sbert_model = SentenceTransformer(SBERT_MODEL)
            logger.info("SBERT model loaded.")
        except ImportError:
            logger.warning("sentence-transformers not installed; falling back to TF-IDF.")
    return _sbert_model


# ── Similarity helpers ────────────────────────────────────────────────────────

def _cosine_tfidf(text_a: str, text_b: str) -> float:
    """Compute cosine similarity between two texts using TF-IDF."""
    from sklearn.feature_extraction.text import TfidfVectorizer
    from sklearn.metrics.pairwise import cosine_similarity

    vectorizer = TfidfVectorizer(stop_words="english", ngram_range=(1, 2))
    try:
        tfidf_matrix = vectorizer.fit_transform([text_a, text_b])
        score = cosine_similarity(tfidf_matrix[0:1], tfidf_matrix[1:2])[0][0]
        return float(score)
    except Exception as e:
        logger.error(f"TF-IDF error: {e}")
        return 0.0


def _cosine_sbert(text_a: str, text_b: str) -> float:
    """Compute cosine similarity using Sentence-BERT embeddings."""
    model = _get_sbert_model()
    if model is None:
        return _cosine_tfidf(text_a, text_b)

    from sklearn.metrics.pairwise import cosine_similarity
    import numpy as np

    emb_a = model.encode([text_a])
    emb_b = model.encode([text_b])
    score = cosine_similarity(emb_a, emb_b)[0][0]
    return float(score)


def compute_similarity(text_a: str, text_b: str) -> float:
    """Dispatch to the configured NLP backend."""
    if NLP_BACKEND == "sbert":
        return _cosine_sbert(text_a, text_b)
    return _cosine_tfidf(text_a, text_b)


# ── Skill extraction ──────────────────────────────────────────────────────────

def extract_skills(text: str) -> set:
    """Extract known tech/skill keywords from text."""
    text_lower = text.lower()
    found = set()
    for skill in TECH_SKILLS_KEYWORDS:
        # Word-boundary aware match
        pattern = r"\b" + re.escape(skill) + r"\b"
        if re.search(pattern, text_lower):
            found.add(skill)
    return found


def extract_experience_level(text: str) -> Optional[str]:
    """Attempt to infer seniority level from text."""
    text_lower = text.lower()
    levels = {
        "intern": ["intern", "internship", "trainee"],
        "junior": ["junior", "entry level", "entry-level", "fresher"],
        "mid": ["mid-level", "mid level", "2 years", "3 years"],
        "senior": ["senior", "5 years", "6 years", "7 years", "8 years"],
        "lead": ["lead", "principal", "staff", "architect"],
        "manager": ["manager", "director", "head of"],
    }
    for level, keywords in levels.items():
        for kw in keywords:
            if kw in text_lower:
                return level
    return None


def extract_years_of_experience(text: str) -> int:
    """Try to extract max years of experience mentioned."""
    patterns = [
        r"(\d+)\+?\s*years?\s+of\s+experience",
        r"(\d+)\+?\s*years?\s+experience",
        r"experience\s+of\s+(\d+)\+?\s*years?",
    ]
    max_years = 0
    for pat in patterns:
        matches = re.findall(pat, text.lower())
        for m in matches:
            try:
                max_years = max(max_years, int(m))
            except ValueError:
                pass
    return max_years


# ── Core scoring ──────────────────────────────────────────────────────────────

def compute_skill_match(resume_text: str, jd_text: str) -> dict:
    """
    Returns dict with:
      score      : float 0–1
      matched    : set of matched skills
      missing    : set of skills in JD not in resume
    """
    resume_skills = extract_skills(resume_text)
    jd_skills = extract_skills(jd_text)

    if not jd_skills:
        # No identifiable skills in JD; fall back to TF-IDF
        sim = _cosine_tfidf(resume_text, jd_text)
        return {"score": sim, "matched": set(), "missing": set(), "jd_skills": set()}

    matched = resume_skills & jd_skills
    missing = jd_skills - resume_skills
    score = len(matched) / len(jd_skills)

    return {
        "score": score,
        "matched": matched,
        "missing": missing,
        "jd_skills": jd_skills,
    }


def compute_experience_match(resume_text: str, jd_text: str) -> dict:
    """
    Returns dict with:
      score          : float 0–1
      resume_years   : int
      required_years : int
    """
    resume_years = extract_years_of_experience(resume_text)
    required_years = extract_years_of_experience(jd_text)

    # Seniority-level semantic similarity
    resume_level = extract_experience_level(resume_text)
    jd_level = extract_experience_level(jd_text)

    level_order = ["intern", "junior", "mid", "senior", "lead", "manager"]

    if required_years > 0 and resume_years > 0:
        ratio = min(resume_years / required_years, 1.0)
    elif resume_level and jd_level:
        try:
            ri = level_order.index(resume_level)
            ji = level_order.index(jd_level)
            ratio = 1.0 if ri >= ji else (ri + 1) / (ji + 1)
        except ValueError:
            ratio = 0.5
    else:
        # Fall back to text similarity for experience section
        ratio = compute_similarity(resume_text[:2000], jd_text[:2000]) * 0.8 + 0.2

    return {
        "score": min(ratio, 1.0),
        "resume_years": resume_years,
        "required_years": required_years,
        "resume_level": resume_level,
        "jd_level": jd_level,
    }


def compute_keyword_match(resume_text: str, jd_text: str) -> dict:
    """Semantic / keyword overlap using chosen NLP backend."""
    sim = compute_similarity(resume_text, jd_text)

    # Extract JD-specific keywords not in resume
    jd_words = set(re.findall(r"\b[a-zA-Z]{4,}\b", jd_text.lower()))
    resume_words = set(re.findall(r"\b[a-zA-Z]{4,}\b", resume_text.lower()))

    common_stop = {
        "this", "that", "with", "have", "will", "from", "they",
        "been", "more", "also", "your", "their", "what", "when",
        "work", "team", "role", "like", "need", "must", "able",
    }
    missing_keywords = (jd_words - resume_words) - common_stop
    # Keep only the top 10 most significant
    missing_keywords = set(list(missing_keywords)[:10])

    return {
        "score": sim,
        "missing_keywords": missing_keywords,
    }


# ── Master scoring function ───────────────────────────────────────────────────

def evaluate(resume_text: str, jd_text: str) -> dict:
    """
    Full evaluation of resume vs job description.
    
    Returns a rich result dict:
    {
      "total_score": float (0–100),
      "skill_score": float (0–100),
      "experience_score": float (0–100),
      "keyword_score": float (0–100),
      "matched_skills": list,
      "missing_skills": list,
      "missing_keywords": list,
      "resume_years": int,
      "required_years": int,
      "resume_level": str | None,
      "jd_level": str | None,
    }
    """
    skill_result = compute_skill_match(resume_text, jd_text)
    exp_result = compute_experience_match(resume_text, jd_text)
    kw_result = compute_keyword_match(resume_text, jd_text)

    total = (
        skill_result["score"] * SKILL_WEIGHT +
        exp_result["score"] * EXPERIENCE_WEIGHT +
        kw_result["score"] * KEYWORD_WEIGHT
    ) * 100

    return {
        "total_score": round(total, 1),
        "skill_score": round(skill_result["score"] * 100, 1),
        "experience_score": round(exp_result["score"] * 100, 1),
        "keyword_score": round(kw_result["score"] * 100, 1),
        "matched_skills": sorted(skill_result["matched"]),
        "missing_skills": sorted(skill_result["missing"]),
        "missing_keywords": sorted(kw_result["missing_keywords"]),
        "resume_years": exp_result["resume_years"],
        "required_years": exp_result["required_years"],
        "resume_level": exp_result["resume_level"],
        "jd_level": exp_result["jd_level"],
    }
