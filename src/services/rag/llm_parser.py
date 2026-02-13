import os
import json
import logging
from typing import List, Dict
from openai import OpenAI
from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger(__name__)

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

MARKDOWN_EXTRACTION_PROMPT = """You are an expert at parsing regulatory documents in Markdown format, specifically Indian Accounting Standards (Ind AS) and International Accounting Standards (IAS).

The input is a Markdown document with PAGE MARKERS like [PAGE X]. Use the heading structure (# ## ###) and page markers to identify sections accurately.

For EACH section found, extract:
- standard_code: The standard identifier (e.g., "Ind AS 1", "Ind AS 21", "IAS 16", "Ind AS 37")
- standard_number: Just the number (e.g., 1, 21, 16, 37)
- standard_name: Full name of the standard (e.g., "Provisions, Contingent Liabilities and Contingent Assets")
- section_name: The section heading (e.g., "Measurement", "Risks and uncertainties", "Present value")
- section_text: ALL the paragraph text under that section heading until the next heading
- page_number: The page number where this section STARTS (look for nearest [PAGE X] marker above)

CRITICAL RULES:
1. Each heading (# ## ###) creates a NEW section entry
2. section_text must contain ALL paragraphs under that heading, NOT just the first line
3. Keep paragraph breaks in section_text
4. Track which standard each section belongs to based on document context
5. If you see "Ind AS 37" or similar at the top, all sections below belong to that standard until a new standard appears
6. Do NOT split paragraphs into separate sections - keep all text under one heading together
7. page_number should be the page where the section heading appears (from [PAGE X] markers)

Return ONLY valid JSON array, no markdown code blocks, no explanation.

Example for this markdown:
```
[PAGE 1]
# Ind AS 37 - Provisions, Contingent Liabilities
## Measurement
The amount recognised as a provision shall be the best estimate.

[PAGE 2]
Where the provision involves a large population, the obligation is estimated by weighting.
## Risks and uncertainties
The risks shall be taken into account in reaching the best estimate.
```

Should produce:
[
  {
    "standard_code": "Ind AS 37",
    "standard_number": 37,
    "standard_name": "Provisions, Contingent Liabilities",
    "section_name": "Measurement",
    "section_text": "The amount recognised as a provision shall be the best estimate.\n\nWhere the provision involves a large population, the obligation is estimated by weighting.",
    "page_number": 1
  },
  {
    "standard_code": "Ind AS 37",
    "standard_number": 37,
    "standard_name": "Provisions, Contingent Liabilities",
    "section_name": "Risks and uncertainties",
    "section_text": "The risks shall be taken into account in reaching the best estimate.",
    "page_number": 2
  }
]

MARKDOWN TO ANALYZE:
"""

def chunk_text(text: str, max_chars: int = 30000) -> List[str]:
    chunks = []
    lines = text.split('\n')
    current_chunk = []
    current_size = 0
    
    for line in lines:
        line_size = len(line) + 1
        if current_size + line_size > max_chars and current_chunk:
            chunks.append('\n'.join(current_chunk))
            current_chunk = [line]
            current_size = line_size
        else:
            current_chunk.append(line)
            current_size += line_size
    
    if current_chunk:
        chunks.append('\n'.join(current_chunk))
    
    return chunks

def parse_with_llm(text: str) -> List[Dict]:
    logger.info("Starting LLM-based markdown parsing...")
    logger.info("Text length: %d characters", len(text))
    
    chunks = chunk_text(text, max_chars=30000)
    logger.info("Split into %d chunks for processing", len(chunks))
    
    all_sections = []
    
    for i, chunk in enumerate(chunks):
        logger.info("Processing chunk %d/%d (%d chars)...", i + 1, len(chunks), len(chunk))
        
        try:
            response = client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {
                        "role": "system",
                        "content": "You are an expert document parser. Return only valid JSON arrays. Parse markdown structure accurately."
                    },
                    {
                        "role": "user", 
                        "content": MARKDOWN_EXTRACTION_PROMPT + chunk
                    }
                ],
                temperature=0,
                max_tokens=16000
            )
            
            result_text = response.choices[0].message.content.strip()
            
            if result_text.startswith("```"):
                result_text = result_text.split("```")[1]
                if result_text.startswith("json"):
                    result_text = result_text[4:]
                result_text = result_text.strip()
            
            sections = json.loads(result_text)
            
            if isinstance(sections, list):
                all_sections.extend(sections)
                logger.info("Chunk %d: extracted %d sections", i + 1, len(sections))
            else:
                logger.warning("Chunk %d: unexpected response format", i + 1)
                
        except json.JSONDecodeError as e:
            logger.error("Chunk %d: JSON parse error - %s", i + 1, str(e))
            logger.debug("Raw response: %s", result_text[:500] if result_text else "empty")
        except Exception as e:
            logger.error("Chunk %d: LLM call failed - %s", i + 1, str(e))
    
    logger.info("LLM parsing complete. Total sections extracted: %d", len(all_sections))
    return all_sections

def parse_document_with_llm(text: str, document_type: str, pages: List[Dict] = None) -> List[Dict]:
    """Parse document with LLM.
    
    Args:
        text: Raw text (used if pages is None)
        document_type: Document type for metadata
        pages: Optional list of page dicts with 'page_number' and 'text' keys
    """
    logger.info("Parsing document with LLM. Type: %s", document_type)
    
    if pages:
        marked_text = ""
        for page in pages:
            marked_text += f"\n[PAGE {page['page_number']}]\n{page['text']}\n"
        sections = parse_with_llm(marked_text)
    else:
        sections = parse_with_llm(text)
    
    result = []
    for i, section in enumerate(sections):
        result.append({
            "document_type": document_type,
            "standard_code": section.get("standard_code", "Unknown"),
            "standard_number": section.get("standard_number"),
            "standard_name": section.get("standard_name", ""),
            "section_name": section.get("section_name", "Main Content"),
            "section_order": i + 1,
            "page_number": section.get("page_number"),
            "chunk": section.get("section_text", "")[:500],
            "actual_text": section.get("section_text", "")
        })
    
    logger.info("Formatted %d sections for database insertion", len(result))
    return result
