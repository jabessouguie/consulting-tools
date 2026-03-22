import re
from typing import List, Dict, Optional

class PIIAnonymizer:
    """
    Utility class to mask Personally Identifiable Information (PII) 
    before sending data to external LLMs.
    """
    
    # Common PII patterns
    PATTERNS = {
        "email": r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{1,}',
        "address": r'\d+[\s,]+(?:rue|avenue|boulevard|place|allée|route|chemin|quai|impasse)[\s,]+[a-zA-Z0-9\s,]+(?:\d{5}\s+[A-Z][A-Z\s]+)?',
        "phone": r'(?:\+?33|0)[\s.-]?[1-9](?:[\s.-]?\d{2}){4}',
        "name": r'(?:M\.|Mme|Mlle|Mr\.|Mrs\.|Ms\.)\s+[A-Z][a-zA-Z]+(?:\s+[a-zA-Z]+)*',
    }

    def __init__(self, custom_masks: Optional[List[str]] = None):
        """
        Initialize with optional custom strings to mask (e.g. specific client names).
        """
        self.custom_masks = custom_masks or []

    def mask(self, text: str) -> str:
        """
        Masks PII in the given text.
        """
        if not text:
            return text
            
        masked_text = text
        
        # Mask custom strings first (most specific)
        for custom in self.custom_masks:
            if custom:
                masked_text = re.sub(re.escape(custom), "[FILTERED_ENTITY]", masked_text, flags=re.IGNORECASE)
        
        # Mask standard patterns
        for label, pattern in self.PATTERNS.items():
            # Use fixed tags [EMAIL], [PHONE], etc. to match tests and be concise
            masked_text = re.sub(pattern, f"[{label.upper()}]", masked_text)
            
        return masked_text

# Singleton instance
anonymizer = PIIAnonymizer()
