import logging
import sys
from app.database.connection import init_db
from app.ui.app import App
from app.config import settings

def setup_logging():
    logging.basicConfig(
        level=settings.LOG_LEVEL,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler("app.log"),
            logging.StreamHandler()
        ]
    )

def main():
    setup_logging()
    logging.info("Starting SocialGrowthAI...")

    # Initialize DB
    try:
        init_db()
    except Exception as e:
        logging.critical(f"Failed to initialize database: {e}")
        return

    # Start UI
    try:
        app = App()
        app.run()
    except Exception as e:
        logging.critical(f"Application crashed: {e}")
        # In a real app, show a message box here if UI fails
        sys.exit(1)

if __name__ == "__main__":
    main()
