import zlib
import base64
import urllib.parse
from typing import List, Dict, Any, Optional
from app.models import MainConcept

def generate_mermaid_mindmap(concept_map: List[MainConcept]) -> str:
    """
    Converts a concept map data structure to Mermaid mindmap syntax.
    
    Args:
        concept_map (List[MainConcept]): The concept map data
        
    Returns:
        str: Mermaid mindmap syntax
    """
    if not concept_map or len(concept_map) == 0:
        return "mindmap\n    root((No concept map data available))"
    
    # Start with the mindmap header
    mermaid_code = ["mindmap"]
    
    # Assume the first item is the root node
    root = concept_map[0]
    root_text = f'    root(("**{root.emoji} {root.name}**<br>{root.description}"))'
    mermaid_code.append(root_text)
    
    # Process main concepts (level 1)
    for main_concept in concept_map[1:]:
        main_text = f'        {_sanitize_id(main_concept.name)}("**{main_concept.emoji} {main_concept.name}** <br> {main_concept.description}")'
        mermaid_code.append(main_text)
        
        # Process subconcepts (level 2)
        if main_concept.subtopics:
            for sub_concept in main_concept.subtopics:
                sub_text = f'            {_sanitize_id(sub_concept.name)} ("**{sub_concept.emoji} {sub_concept.name}** <br> {sub_concept.description}")'
                mermaid_code.append(sub_text)
                
                # Process detail concepts (level 3)
                if sub_concept.details:
                    for detail in sub_concept.details:
                        detail_text = f'                {_sanitize_id(detail.name)} ("**{detail.emoji} {detail.name}** <br> {detail.description}")'
                        mermaid_code.append(detail_text)
    
    # Join all lines with newlines
    return "\n".join(mermaid_code)

def _sanitize_id(text: str) -> str:
    """
    Sanitizes text to be used as a Mermaid node ID.
    Removes special characters and replaces spaces with underscores.
    
    Args:
        text (str): The text to sanitize
        
    Returns:
        str: Sanitized text suitable for a Mermaid node ID
    """
    # Replace spaces with underscores and remove special characters
    sanitized = ''.join(c if c.isalnum() or c == '_' else '_' for c in text.replace(' ', '_'))
    return sanitized

def get_mermaid_url(mermaid_code: str) -> str:
    """
    Compresses and encodes Mermaid code for use in a mermaid.ink URL.
    
    Args:
        mermaid_code (str): The Mermaid syntax code
        
    Returns:
        str: URL with encoded Mermaid code
    """
    # Compress the Mermaid code using zlib (equivalent to pako in JavaScript)
    compressed = zlib.compress(mermaid_code.encode('utf-8'))
    
    # Encode with base64
    encoded = base64.b64encode(compressed).decode('utf-8')
    
    # Make the encoded string URL-safe
    url_safe_encoded = encoded.replace('+', '-').replace('/', '_')
    
    # Create the final URL
    return f"https://mermaid.ink/img/pako:{url_safe_encoded}"

def process_concept_map_to_mermaid_url(concept_map: List[Dict[str, Any]]) -> Dict[str, str]:
    """
    Process a concept map and return both the Mermaid code and the URL.
    
    Args:
        concept_map (List[Dict]): The concept map data
        
    Returns:
        Dict[str, str]: Dictionary with 'mermaid_code' and 'mermaid_url' keys
    """
    # Convert to MainConcept objects if needed
    if concept_map and isinstance(concept_map[0], dict):
        from app.models import MainConcept
        concept_objects = [MainConcept.model_validate(item) for item in concept_map]
    else:
        concept_objects = concept_map
    
    # Generate Mermaid code
    mermaid_code = generate_mermaid_mindmap(concept_objects)
    
    # Get the URL
    mermaid_url = get_mermaid_url(mermaid_code)
    
    return {
        "mermaid_code": mermaid_code,
        "mermaid_url": mermaid_url
    }
