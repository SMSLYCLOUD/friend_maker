import uvicorn

from app.config import settings


def main():
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8000,
        log_level=settings.LOG_LEVEL.lower(),
    )


if __name__ == "__main__":
    main()
