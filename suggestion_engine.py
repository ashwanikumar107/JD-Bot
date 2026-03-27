"""
core/suggestion_engine.py – Generate actionable improvement suggestions.
"""

import re
from config import SCORE_THRESHOLD, ACTION_VERBS


def generate_suggestions(eval_result: dict, resume_text: str) -> list[str]:
    """
    Generate a list of concrete improvement suggestions based on evaluation.

    Args:
        eval_result : Output of nlp_engine.evaluate()
        resume_text : Raw resume text

    Returns:
        List of suggestion strings (markdown-friendly).
    """
    suggestions = []

    score = eval_result["total_score"]
    missing_skills = eval_result["missing_skills"]
    missing_keywords = eval_result["missing_keywords"]
    skill_score = eval_result["skill_score"]
    exp_score = eval_result["experience_score"]
    kw_score = eval_result["keyword_score"]
    resume_years = eval_result["resume_years"]
    required_years = eval_result["required_years"]

    # ── 1. Missing skills ─────────────────────────────────────────────────────
    if missing_skills:
        top_missing = missing_skills[:6]
        skill_list = ", ".join(f"`{s}`" for s in top_missing)
        suggestions.append(
            f"🛠 *Add Missing Skills*: The JD requires skills not found in your resume: {skill_list}. "
            f"Add these to your Skills section if you have experience with them."
        )

    # ── 2. Low skill score ────────────────────────────────────────────────────
    if skill_score < 50 and not missing_skills:
        suggestions.append(
            "🛠 *Expand Your Skills Section*: Your Skills section seems sparse. "
            "List all relevant technologies, frameworks, and tools you've used."
        )

    # ── 3. Experience gap ─────────────────────────────────────────────────────
    if required_years > 0 and resume_years < required_years:
        gap = required_years - resume_years
        suggestions.append(
            f"📅 *Experience Gap*: The role requires {required_years} years of experience "
            f"but your resume indicates ~{resume_years} years. "
            f"Consider highlighting project impact and scope to bridge the {gap}-year gap."
        )
    elif exp_score < 50:
        suggestions.append(
            "📅 *Strengthen Experience Descriptions*: Your experience section could better align "
            "with the job requirements. Quantify achievements (e.g., 'Reduced load time by 40%')."
        )

    # ── 4. Missing keywords ───────────────────────────────────────────────────
    if missing_keywords:
        kw_list = ", ".join(f"`{k}`" for k in list(missing_keywords)[:8])
        suggestions.append(
            f"🔑 *Add JD Keywords*: Incorporate these keywords from the job description "
            f"to improve ATS matching: {kw_list}."
        )

    # ── 5. Action verbs ───────────────────────────────────────────────────────
    resume_lower = resume_text.lower()
    used_verbs = [v for v in ACTION_VERBS if v in resume_lower]
    if len(used_verbs) < 5:
        missing_verbs = [v for v in ACTION_VERBS[:10] if v not in used_verbs][:5]
        verb_list = ", ".join(f"*{v.title()}*" for v in missing_verbs)
        suggestions.append(
            f"✍️ *Use Strong Action Verbs*: Start bullet points with impactful verbs like {verb_list}. "
            f"This makes your contributions clearer and more compelling."
        )

    # ── 6. Quantify achievements ──────────────────────────────────────────────
    numbers_count = len(re.findall(r"\b\d+[%x]?\b", resume_text))
    if numbers_count < 5:
        suggestions.append(
            "📊 *Quantify Your Achievements*: Add measurable results to your experience bullets. "
            "Examples: 'Improved performance by 30%', 'Managed a team of 8 engineers', "
            "'Reduced deployment time from 2 hours to 15 minutes'."
        )

    # ── 7. Summary / Objective ────────────────────────────────────────────────
    has_summary = bool(re.search(
        r"(?i)(summary|objective|profile|about me)", resume_text
    ))
    if not has_summary:
        suggestions.append(
            "📝 *Add a Professional Summary*: A 3–4 line summary at the top of your resume "
            "tailored to this specific role can significantly improve recruiter engagement."
        )

    # ── 8. Overall score feedback ─────────────────────────────────────────────
    if score >= 85:
        suggestions.insert(0,
            "🌟 *Strong Match!* Your resume aligns well with this job. "
            "Minor keyword tweaks could push you to the top of the pile."
        )
    elif score >= SCORE_THRESHOLD:
        suggestions.insert(0,
            f"✅ *Good Match ({score}%)* — A few targeted improvements could make your resume stand out."
        )
    else:
        suggestions.insert(0,
            f"⚠️ *Below Threshold ({score}%)* — Your resume needs significant tailoring for this role. "
            f"Focus on the suggestions below to improve your chances."
        )

    # ── 9. Formatting tips ────────────────────────────────────────────────────
    line_count = len(resume_text.split("\n"))
    word_count = len(resume_text.split())

    if word_count < 200:
        suggestions.append(
            "📄 *Expand Your Resume*: Your resume appears quite short (<200 words). "
            "Add more detail to your experience, projects, and skills sections."
        )
    elif word_count > 1200:
        suggestions.append(
            "✂️ *Trim Your Resume*: Your resume is quite long. "
            "Aim for 1 page (junior) or 2 pages (senior). Remove outdated or irrelevant content."
        )

    return suggestions


def format_suggestions_message(suggestions: list[str]) -> str:
    """Format suggestions into a readable Telegram message."""
    if not suggestions:
        return "✅ No major improvements needed — great match!"

    lines = ["*💡 Improvement Suggestions:*\n"]
    for i, suggestion in enumerate(suggestions, 1):
        lines.append(f"{i}. {suggestion}\n")

    return "\n".join(lines)
