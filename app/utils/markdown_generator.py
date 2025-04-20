from typing import List, Dict, Any, Optional, Tuple
from app.models import ContentAnalysis, MainConcept, Speaker, Statement
import urllib.parse # Import for URL encoding
import re

def _create_youtube_timestamp_link(url: str, timestamp: str) -> str:
    """
    Create a YouTube link with timestamp.
    
    Args:
        url (str): YouTube URL
        timestamp (str): Timestamp in MM:SS format
        
    Returns:
        str: YouTube URL with timestamp parameter
    """
    try:
        # Convert MM:SS to seconds
        parts = timestamp.split(':')
        if len(parts) == 2:
            minutes, seconds = int(parts[0]), int(parts[1])
            total_seconds = minutes * 60 + seconds
            
            # Handle different YouTube URL formats
            if 'youtube.com/watch' in url:
                # Standard YouTube URL
                if '?' in url:
                    return f"{url}&t={total_seconds}"
                else:
                    return f"{url}?t={total_seconds}"
            elif 'youtu.be/' in url:
                # Shortened YouTube URL
                if '?' in url:
                    return f"{url}&t={total_seconds}"
                else:
                    return f"{url}?t={total_seconds}"
            else:
                # Unknown format, return original URL
                return url
        else:
            # Invalid timestamp format
            return url
    except (ValueError, IndexError):
        # Error parsing timestamp
        return url

def generate_markdown(data: Dict[str, Any], video_title: Optional[str] = None) -> str:
    """
    Convert the ContentAnalysis data (including potential metadata like 
    'original_filename' and 'google_drive_id') to a structured Markdown format.
    
    Args:
        data (Dict[str, Any]): The ContentAnalysis data dictionary. 
                               Should contain analysis results and potentially 
                               'original_filename' and 'google_drive_id'.
        video_title (Optional[str]): The title of the video, if available. 
                                     Defaults to 'Video Analysis'.
        
    Returns:
        str: Formatted Markdown representation
    """
    markdown = []
    
    # Store YouTube URL for timestamp links
    youtube_url = data.get('youtube_url', '')
    
    # Add title
    title = video_title or "Video Analysis"
    markdown.append(f"# 📊 {title}\n")

    # --- Add Summary (from first main concept) ---
    if "concept_map" in data and data["concept_map"]:
        first_concept = data["concept_map"][0]
        if first_concept and 'description' in first_concept:
             markdown.append(f"*{first_concept.get('description', '')}*\n")
    
    # --- Add Introduction with speaker names ---
    if "speakers" in data and data["speakers"]:
        speaker_names = [s.get('full_name', '') for s in data["speakers"] if s.get('full_name')]
        if speaker_names:
            speakers_text = ", ".join(speaker_names)
            markdown.append(f"*Arutelu, kus osalevad {speakers_text}.*\n")
    
    # Add Mermaid diagram if available
    if "mermaid" in data and "mermaid_url" in data["mermaid"]:
        markdown.append("## 📊 Concept Map\n")
        markdown.append(f"![Concept Map]({data['mermaid']['mermaid_url']})\n")
    
    # Add concept map details
    if "concept_map" in data and data["concept_map"]:
        markdown.append("## 💡 Key Concepts\n")
        
        # Process each main concept (skip the first one's description as it's used for summary)
        for i, concept in enumerate(data["concept_map"]):
            # Use H3 for main concepts
            markdown.append(f"### {concept.get('emoji', '')} {concept.get('name', '')}")
            # Add description for concepts other than the first one (which is the summary)
            if i > 0 and concept.get('description'):
                 markdown.append(f"*{concept.get('description', '')}*\n")
            else: # Add a newline after the title/summary
                 markdown.append("") # Ensure newline separation

            # Process subconcepts (level 2) - Use H4
            if "subtopics" in concept and concept["subtopics"]:
                for subconcept in concept["subtopics"]:
                    markdown.append(f"**{subconcept.get('emoji', '')} {subconcept.get('name', '')}**")
                    if subconcept.get('description'):
                        markdown.append(f"*{subconcept.get('description', '')}*\n")
                    
                    # Process details (level 3) - Use bullet points
                    if "details" in subconcept and subconcept["details"]:
                        for detail in subconcept["details"]:
                            markdown.append(f"- **{detail.get('emoji', '')} {detail.get('name', '')}**: {detail.get('description', '')}")
                        markdown.append("")  # Add empty line after details list
            markdown.append("") # Add newline after each main concept block

    # --- Group Statements by Category ---
    if "speakers" in data and data["speakers"]:
        markdown.append("## 💬 Võtmeväited Kategooriate Kaupa\n") # Key Statements by Category

        all_statements_by_category = {}
        # Collect all statements from all speakers
        for speaker in data["speakers"]:
            speaker_name = speaker.get('full_name', 'Unknown Speaker')
            if "statements" in speaker and speaker["statements"]:
                for statement in speaker["statements"]:
                    category = statement.get("category", "unknown")
                    text = statement.get("text")
                    timestamp = statement.get("timestamp")
                    if text: # Only add if text exists
                        if category not in all_statements_by_category:
                            all_statements_by_category[category] = []
                        all_statements_by_category[category].append({
                            "speaker": speaker_name, 
                            "text": text,
                            "timestamp": timestamp
                        })

        # Define category order and display names/emojis
        category_order = ['insight', 'opinion', 'fact', 'explanation', 'anecdote', 'prediction', 'unknown']
        category_display = {
            "insight": ("💡", "Võtmetähelepanekud (Insights)"),
            "opinion": ("🗣️", "Arvamused (Opinions)"),
            "fact": ("📝", "Faktid (Facts)"),
            "explanation": ("🧠", "Selgitused (Explanations)"),
            "anecdote": ("📖", "Näited/Lood (Anecdotes)"),
            "prediction": ("🔮", "Ennustused (Predictions)"),
            "unknown": ("❓", "Muu (Other)")
        }

        # Iterate through ordered categories and print statements
        for category_key in category_order:
            if category_key in all_statements_by_category:
                emoji, display_name = category_display.get(category_key, ("•", category_key.title()))
                markdown.append(f"### {emoji} {display_name}\n") # Use H3 for category titles
                for stmt in all_statements_by_category[category_key]:
                    # Add timestamp with YouTube link if available
                    if 'timestamp' in stmt and stmt['timestamp'] and youtube_url:
                        timestamp_link = _create_youtube_timestamp_link(youtube_url, stmt['timestamp'])
                        markdown.append(f"- **{stmt['speaker']}** ([{stmt['timestamp']}]({timestamp_link})): \"{stmt['text']}\"")
                    elif 'timestamp' in stmt and stmt['timestamp']:
                        # Non-YouTube video with timestamp
                        markdown.append(f"- **{stmt['speaker']}** ({stmt['timestamp']}): \"{stmt['text']}\"")
                    else:
                        # No timestamp available
                        markdown.append(f"- **{stmt['speaker']}:** \"{stmt['text']}\"")
                markdown.append("") # Add newline after each category list

    # --- Add Named Entities ---
    if "named_entities" in data and data["named_entities"]:
        entities = data["named_entities"]
        # Check if any entity list is not None and not empty
        has_entities = any(entities.get(key) for key in ['terms', 'persons', 'organizations'])

        if has_entities:
            markdown.append("## 🔗 Mainitud üksused\n") # Mentioned Entities

            entity_types = {
                "terms": ("🏷️", "Terminid"),
                "persons": ("👤", "Isikud"),
                "organizations": ("🏢", "Organisatsioonid")
            }

            for type_key, (emoji, display_name) in entity_types.items():
                 # Check if the key exists and the list is not None and not empty
                if entities.get(type_key):
                    markdown.append(f"### {emoji} {display_name}\n") # Use H3 for entity types
                    for item in entities[type_key]:
                        # Create Google search link
                        search_query = urllib.parse.quote_plus(item)
                        link = f"https://www.google.com/search?q={search_query}"
                        markdown.append(f"- [{item}]({link})")
                    markdown.append("") # Add newline after each entity list

    # --- Add Conclusion Section with Key Insights ---
    if "speakers" in data and data["speakers"]:
        # Extract key insights from statements
        key_insights = []
        for speaker in data["speakers"]:
            speaker_name = speaker.get('full_name', 'Unknown Speaker')
            if "statements" in speaker and speaker["statements"]:
                for statement in speaker["statements"]:
                    if statement.get("category") == "insight":
                        key_insights.append({
                            "speaker": speaker_name,
                            "text": statement.get("text", ""),
                            "timestamp": statement.get("timestamp")
                        })
        
        if key_insights and len(key_insights) > 0:
            markdown.append("## 📝 Kokkuvõte\n")
            markdown.append("Peamised tähelepanekud:\n")
            # Limit to top 3 insights
            for i, insight in enumerate(key_insights[:3]):
                # Add timestamp with YouTube link if available
                if 'timestamp' in insight and insight['timestamp'] and youtube_url:
                    timestamp_link = _create_youtube_timestamp_link(youtube_url, insight['timestamp'])
                    markdown.append(f"- **{insight['speaker']}** ([{insight['timestamp']}]({timestamp_link})): {insight['text']}")
                elif 'timestamp' in insight and insight['timestamp']:
                    # Non-YouTube video with timestamp
                    markdown.append(f"- **{insight['speaker']}** ({insight['timestamp']}): {insight['text']}")
                else:
                    # No timestamp available
                    markdown.append(f"- **{insight['speaker']}:** {insight['text']}")
            markdown.append("")

    # --- Add Source Information ---
    original_filename = data.get('original_filename')
    google_drive_id = data.get('google_drive_id')

    if original_filename:
        markdown.append("---") # Add a horizontal rule before source info
        source_text = f"Automaatne analüüs genereeritud Voxtory API kaudu. Andmed pärinevad salvestusest: "
        if google_drive_id:
            drive_link = f"https://drive.google.com/file/d/{google_drive_id}/view"
            source_text += f"[{original_filename}]({drive_link})"
        else:
            source_text += f"**{original_filename}**"
        markdown.append(source_text + "\n")

    # Join all lines
    return "\n".join(markdown)


def process_content_analysis_to_markdown(data: Dict[str, Any], video_title: Optional[str] = None) -> str:
    """
    Process the ContentAnalysis data dictionary and return formatted Markdown.
    
    Args:
        data (Dict[str, Any]): The ContentAnalysis data dictionary, potentially 
                               including metadata like 'original_filename' and 
                               'google_drive_id' alongside analysis results.
        video_title (Optional[str]): The title of the video, if available.
        
    Returns:
        str: Formatted Markdown
    """
    # Pass the full data dictionary which might contain filename/drive_id
    # The generate_markdown function now handles extracting these.
    return generate_markdown(data, video_title)
