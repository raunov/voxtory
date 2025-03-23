def get_language_prompt(language_code: str = 'en', additional_instructions: str = '') -> str:
    """
    Get the prompt with specified language instructions
    
    Args:
        language_code (str): Language code for the output
        additional_instructions (str): Any additional instructions to append to the prompt
    
    Returns:
        str: Prompt with language instructions
    """
    base_prompt = f"""
You are tasked with analyzing a video recording and creating a concept map of topics discussed and dossiers for each speaker mentioned.
Additional instructions for video content:
* Include visual descriptions of scenes and actions where relevant
* Note significant visual elements alongside the audio
* Identify speakers based on both visual and audio cues
* Generate all output in the language specified by this code: {language_code}

Please follow these instructions carefully:

1. Concept Map Creation:
   Create a 3-level hierarchical concept map of the video content. For each main concept or topic discussed, include:
   - name of the concept or topic
   - level of concept topic (main concept, subtopic, detail) 
        * Main Concept: the core themes of the video
        * Subtopic: major concepts and areas within the central topics
        * Detail: specific ideas, definitions, examples and challenges related to the subtopics
   - Appropriate emoji for each topic
   - A brief description of the topic
   Present this information in a structured format. Ensure that your response maintains this exact 3-level hierarchy with no additional nested levels.

2. Speaker Identification:
   Identify speakers based on what they say about themselves or each other. Use every clue available, including:
   - Self-introductions
   - Introductions by others
   - References to past roles or affiliations
   - Visual cues (e.g., name tags, company logos)
   - Contextual clues (e.g., "the CEO of XYZ Corp", "the interviewer", etc.)
   If a speaker's name is not explicitly mentioned, use a generic descriptor that best fits their role (e.g., "Interviewer", "Guest Expert", "Company CEO").

3. Speaker Dossiers:
   For each identified speaker, create a dossier. Extract factual background information from the transcript based on what the speakers themselves or other participants say. Focus on:
   a. Full name
   b. Current and past roles and affiliations mentioned
   c. Visual descriptions of the speaker (if mentioned)
   d. Voice description (if relevant)
   e. Insightful statements uttered by the speaker, categorized as either: facts, predictions, insights, anecdotes, opinions.
   Include only the statements that are relevant to the speaker's role and expertise. Categorize each statement accordingly.

If certain information is not available, omit those fields entirely.
Ensure that your final output contains only the information requested, without any additional explanation or commentary.
Remember to focus on extracting and presenting factual information from the video/audio. Do not include any speculative or inferred information.
Generate all output in the language specified by this code: {language_code}
"""
    
    # Append any additional instructions if provided
    if additional_instructions:
        base_prompt += f"\n\nAdditional Instructions:\n{additional_instructions}"
    
    return base_prompt
