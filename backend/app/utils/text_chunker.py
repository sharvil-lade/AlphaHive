import re
import logging
from typing import List, Dict, Any

logger = logging.getLogger("text-chunker")


class RecursiveCharacterTextSplitter:
    """Pure-python implementation of RecursiveCharacterTextSplitter to avoid heavy/varying dependencies."""
    
    def __init__(self, chunk_size: int = 1000, chunk_overlap: int = 150):
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap

    def split_text(self, text: str) -> List[str]:
        """Splits a body of text into chunks of chunk_size with chunk_overlap, splitting on newlines and sentences."""
        if not text:
            return []
            
        chunks = []
        text_len = len(text)
        start = 0
        
        while start < text_len:
            # Determine initial end index
            end = min(start + self.chunk_size, text_len)
            
            # Look for ideal split boundaries backwards from end to start + overlap
            if end < text_len:
                # 1. Try double newlines (paragraph boundary)
                idx = text.rfind("\n\n", start + self.chunk_overlap, end)
                if idx != -1:
                    end = idx + 2
                else:
                    # 2. Try single newlines
                    idx = text.rfind("\n", start + self.chunk_overlap, end)
                    if idx != -1:
                        end = idx + 1
                    else:
                        # 3. Try sentence endings
                        idx = text.rfind(". ", start + self.chunk_overlap, end)
                        if idx != -1:
                            end = idx + 2
            
            chunk = text[start:end].strip()
            if chunk:
                chunks.append(chunk)
                
            # Slide start index forward by chunk size minus overlap
            next_start = end - self.chunk_overlap
            
            # Force progress to prevent infinite loops
            if next_start <= start:
                start = end
            else:
                start = next_start
                
        return chunks


class TextChunker:
    """Chunks SEC filings text into semantic segments enriched with item metadata."""

    def __init__(self):
        self.text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=1000,
            chunk_overlap=150
        )

    def segment_and_chunk(self, raw_text: str) -> List[Dict[str, Any]]:
        """Segments raw filing text into Item 1A (Risk Factors) and Item 7 (MD&A), then chunks them."""
        chunks = []
        
        # 1. Regex to locate Item 1A and Item 7 sections
        item_1a_match = re.search(r"ITEM\s+1A\.?\s+RISK\s+FACTORS", raw_text, re.IGNORECASE)
        item_7_match = re.search(r"ITEM\s+7\.?\s+MANAGEMENT", raw_text, re.IGNORECASE)
        item_8_match = re.search(r"ITEM\s+8\.?\s+FINANCIAL\s+STATEMENTS", raw_text, re.IGNORECASE)

        sections = []

        # Slice text by identified indices
        if item_1a_match and item_7_match:
            idx_1a = item_1a_match.start()
            idx_7 = item_7_match.start()
            
            # General section (before Item 1A)
            sections.append({
                "name": "General & Business Overview",
                "text": raw_text[:idx_1a]
            })
            
            # Risk Factors (between 1A and 7)
            sections.append({
                "name": "Item 1A. Risk Factors",
                "text": raw_text[idx_1a:idx_7]
            })
            
            # MD&A section
            if item_8_match and item_8_match.start() > idx_7:
                sections.append({
                    "name": "Item 7. Management's Discussion and Analysis",
                    "text": raw_text[idx_7:item_8_match.start()]
                })
                sections.append({
                    "name": "Item 8. Financial Statements & Disclosures",
                    "text": raw_text[item_8_match.start():]
                })
            else:
                sections.append({
                    "name": "Item 7. Management's Discussion and Analysis",
                    "text": raw_text[idx_7:]
                })
        else:
            # Fallback if specific item headers were not found
            sections.append({
                "name": "General Corporate Filing",
                "text": raw_text
            })

        # 2. Chunk each segment recursively
        chunk_counter = 0
        for sec in sections:
            sec_name = sec["name"]
            sec_text = sec["text"]
            
            if not sec_text.strip():
                continue
                
            split_texts = self.text_splitter.split_text(sec_text)
            for text in split_texts:
                chunks.append({
                    "text": text,
                    "section": sec_name,
                    "chunk_id": chunk_counter
                })
                chunk_counter += 1

        logger.info(f"Segmented filing into {len(sections)} sections, yielding {len(chunks)} total text chunks")
        return chunks


text_chunker = TextChunker()
