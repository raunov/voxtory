from typing import List, Dict, Any, Optional
from app.models import ContentAnalysis, MainConcept, Speaker, Statement

def generate_markdown(data: Dict[str, Any], video_title: Optional[str] = None) -> str:
    """
    Convert the ContentAnalysis data to a structured Markdown format.
    
    Args:
        data (Dict[str, Any]): The ContentAnalysis data
        video_title (Optional[str]): The title of the video, if available
        
    Returns:
        str: Formatted Markdown representation
    """
    markdown = []
    
    # Add title
    title = video_title or "Video Analysis"
    markdown.append(f"# 📊 {title}\n")
    
    # Add Mermaid diagram if available
    if "mermaid" in data and "mermaid_url" in data["mermaid"]:
        markdown.append("## 📊 Concept Map\n")
        markdown.append(f"![Concept Map]({data['mermaid']['mermaid_url']})\n")
    
    # Add concept map
    if "concept_map" in data and data["concept_map"]:
        markdown.append("## 💡 Key Concepts\n")
        
        # Process each main concept
        for i, concept in enumerate(data["concept_map"]):
            if i == 0:  # First concept is often the root/central topic
                markdown.append(f"### {concept.get('emoji', '')} {concept.get('name', '')}")
                markdown.append(f"*{concept.get('description', '')}*\n")
            else:
                markdown.append(f"### {concept.get('emoji', '')} {concept.get('name', '')}")
                markdown.append(f"*{concept.get('description', '')}*\n")
                
                # Process subconcepts (level 2)
                if "subtopics" in concept and concept["subtopics"]:
                    for subconcept in concept["subtopics"]:
                        markdown.append(f"#### {subconcept.get('emoji', '')} {subconcept.get('name', '')}")
                        markdown.append(f"*{subconcept.get('description', '')}*\n")
                        
                        # Process details (level 3)
                        if "details" in subconcept and subconcept["details"]:
                            for detail in subconcept["details"]:
                                markdown.append(f"- **{detail.get('emoji', '')} {detail.get('name', '')}**: {detail.get('description', '')}")
                            markdown.append("")  # Add empty line after details
    
    # Add speakers
    if "speakers" in data and data["speakers"]:
        markdown.append("## 👥 Speakers\n")
        
        for speaker in data["speakers"]:
            markdown.append(f"### {speaker.get('full_name', '')}")
            
            # Add roles/affiliations if available
            if "roles_affiliations" in speaker and speaker["roles_affiliations"]:
                roles = ", ".join(speaker["roles_affiliations"])
                markdown.append(f"**Roles/Affiliations**: {roles}")
            
            # Add visual description if available
            if "visual_description" in speaker and speaker["visual_description"]:
                markdown.append(f"**Visual Description**: {speaker['visual_description']}")
            
            # Add voice description if available
            if "voice_description" in speaker and speaker["voice_description"]:
                markdown.append(f"**Voice Description**: {speaker['voice_description']}")
            
            markdown.append("")  # Empty line
            
            # Add statements by category
            if "statements" in speaker and speaker["statements"]:
                markdown.append("#### Key Statements:")
                
                # Group statements by category
                statements_by_category = {}
                for statement in speaker["statements"]:
                    category = statement.get("category")
                    text = statement.get("text")
                    if category and text:
                        if category not in statements_by_category:
                            statements_by_category[category] = []
                        statements_by_category[category].append(text)
                
                # Add statements with category-specific emojis
                category_emojis = {
                    "fact": "📝",
                    "prediction": "🔮",
                    "insight": "💡",
                    "anecdote": "📖",
                    "opinion": "🗣️",
                    "explanation": "🧠"
                }
                
                for category, statements in statements_by_category.items():
                    emoji = category_emojis.get(category, "•")
                    markdown.append(f"\n**{emoji} {category.title()}**")
                    for statement in statements:
                        markdown.append(f"- \"{statement}\"")
                
                markdown.append("")  # Empty line after statements
    
    # Join all lines with double newlines for better readability
    return "\n".join(markdown)


def process_content_analysis_to_markdown(data: Dict[str, Any], video_title: Optional[str] = None) -> str:
    """
    Process the ContentAnalysis data and return formatted Markdown.
    
    Args:
        data (Dict[str, Any]): The ContentAnalysis data
        video_title (Optional[str]): The title of the video, if available
        
    Returns:
        str: Formatted Markdown
    """
    return generate_markdown(data, video_title)
