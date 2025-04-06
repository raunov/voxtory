from pydantic import BaseModel, Field
from typing import Optional, List, Literal, Dict, Any

# Model for roles and affiliations
class RoleAffiliation(BaseModel):
    role_affiliation: str
    is_current: Optional[bool] = None  # To distinguish between current and past roles

class DetailConcept(BaseModel):
    name: str
    type: str 
    emoji: str
    description: str

class SubConcept(BaseModel):
    name: str
    type: str 
    emoji: str
    description: str
    details: Optional[List[DetailConcept]] = None  # Contains details (level 3)

class MainConcept(BaseModel):
    name: str
    type: str 
    emoji: str
    description: str
    subtopics: Optional[List[SubConcept]] = None  # Contains subtopics (level 2)

# Model for transcript entries
class TranscriptEntry(BaseModel):
    speaker: str
    timestamp: str
    text: str
    # Added visual elements as requested
    visual_description: Optional[str] = None  # For visual descriptions in the transcript

# Model for categorized statements by speakers
class Statement(BaseModel):
    text: str
    category: Literal["fact", "prediction", "insight", "anecdote", "opinion", "explanation"]

# Enhanced speaker model
class Speaker(BaseModel):
    full_name: str  # Full name or descriptor if name not available
    roles_affiliations: Optional[List[str]] = None  # List of roles and affiliations
    visual_description: Optional[str] = None  # Visual description for video or voice description for audio
    voice_description: Optional[str] = None  # Voice description if relevant
    statements: List[Statement]  # All statements made by the speaker with categories

# Model for Named Entities
class NamedEntities(BaseModel):
    persons: Optional[List[str]] = None
    organizations: Optional[List[str]] = None
    terms: Optional[List[str]] = None

# Model for Mermaid Output
class MermaidOutput(BaseModel):
    mermaid_code: str = Field(description="The generated Mermaid syntax for the concept map.")
    mermaid_url: str = Field(description="A URL to view the rendered Mermaid diagram.")

# Main response model
class ContentAnalysis(BaseModel):
    original_filename: Optional[str] = Field(default=None, description="Original filename if available from Google Drive.")
    google_drive_id: Optional[str] = Field(default=None, description="Google Drive ID if the source was Google Drive.")
    concept_map: List[MainConcept] = Field(description="Hierarchical concept map extracted from the content.")
    speakers: List[Speaker] = Field(description="Detailed information about each identified speaker and their statements.")
    named_entities: Optional[NamedEntities] = Field(default=None, description="Extracted named entities (persons, organizations, terms).")
    mermaid: Optional[MermaidOutput] = Field(default=None, description="Generated Mermaid diagram code and URL for the concept map.")

# API Request models
class VideoAnalysisRequest(BaseModel):
    youtube_url: Optional[str] = None
    google_drive_id: Optional[str] = None
    language: str = "en"
    format: Optional[Literal["json", "markdown", "both"]] = "json"

# API Response model
class ApiResponse(BaseModel):
    status: str
    data: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
