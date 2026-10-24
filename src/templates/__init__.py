"""Templates and category formatting package."""

from src.templates.registry import (
    QueryTemplate,
    TEMPLATES,
    get_template_for_category,
)
from src.templates.guardrail import (
    verify_recommendation_guardrail,
    scrub_recommendations_if_present,
    FORBIDDEN_RECOMMENDATION_PATTERNS,
)

__all__ = [
    "QueryTemplate",
    "TEMPLATES",
    "get_template_for_category",
    "verify_recommendation_guardrail",
    "scrub_recommendations_if_present",
    "FORBIDDEN_RECOMMENDATION_PATTERNS",
]
