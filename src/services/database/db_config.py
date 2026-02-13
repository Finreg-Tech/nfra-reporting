import os
import logging
from dotenv import load_dotenv
from urllib.parse import urlparse

logger = logging.getLogger(__name__)

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL")

def get_db_components():
    logger.debug("Parsing DATABASE_URL")
    parsed = urlparse(DATABASE_URL)
    db_info = {
        "host": parsed.hostname,
        "port": parsed.port or 5432,
        "user": parsed.username,
        "password": parsed.password,
        "dbname": parsed.path.lstrip("/")
    }
    logger.debug("DB config loaded: host=%s, port=%s, dbname=%s", db_info["host"], db_info["port"], db_info["dbname"])
    return db_info
