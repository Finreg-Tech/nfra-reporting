import logging
import psycopg2
from psycopg2 import sql
from src.services.database.db_config import get_db_components

logger = logging.getLogger(__name__)

EMBEDDING_DIM = 384

def create_database_if_not_exists():
    db_info = get_db_components()
    logger.info("Checking if database '%s' exists...", db_info["dbname"])
    
    conn = psycopg2.connect(
        host=db_info["host"],
        port=db_info["port"],
        user=db_info["user"],
        password=db_info["password"],
        dbname="postgres"
    )
    conn.autocommit = True
    cursor = conn.cursor()
    
    cursor.execute(
        "SELECT 1 FROM pg_database WHERE datname = %s",
        (db_info["dbname"],)
    )
    exists = cursor.fetchone()
    
    if not exists:
        logger.info("Database '%s' does not exist. Creating...", db_info["dbname"])
        cursor.execute(
            sql.SQL("CREATE DATABASE {}").format(
                sql.Identifier(db_info["dbname"])
            )
        )
        logger.info("Database '%s' created successfully", db_info["dbname"])
    else:
        logger.info("Database '%s' already exists", db_info["dbname"])
    
    cursor.close()
    conn.close()

def create_tables():
    db_info = get_db_components()
    logger.info("Creating tables and extensions if not exist...")
    
    conn = psycopg2.connect(
        host=db_info["host"],
        port=db_info["port"],
        user=db_info["user"],
        password=db_info["password"],
        dbname=db_info["dbname"]
    )
    cursor = conn.cursor()
    
    logger.info("Enabling pgvector extension...")
    cursor.execute("CREATE EXTENSION IF NOT EXISTS vector;")
    
    cursor.execute(f"""
        CREATE TABLE IF NOT EXISTS rules (
            id SERIAL PRIMARY KEY,
            document_type TEXT NOT NULL,
            standard_code TEXT NOT NULL,
            standard_number INTEGER,
            standard_name TEXT,
            section_name TEXT,
            section_order INTEGER,
            page_number INTEGER,
            chunk TEXT,
            actual_text TEXT,
            embedding vector({EMBEDDING_DIM})
        );
    """)
    
    cursor.execute("""
        SELECT column_name FROM information_schema.columns 
        WHERE table_name = 'rules' AND column_name = 'page_number';
    """)
    if not cursor.fetchone():
        logger.info("Adding page_number column to existing table...")
        cursor.execute("ALTER TABLE rules ADD COLUMN page_number INTEGER;")
    
    cursor.execute("""
        SELECT column_name FROM information_schema.columns 
        WHERE table_name = 'rules' AND column_name = 'embedding';
    """)
    if not cursor.fetchone():
        logger.info("Adding embedding column to existing table...")
        cursor.execute(f"ALTER TABLE rules ADD COLUMN embedding vector({EMBEDDING_DIM});")
    
    logger.info("Creating vector index...")
    cursor.execute("""
        CREATE INDEX IF NOT EXISTS rules_embedding_idx 
        ON rules USING ivfflat (embedding vector_cosine_ops)
        WITH (lists = 100);
    """)
    
    conn.commit()
    cursor.close()
    conn.close()
    logger.info("Tables and vector extension created/verified successfully")

def init_db():
    logger.info("Initializing database...")
    create_database_if_not_exists()
    create_tables()
    logger.info("Database initialization complete")
