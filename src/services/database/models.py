import logging
import psycopg2
from pgvector.psycopg2 import register_vector
from typing import List, Dict, Optional
from src.services.database.db_config import get_db_components

logger = logging.getLogger(__name__)

def get_connection():
    db_info = get_db_components()
    logger.debug("Establishing database connection...")
    conn = psycopg2.connect(
        host=db_info["host"],
        port=db_info["port"],
        user=db_info["user"],
        password=db_info["password"],
        dbname=db_info["dbname"]
    )
    register_vector(conn)
    return conn

def insert_rule(
    document_type: str,
    standard_code: str,
    standard_number: Optional[int],
    standard_name: Optional[str],
    section_name: Optional[str],
    section_order: Optional[int],
    page_number: Optional[int],
    chunk: str,
    actual_text: str
) -> int:
    conn = get_connection()
    cursor = conn.cursor()
    
    cursor.execute("""
        INSERT INTO rules (
            document_type, standard_code, standard_number, standard_name,
            section_name, section_order, page_number, chunk, actual_text
        ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
        RETURNING id;
    """, (
        document_type, standard_code, standard_number, standard_name,
        section_name, section_order, page_number, chunk, actual_text
    ))
    
    rule_id = cursor.fetchone()[0]
    conn.commit()
    cursor.close()
    conn.close()
    return rule_id

def insert_rules_batch(rules: List[Dict]) -> int:
    logger.info("Inserting batch of %d rules...", len(rules))
    conn = get_connection()
    cursor = conn.cursor()
    
    for idx, rule in enumerate(rules):
        logger.debug("Inserting rule %d: %s - %s (page %s)", idx + 1, rule.get("standard_code"), rule.get("section_name"), rule.get("page_number"))
        embedding = rule.get("embedding")
        if embedding:
            cursor.execute("""
                INSERT INTO rules (
                    document_type, standard_code, standard_number, standard_name,
                    section_name, section_order, page_number, chunk, actual_text, embedding
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s);
            """, (
                rule["document_type"],
                rule["standard_code"],
                rule.get("standard_number"),
                rule.get("standard_name"),
                rule.get("section_name"),
                rule.get("section_order"),
                rule.get("page_number"),
                rule["chunk"],
                rule["actual_text"],
                embedding
            ))
        else:
            cursor.execute("""
                INSERT INTO rules (
                    document_type, standard_code, standard_number, standard_name,
                    section_name, section_order, page_number, chunk, actual_text
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s);
            """, (
                rule["document_type"],
                rule["standard_code"],
                rule.get("standard_number"),
                rule.get("standard_name"),
                rule.get("section_name"),
                rule.get("section_order"),
                rule.get("page_number"),
                rule["chunk"],
                rule["actual_text"]
            ))
    
    conn.commit()
    cursor.close()
    conn.close()
    logger.info("Successfully inserted %d rules", len(rules))
    return len(rules)

def query_rules(
    document_type: str,
    standard_code: str,
    standard_number: Optional[int] = None,
    section_name: Optional[str] = None,
    section_order: Optional[int] = None,
    page_number: Optional[int] = None
) -> List[Dict]:
    logger.info("Querying rules: document_type=%s, standard_code=%s", document_type, standard_code)
    if standard_number:
        logger.debug("Filter: standard_number=%s", standard_number)
    if section_name:
        logger.debug("Filter: section_name=%s", section_name)
    if section_order:
        logger.debug("Filter: section_order=%s", section_order)
    if page_number:
        logger.debug("Filter: page_number=%s", page_number)
    
    conn = get_connection()
    cursor = conn.cursor()
    
    query = """
        SELECT id, document_type, standard_code, standard_number, standard_name,
               section_name, section_order, page_number, chunk, actual_text
        FROM rules
        WHERE document_type = %s AND standard_code = %s
    """
    params = [document_type, standard_code]
    
    if standard_number is not None:
        query += " AND standard_number = %s"
        params.append(standard_number)
    
    if section_name is not None:
        query += " AND section_name ILIKE %s"
        params.append(f"%{section_name}%")
    
    if section_order is not None:
        query += " AND section_order = %s"
        params.append(section_order)
    
    if page_number is not None:
        query += " AND page_number = %s"
        params.append(page_number)
    
    query += " ORDER BY section_order ASC;"
    
    cursor.execute(query, params)
    rows = cursor.fetchall()
    
    result = []
    for row in rows:
        result.append({
            "id": row[0],
            "document_type": row[1],
            "standard_code": row[2],
            "standard_number": row[3],
            "standard_name": row[4],
            "section_name": row[5],
            "section_order": row[6],
            "page_number": row[7],
            "chunk": row[8],
            "actual_text": row[9]
        })
    
    cursor.close()
    conn.close()
    logger.info("Query returned %d results", len(result))
    return result

def vector_search(
    query_embedding: List[float],
    top_k: int = 5,
    document_type: Optional[str] = None,
    standard_code: Optional[str] = None
) -> List[Dict]:
    logger.info("Performing vector search with top_k=%d", top_k)
    if document_type:
        logger.debug("Filter: document_type=%s", document_type)
    if standard_code:
        logger.debug("Filter: standard_code=%s", standard_code)
    
    conn = get_connection()
    cursor = conn.cursor()
    
    query = """
        SELECT id, document_type, standard_code, standard_number, standard_name,
               section_name, section_order, page_number, chunk, actual_text,
               1 - (embedding <=> %s::vector) as similarity
        FROM rules
        WHERE embedding IS NOT NULL
    """
    params = [query_embedding]
    
    if document_type is not None:
        query += " AND document_type = %s"
        params.append(document_type)
    
    if standard_code is not None:
        query += " AND standard_code = %s"
        params.append(standard_code)
    
    query += " ORDER BY embedding <=> %s::vector LIMIT %s;"
    params.extend([query_embedding, top_k])
    
    cursor.execute(query, params)
    rows = cursor.fetchall()
    
    result = []
    for row in rows:
        result.append({
            "id": row[0],
            "document_type": row[1],
            "standard_code": row[2],
            "standard_number": row[3],
            "standard_name": row[4],
            "section_name": row[5],
            "section_order": row[6],
            "page_number": row[7],
            "chunk": row[8],
            "actual_text": row[9],
            "similarity": float(row[10]) if row[10] else 0.0
        })
    
    cursor.close()
    conn.close()
    logger.info("Vector search returned %d results", len(result))
    return result

def hybrid_search(
    query_embedding: List[float],
    query_text: str,
    top_k: int = 5,
    document_type: Optional[str] = None,
    alpha: float = 0.5
) -> List[Dict]:
    logger.info("Performing hybrid search with top_k=%d, alpha=%.2f", top_k, alpha)
    
    conn = get_connection()
    cursor = conn.cursor()
    
    query = """
        WITH vector_scores AS (
            SELECT id, 1 - (embedding <=> %s::vector) as vec_score
            FROM rules
            WHERE embedding IS NOT NULL
        ),
        text_scores AS (
            SELECT id, 
                   ts_rank(to_tsvector('english', coalesce(chunk, '') || ' ' || coalesce(actual_text, '')), 
                          plainto_tsquery('english', %s)) as text_score
            FROM rules
        )
        SELECT r.id, r.document_type, r.standard_code, r.standard_number, r.standard_name,
               r.section_name, r.section_order, r.page_number, r.chunk, r.actual_text,
               (%s * COALESCE(v.vec_score, 0)) + ((1 - %s) * COALESCE(t.text_score, 0)) as combined_score
        FROM rules r
        LEFT JOIN vector_scores v ON r.id = v.id
        LEFT JOIN text_scores t ON r.id = t.id
        WHERE r.embedding IS NOT NULL
    """
    params = [query_embedding, query_text, alpha, alpha]
    
    if document_type is not None:
        query += " AND r.document_type = %s"
        params.append(document_type)
    
    query += " ORDER BY combined_score DESC LIMIT %s;"
    params.append(top_k)
    
    cursor.execute(query, params)
    rows = cursor.fetchall()
    
    result = []
    for row in rows:
        result.append({
            "id": row[0],
            "document_type": row[1],
            "standard_code": row[2],
            "standard_number": row[3],
            "standard_name": row[4],
            "section_name": row[5],
            "section_order": row[6],
            "page_number": row[7],
            "chunk": row[8],
            "actual_text": row[9],
            "score": float(row[10]) if row[10] else 0.0
        })
    
    cursor.close()
    conn.close()
    logger.info("Hybrid search returned %d results", len(result))
    return result
