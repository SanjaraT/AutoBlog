from __future__ import annotations
import operator
from typing import TypedDict, List, Optional, Literal, Annotated
from pydantic import BaseModel, Field


class Task(BaseModel):
    id: int
    title: str
    goal: str = Field(..., description="One sentence describing what the reader should be able to do/understand after this section.")
    bullets: List[str] = Field(..., min_length=3, max_length=6, description="3–6 concrete, non-overlapping subpoints to cover.")
    target_words: int = Field(..., description="Target word count for this section (120–550).")

    # lets the orchestrator flag which sections need fresh info, code, or citations
    tags: List[str] = Field(default_factory=list)
    requires_research: bool = False
    requires_citations: bool = False
    requires_code: bool = False


class Plan(BaseModel):
    blog_title: str
    audience: str
    tone: str

    # tells downstream nodes what "shape" of blog this is
    blog_kind: Literal["explainer", "tutorial", "news_roundup", "comparison", "system_design"] = "explainer"
    constraints: List[str] = Field(default_factory=list)
    tasks: List[Task]


# a single piece of retrieved web evidence, normalized from raw Tavily output
class EvidenceItem(BaseModel):
    title: str
    url: str
    published_at: Optional[str] = None  
    snippet: Optional[str] = None
    source: Optional[str] = None


# structured output schema for the router LLM call
class RouterDecision(BaseModel):
    needs_research: bool
    mode: Literal["closed_book", "hybrid", "open_book"]
    queries: List[str] = Field(default_factory=list)


# structured output schema for the research-synthesis LLM call
class EvidencePack(BaseModel):
    evidence: List[EvidenceItem] = Field(default_factory=list)

# structured output schema for critique
class SectionCritique(BaseModel):
    task_id: int
    passes: bool
    issues: List[str] = Field(
        default_factory=list,
        description="Specific, actionable problems found, e.g. 'word count 40% below target', 'bullet 3 not addressed'.",
    )

class CritiquePack(BaseModel):
    critiques: List[SectionCritique]


# structured output schema for image generation
class ImageSpec(BaseModel):
    placeholder: str = Field(..., description="e.g. [[IMAGE_1]]")
    filename: str = Field(..., description="Save under images/, e.g. qkv_flow.png")
    alt: str
    caption: str
    mermaid_code: str = Field(
        ...,
        description="Valid Mermaid diagram syntax (flowchart, sequence, etc.) representing this concept.",
    )


class GlobalImagePlan(BaseModel):
    md_with_placeholders: str
    images: List[ImageSpec] = Field(default_factory=list)

def keep_max(a: int, b: int) -> int:
    return max(a, b)

class State(TypedDict):
    topic: str
    mode: str
    needs_research: bool
    queries: List[str]
    evidence: List[EvidenceItem]
    plan: Optional[Plan]
    sections: Annotated[List[tuple], operator.add]

    critiques: List[dict]         
    unverified_citations: List[str] 
    revision_count: Annotated[int, keep_max]
     
    merged_md: str
    md_with_placeholders: str
    image_specs: List[dict]

    final: str
    run_id: Optional[int] 