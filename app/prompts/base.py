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
First decide on the main title of the video. Then, based on the content of the video, create a 3-level hierarchical concept map of the video content. For each main concept or topic discussed, include:
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
   e. up to 10 most important statements uttered by the speaker, categorized as either: facts, predictions, insights, anecdotes, opinions.
      For each statement, include an approximate timestamp (in format MM:SS) when it was said in the video.
   Include only the statements that are relevant to the speaker's role and expertise. Do not include generic or irrelevant.

4. Named Entity Recognition (NER):
   Identify and list the following entities mentioned throughout the video content:
   a. Persons: Names of individuals mentioned (excluding the main speakers already detailed in the dossiers above).
   b. Organizations: Names of companies, institutions, groups, etc.
   c. Specific Terms: Key technical terms, concepts, or jargon relevant to the discussion that are not already part of the concept map structure. Only inlcude terms that are relevant to the video content and not generic terms.
   Present these as simple lists under their respective categories.

Generate all output in the language specified by this code: {language_code}
"""
    
    # Append any additional instructions if provided
    if additional_instructions:
        base_prompt += f"\n\nAdditional Instructions:\n{additional_instructions}"
    
    return base_prompt
