"""
utils/helpers.py – Shared utility functions
"""

import os
import re
import hashlib
import logging
from datetime import datetime

logger = logging.getLogger(__name__)


def save_uploaded_file(file_bytes: bytes, user_id: int, suffix: str = ".pdf") -> str:
    """
    Save an uploaded file to the output directory.
    Returns the file path.
    """
    from config import OUTPUT_DIR
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"{user_id}_{timestamp}{suffix}"
    path = os.path.join(OUTPUT_DIR, filename)
    with open(path, "wb") as f:
        f.write(file_bytes)
    return path


def cleanup_old_files(directory: str, max_age_hours: int = 24) -> None:
    """Remove files older than max_age_hours from the directory."""
    import time
    now = time.time()
    max_age_seconds = max_age_hours * 3600
    for fname in os.listdir(directory):
        fpath = os.path.join(directory, fname)
        if os.path.isfile(fpath):
            age = now - os.path.getmtime(fpath)
            if age > max_age_seconds:
                os.remove(fpath)
                logger.info(f"Cleaned up old file: {fpath}")


def format_score_bar(score: float, width: int = 20) -> str:
    """Create a visual ASCII progress bar for a score 0–100."""
    filled = int((score / 100) * width)
    bar = "█" * filled + "░" * (width - filled)
    return f"[{bar}] {score:.1f}%"


def score_to_emoji(score: float) -> str:
    if score >= 85:
        return "🟢"
    elif score >= 70:
        return "🟡"
    elif score >= 50:
        return "🟠"
    else:
        return "🔴"


def format_evaluation_message(eval_result: dict) -> str:
    """
    Format the evaluation result dict into a rich Telegram message.
    """
    score = eval_result["total_score"]
    emoji = score_to_emoji(score)

    lines = [
        f"📊 *Resume Evaluation Results*\n",
        f"{emoji} *Overall Match Score: {score}%*",
        format_score_bar(score),
        "",
        "📈 *Score Breakdown:*",
        f"  🛠 Skills Match:     {format_score_bar(eval_result['skill_score'], 15)}",
        f"  💼 Experience Match: {format_score_bar(eval_result['experience_score'], 15)}",
        f"  🔑 Keyword Match:    {format_score_bar(eval_result['keyword_score'], 15)}",
        "",
    ]

    # Matched skills
    if eval_result["matched_skills"]:
        matched = ", ".join(f"`{s}`" for s in eval_result["matched_skills"][:8])
        lines.append(f"✅ *Matched Skills:* {matched}")
        lines.append("")

    # Missing skills
    if eval_result["missing_skills"]:
        missing = ", ".join(f"`{s}`" for s in eval_result["missing_skills"][:6])
        lines.append(f"❌ *Missing Skills:* {missing}")
        lines.append("")

    # Experience info
    if eval_result["required_years"] > 0:
        lines.append(
            f"📅 *Experience:* Resume: {eval_result['resume_years']} yrs | "
            f"Required: {eval_result['required_years']} yrs"
        )
        lines.append("")

    lines.append("_Send /generate to get an optimized resume PDF_")

    return "\n".join(lines)


def sanitize_filename(name: str) -> str:
    return re.sub(r"[^\w\-_.]", "_", name)


def truncate_text(text: str, max_chars: int = 4000) -> str:
    if len(text) <= max_chars:
        return text
    return text[:max_chars] + "\n...[truncated]"
