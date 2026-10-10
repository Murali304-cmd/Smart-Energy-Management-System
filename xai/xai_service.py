import logging
from typing import Dict, Any, Optional
from xai.explanation import build_explanation

logger = logging.getLogger("SEMS.XAI")

class ExplainableAIService:
    def __init__(self):
        pass

    def explain(self, recommendation_result: Dict[str, Any], explanation_level: str = "simple") -> Dict[str, Any]:
        return build_explanation(recommendation_data=recommendation_result, explanation_level=explanation_level)

_xai_instance: Optional[ExplainableAIService] = None

def get_xai_service() -> ExplainableAIService:
    global _xai_instance
    if _xai_instance is None:
        _xai_instance = ExplainableAIService()
    return _xai_instance

def explain_recommendation(recommendation_result: Dict[str, Any], explanation_level: str = "simple") -> Dict[str, Any]:
    service = get_xai_service()
    return service.explain(recommendation_result, explanation_level=explanation_level)
