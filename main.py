import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import logging

logging.basicConfig(
    format="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
    level=logging.INFO,
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler("bot.log", encoding="utf-8"),
    ],
)
logger = logging.getLogger(__name__)


def check_dependencies():
    required = {
        "telegram": "python-telegram-bot",
        "pdfplumber": "pdfplumber",
        "reportlab": "reportlab",
        "sklearn": "scikit-learn",
    }
    missing = []
    for module, package in required.items():
        try:
            __import__(module)
        except ImportError:
            missing.append(package)

    if missing:
        logger.error(f"Missing: {', '.join(missing)}")
        sys.exit(1)

    try:
        import sentence_transformers
        logger.info("sentence-transformers available")
    except ImportError:
        logger.info("sentence-transformers not found — using TF-IDF backend (fine for most use cases)")


def main():
    logger.info("=" * 60)
    logger.info("  Resume Evaluator Bot — Starting up")
    logger.info("=" * 60)

    check_dependencies()

    from telegram_bot import build_application

    app = build_application()

    logger.info("Bot is running. Press Ctrl+C to stop.")
    logger.info("Connect to your bot on Telegram and send /start")

    app.run_polling(
        allowed_updates=["message", "callback_query"],
        drop_pending_updates=True,
    )


if __name__ == "__main__":
    main()