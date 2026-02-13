import re
import logging
from typing import List, Dict, Optional, Tuple

logger = logging.getLogger(__name__)

STANDARD_HEADER_PATTERN = re.compile(
    r"(?:^|\n)\s*((?:Ind\s*AS|IAS)\s*(\d+))\s*[,\-–:]*\s*([^\n]*)",
    re.IGNORECASE | re.MULTILINE
)

def find_all_standards(text: str) -> List[Tuple[int, str, int, str]]:
    logger.debug("Finding all standards in document...")
    standards = []
    
    for match in STANDARD_HEADER_PATTERN.finditer(text):
        position = match.start()
        full_match = match.group(1).strip()
        number = int(match.group(2).strip())
        name = match.group(3).strip() if match.group(3) else ""
        
        if "ind" in full_match.lower():
            code = f"Ind AS {number}"
        else:
            code = f"IAS {number}"
        
        standards.append((position, code, number, name))
        logger.debug("Found: %s - %s at position %d", code, name[:50] if name else "N/A", position)
    
    logger.info("Found %d standard occurrences in document", len(standards))
    return standards

def split_by_standards(text: str) -> List[Tuple[str, int, str, str]]:
    standards = find_all_standards(text)
    
    if not standards:
        logger.debug("No standards found, returning entire text")
        return [("Unknown", None, None, text)]
    
    chunks = []
    for i, (pos, code, number, name) in enumerate(standards):
        if i + 1 < len(standards):
            next_pos = standards[i + 1][0]
            chunk_text = text[pos:next_pos]
        else:
            chunk_text = text[pos:]
        
        if len(chunk_text.strip()) > 50:
            chunks.append((code, number, name, chunk_text))
            logger.debug("Standard %s: %d characters", code, len(chunk_text))
    
    return chunks

def split_into_sections(text: str) -> List[Dict]:
    logger.debug("Splitting text into sections...")
    lines = text.split("\n")
    sections = []
    current_section = None
    current_content = []
    section_order = 0
    
    for line in lines:
        stripped = line.strip()
        
        if is_section_header(stripped):
            if current_section and current_content:
                sections.append({
                    "section_name": current_section,
                    "section_order": section_order,
                    "content": "\n".join(current_content).strip()
                })
            section_order += 1
            current_section = stripped
            current_content = []
        else:
            current_content.append(line)
    
    if current_section and current_content:
        sections.append({
            "section_name": current_section,
            "section_order": section_order,
            "content": "\n".join(current_content).strip()
        })
    
    if not sections and text.strip():
        logger.debug("No sections found, using entire text as Main Content")
        sections.append({
            "section_name": "Main Content",
            "section_order": 1,
            "content": text.strip()
        })
    
    return sections

def is_section_header(line: str) -> bool:
    if not line:
        return False
    
    if len(line) < 3 or len(line) > 100:
        return False
    
    if re.match(r"^\s*(?:Ind\s*AS|IAS)\s*\d+", line, re.IGNORECASE):
        return False
    
    if line.isupper() and len(line.split()) <= 10:
        return True
    
    words = line.split()
    if len(words) <= 6 and words[0][0].isupper():
        if not any(char in line for char in [".", ",", ":", ";"]) or line.endswith(":"):
            if re.match(r"^[A-Z][a-zA-Z\s\-]+:?$", line):
                return True
    
    return False

def parse_document(text: str, document_type: str) -> List[Dict]:
    logger.info("Parsing document of type: %s", document_type)
    
    standard_chunks = split_by_standards(text)
    logger.info("Document split into %d standard blocks", len(standard_chunks))
    
    result = []
    global_section_order = 0
    
    for standard_code, standard_number, standard_name, chunk_text in standard_chunks:
        sections = split_into_sections(chunk_text)
        logger.debug("Standard %s has %d sections", standard_code, len(sections))
        
        for section in sections:
            global_section_order += 1
            result.append({
                "document_type": document_type,
                "standard_code": standard_code,
                "standard_number": standard_number,
                "standard_name": standard_name,
                "section_name": section["section_name"],
                "section_order": global_section_order,
                "chunk": section["content"][:500] if len(section["content"]) > 500 else section["content"],
                "actual_text": section["content"]
            })
    
    logger.info("Parsed %d total sections from document", len(result))
    return result

def detect_standard(text: str) -> Optional[Tuple[str, int, str]]:
    logger.debug("Detecting standard in text...")
    match = STANDARD_HEADER_PATTERN.search(text)
    if match:
        full_match = match.group(1).strip()
        number = int(match.group(2).strip())
        name = match.group(3).strip()
        if "ind" in full_match.lower():
            code = f"Ind AS {number}"
        else:
            code = f"IAS {number}"
        logger.info("Detected standard: %s - %s", code, name)
        return (code, number, name)
    logger.debug("No standard pattern found")
    return None
