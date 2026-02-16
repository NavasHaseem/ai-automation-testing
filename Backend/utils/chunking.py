
from typing import List
import textwrap
import re

def naive_chunks(text: str, chunk_chars: int = 1200, overlap: int = 150) -> List[str]:
    """
    Split text into chunks at word boundaries to avoid breaking words.
    """
    if not text:
        return []
    
    chunks = []
    start = 0
    n = len(text)
    
    while start < n:
        # Calculate the initial end position
        end = min(start + chunk_chars, n)
        
        # If we're not at the end of the text, find the last word boundary
        if end < n:
            # Look backwards from 'end' to find a word boundary (space, newline, punctuation)
            # Search within a reasonable range (up to 100 chars back)
            search_start = max(start, end - 100)
            chunk_text = text[search_start:end]
            
            # Find the last word boundary (space, newline, or punctuation followed by space)
            matches = list(re.finditer(r'[\s\n.!?,;:)\]}\-]+', chunk_text))
            
            if matches:
                # Get the last match position
                last_boundary = matches[-1].end()
                # Adjust end to the word boundary
                end = search_start + last_boundary
            # If no boundary found, keep original end (rare case)
        
        # Extract chunk
        chunk = text[start:end].strip()
        if chunk:
            chunks.append(chunk)
        
        # Move start position with overlap, but ensure we don't break words
        if end < n:
            # Calculate overlap start
            overlap_start = max(end - overlap, start + 1)
            
            # Find the next word boundary after overlap_start
            remaining_text = text[overlap_start:min(overlap_start + 100, n)]
            match = re.search(r'[\s\n]+', remaining_text)
            
            if match:
                start = overlap_start + match.end()
            else:
                start = end
        else:
            start = end
    
    return chunks
