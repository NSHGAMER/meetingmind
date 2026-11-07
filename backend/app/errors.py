class HindsightUnavailable(Exception):
    """Hindsight could not be reached or rejected the request. Never swallowed silently."""


class LLMError(Exception):
    """LLM provider unreachable / not configured."""


class LLMInvalidResponse(LLMError):
    """LLM returned output that failed schema validation."""
