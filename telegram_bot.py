"""
bot/telegram_bot.py – Telegram bot handler using python-telegram-bot v20+

Conversation Flow:
  /start → upload Resume PDF → upload JD PDF (or paste text) → receive score+suggestions
  /generate → receive optimized resume PDF
  /help → usage instructions
  /reset → clear user session
"""

import os
import logging
import asyncio
from pathlib import Path

from telegram import Update, Document
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    ContextTypes,
    filters,
    ConversationHandler,
)
from telegram.constants import ParseMode

from config import TELEGRAM_BOT_TOKEN, OUTPUT_DIR
from pdf_parser import extract_text_from_pdf
from nlp_engine import evaluate
from suggestion_engine import generate_suggestions, format_suggestions_message
from resume_generator import generate_optimized_resume
from helpers import (
    save_uploaded_file,
    format_evaluation_message,
    truncate_text,
)

logger = logging.getLogger(__name__)

# ── Conversation states ───────────────────────────────────────────────────────
WAITING_RESUME = 1
WAITING_JD = 2

# ── User session store (in-memory; replace with Redis for production) ─────────
# Structure: { user_id: { "resume_text": str, "jd_text": str, "eval_result": dict, "suggestions": list } }
user_sessions: dict = {}


# ── Helpers ───────────────────────────────────────────────────────────────────

async def _download_pdf(document: Document, context: ContextTypes.DEFAULT_TYPE) -> bytes:
    """Download a Telegram document and return its bytes."""
    file = await context.bot.get_file(document.file_id)
    return await file.download_as_bytearray()


async def _send_long_message(update: Update, text: str, parse_mode=ParseMode.MARKDOWN) -> None:
    """Split and send messages longer than Telegram's 4096-char limit."""
    max_len = 4000
    for i in range(0, len(text), max_len):
        chunk = text[i:i + max_len]
        await update.message.reply_text(chunk, parse_mode=parse_mode)
        await asyncio.sleep(0.3)


# ── Command Handlers ──────────────────────────────────────────────────────────

async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handle /start — welcome and reset session."""
    user = update.effective_user
    user_id = user.id
    user_sessions[user_id] = {}

    welcome = (
        f"👋 Welcome, *{user.first_name}*!\n\n"
        "I'm your *Resume Evaluator Bot* 🤖\n\n"
        "I'll analyze your resume against a job description and give you:\n"
        "  • 📊 A compatibility score (%)\n"
        "  • 💡 Targeted improvement suggestions\n"
        "  • 📄 An optimized resume PDF\n\n"
        "━━━━━━━━━━━━━━━━━━━━\n"
        "📎 *Step 1:* Upload your *Resume* as a PDF file.\n"
        "━━━━━━━━━━━━━━━━━━━━"
    )
    await update.message.reply_text(welcome, parse_mode=ParseMode.MARKDOWN)
    return WAITING_RESUME


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /help."""
    help_text = (
        "📚 *How to use Resume Evaluator Bot*\n\n"
        "1️⃣ Send `/start` to begin\n"
        "2️⃣ Upload your *Resume PDF*\n"
        "3️⃣ Upload the *Job Description PDF* (or type/paste the JD text)\n"
        "4️⃣ Receive your *match score* and *suggestions*\n"
        "5️⃣ Send `/generate` to get an *optimized resume PDF*\n\n"
        "📌 *Other commands:*\n"
        "  /reset — Clear your session and start over\n"
        "  /score — Re-show your last score\n"
        "  /help  — Show this message\n\n"
        "💡 *Tips:*\n"
        "  • Use text-based PDFs (not scanned images)\n"
        "  • You can paste the JD as plain text instead of uploading a PDF\n"
        "  • The bot supports multiple users simultaneously"
    )
    await update.message.reply_text(help_text, parse_mode=ParseMode.MARKDOWN)


async def reset_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handle /reset."""
    user_id = update.effective_user.id
    user_sessions[user_id] = {}
    await update.message.reply_text(
        "🔄 Session cleared! Send `/start` to begin a new evaluation.",
        parse_mode=ParseMode.MARKDOWN,
    )
    return WAITING_RESUME


async def score_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /score — re-show last evaluation."""
    user_id = update.effective_user.id
    session = user_sessions.get(user_id, {})
    eval_result = session.get("eval_result")

    if not eval_result:
        await update.message.reply_text(
            "No evaluation found. Please start with `/start` and upload your resume.",
            parse_mode=ParseMode.MARKDOWN,
        )
        return

    msg = format_evaluation_message(eval_result)
    await _send_long_message(update, msg)


async def generate_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /generate — create optimized resume PDF."""
    user_id = update.effective_user.id
    session = user_sessions.get(user_id, {})

    resume_text = session.get("resume_text", "")
    eval_result = session.get("eval_result")
    suggestions = session.get("suggestions", [])

    if not resume_text or not eval_result:
        await update.message.reply_text(
            "⚠️ Please evaluate your resume first.\n"
            "Send `/start` and upload both your resume and the job description.",
            parse_mode=ParseMode.MARKDOWN,
        )
        return

    await update.message.reply_text(
        "⚙️ Generating your optimized resume... please wait.",
        parse_mode=ParseMode.MARKDOWN,
    )

    try:
        pdf_path = generate_optimized_resume(
            resume_text=resume_text,
            eval_result=eval_result,
            suggestions=suggestions,
            user_id=user_id,
        )

        with open(pdf_path, "rb") as f:
            await update.message.reply_document(
                document=f,
                filename="Optimized_Resume.pdf",
                caption=(
                    "✅ *Your Optimized Resume is ready!*\n\n"
                    "📌 Key improvements applied:\n"
                    f"  • Added {len(eval_result.get('missing_skills', []))} missing skills highlighted\n"
                    f"  • Incorporated {len(eval_result.get('missing_keywords', []))} key JD terms\n"
                    "  • Professional formatting applied\n\n"
                    "_Review the optimization notes at the bottom of the PDF._"
                ),
                parse_mode=ParseMode.MARKDOWN,
            )
    except Exception as e:
        logger.error(f"Resume generation failed: {e}", exc_info=True)
        await update.message.reply_text(
            f"❌ Failed to generate resume: {str(e)}\nPlease try again.",
            parse_mode=ParseMode.MARKDOWN,
        )


# ── Conversation Handlers ─────────────────────────────────────────────────────

async def handle_resume_upload(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Receive and process the uploaded resume PDF."""
    user_id = update.effective_user.id
    document = update.message.document

    # Validate file type
    if not document or not document.file_name.lower().endswith(".pdf"):
        await update.message.reply_text(
            "⚠️ Please upload a *PDF file* for your resume.",
            parse_mode=ParseMode.MARKDOWN,
        )
        return WAITING_RESUME

    await update.message.reply_text("⏳ Processing your resume...")

    try:
        # Download and save
        pdf_bytes = await _download_pdf(document, context)
        temp_path = save_uploaded_file(bytes(pdf_bytes), user_id, "_resume.pdf")

        # Extract text
        resume_text = extract_text_from_pdf(temp_path)
        os.remove(temp_path)  # cleanup temp file

        if not resume_text or len(resume_text.strip()) < 50:
            await update.message.reply_text(
                "⚠️ Could not extract text from your resume PDF.\n"
                "Please ensure the PDF is *text-based* (not a scanned image).",
                parse_mode=ParseMode.MARKDOWN,
            )
            return WAITING_RESUME

        # Store in session
        user_sessions[user_id]["resume_text"] = resume_text

        word_count = len(resume_text.split())
        await update.message.reply_text(
            f"✅ Resume received! Extracted *{word_count} words*.\n\n"
            "━━━━━━━━━━━━━━━━━━━━\n"
            "📎 *Step 2:* Now upload the *Job Description PDF*, "
            "or simply *type/paste* the job description text.\n"
            "━━━━━━━━━━━━━━━━━━━━",
            parse_mode=ParseMode.MARKDOWN,
        )
        return WAITING_JD

    except Exception as e:
        logger.error(f"Resume processing error: {e}", exc_info=True)
        await update.message.reply_text(
            f"❌ Error processing resume: {str(e)}\nPlease try again.",
        )
        return WAITING_RESUME


async def handle_jd_upload(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Receive JD as a PDF file."""
    user_id = update.effective_user.id
    document = update.message.document

    if not document or not document.file_name.lower().endswith(".pdf"):
        await update.message.reply_text(
            "⚠️ Please upload a *PDF file* or type/paste the job description as text.",
            parse_mode=ParseMode.MARKDOWN,
        )
        return WAITING_JD

    await update.message.reply_text("⏳ Processing job description...")

    try:
        pdf_bytes = await _download_pdf(document, context)
        temp_path = save_uploaded_file(bytes(pdf_bytes), user_id, "_jd.pdf")
        jd_text = extract_text_from_pdf(temp_path)
        os.remove(temp_path)

        if not jd_text or len(jd_text.strip()) < 20:
            await update.message.reply_text(
                "⚠️ Could not extract text from the JD PDF. Please paste the text directly.",
            )
            return WAITING_JD

        await _run_evaluation(update, user_id, jd_text)
        return ConversationHandler.END

    except Exception as e:
        logger.error(f"JD processing error: {e}", exc_info=True)
        await update.message.reply_text(f"❌ Error: {str(e)}")
        return WAITING_JD


async def handle_jd_text(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Receive JD as plain text."""
    user_id = update.effective_user.id
    jd_text = update.message.text.strip()

    if len(jd_text) < 30:
        await update.message.reply_text(
            "⚠️ Job description is too short. Please paste the full text or upload a PDF.",
        )
        return WAITING_JD

    await update.message.reply_text("⏳ Analyzing your resume against the job description...")
    await _run_evaluation(update, user_id, jd_text)
    return ConversationHandler.END


async def _run_evaluation(update: Update, user_id: int, jd_text: str) -> None:
    """Core evaluation runner — called after both docs are received."""
    session = user_sessions.get(user_id, {})
    resume_text = session.get("resume_text", "")

    if not resume_text:
        await update.message.reply_text(
            "⚠️ No resume found in session. Please start again with /start.",
        )
        return

    try:
        # Store JD
        user_sessions[user_id]["jd_text"] = jd_text

        await update.message.reply_text("🔍 Running NLP analysis... this may take a moment.")

        # ── Evaluate ──────────────────────────────────────────────────────────
        eval_result = evaluate(resume_text, jd_text)
        suggestions = generate_suggestions(eval_result, resume_text)

        user_sessions[user_id]["eval_result"] = eval_result
        user_sessions[user_id]["suggestions"] = suggestions

        # ── Send score ────────────────────────────────────────────────────────
        score_msg = format_evaluation_message(eval_result)
        await _send_long_message(update, score_msg)

        # ── Send suggestions ──────────────────────────────────────────────────
        suggestions_msg = format_suggestions_message(suggestions)
        await _send_long_message(update, suggestions_msg)

        # ── Prompt for resume generation ──────────────────────────────────────
        await update.message.reply_text(
            "━━━━━━━━━━━━━━━━━━━━\n"
            "📄 Send `/generate` to receive an *optimized resume PDF*.\n"
            "🔄 Send `/reset` to start a new evaluation.\n"
            "━━━━━━━━━━━━━━━━━━━━",
            parse_mode=ParseMode.MARKDOWN,
        )

    except Exception as e:
        logger.error(f"Evaluation error: {e}", exc_info=True)
        await update.message.reply_text(
            f"❌ Evaluation failed: {str(e)}\nPlease try again with /start.",
        )


async def handle_unexpected_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Catch-all handler for unexpected messages."""
    await update.message.reply_text(
        "🤔 Not sure what to do with that.\n"
        "Send `/start` to begin an evaluation or `/help` for instructions.",
        parse_mode=ParseMode.MARKDOWN,
    )


# ── Application builder ───────────────────────────────────────────────────────

def build_application() -> Application:
    """Build and configure the Telegram bot application."""
    app = Application.builder().token(TELEGRAM_BOT_TOKEN).build()

    # Conversation handler (multi-step upload flow)
    conv_handler = ConversationHandler(
        entry_points=[CommandHandler("start", start_command)],
        states={
            WAITING_RESUME: [
                MessageHandler(filters.Document.PDF, handle_resume_upload),
                MessageHandler(filters.TEXT & ~filters.COMMAND, lambda u, c: u.message.reply_text(
                    "Please upload your *Resume as a PDF file* first.", parse_mode=ParseMode.MARKDOWN
                )),
            ],
            WAITING_JD: [
                MessageHandler(filters.Document.PDF, handle_jd_upload),
                MessageHandler(filters.TEXT & ~filters.COMMAND, handle_jd_text),
            ],
        },
        fallbacks=[
            CommandHandler("reset", reset_command),
            CommandHandler("start", start_command),
        ],
    )

    app.add_handler(conv_handler)
    app.add_handler(CommandHandler("help", help_command))
    app.add_handler(CommandHandler("reset", reset_command))
    app.add_handler(CommandHandler("score", score_command))
    app.add_handler(CommandHandler("generate", generate_command))
    app.add_handler(MessageHandler(filters.ALL, handle_unexpected_message))

    return app
