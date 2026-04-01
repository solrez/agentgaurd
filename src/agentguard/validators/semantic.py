"""Semantic checker — LLM-powered hallucination detection against grounding documents."""

from __future__ import annotations

import json
import logging

from agentguard.core.action import AgentAction
from agentguard.llm.base import LLMProvider
from agentguard.validators.base import BaseValidator, ValidationResult, ValidationStatus

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = """You are a fact-checking verification system. Your job is to determine whether \
an agent's proposed action is consistent with the provided grounding documents.

Analyze the action's target and payload against the grounding documents. Determine if the action \
references real entities, endpoints, fields, or data that exist in the grounding context.

Respond ONLY with valid JSON in this exact format:
{"grounded": true, "confidence": 0.95, "reason": "Brief explanation"}

Rules:
- "grounded": true if the action is consistent with the documents, false if it references \
things not in the documents or contradicts them.
- "confidence": 0.0 to 1.0, how confident you are in your assessment.
- "reason": A brief explanation of your reasoning.
- Do NOT include any text outside the JSON object."""


class SemanticChecker(BaseValidator):
    """Validates agent actions against grounding documents using an LLM.

    Cross-references the action's target and payload against provided context
    to detect hallucinated endpoints, fabricated data, or inconsistent references.
    """

    name = "semantic"

    def __init__(
        self,
        llm_provider: LLMProvider | None = None,
        provider: str = "anthropic",
        model: str | None = None,
        api_key: str | None = None,
        grounding_docs: list[str] | None = None,
        confidence_threshold: float = 0.7,
        max_doc_chars: int = 10_000,
    ):
        if llm_provider:
            self._provider = llm_provider
        else:
            self._provider = None
            self._provider_name = provider
            self._model = model
            self._api_key = api_key

        self.grounding_docs = grounding_docs or []
        self.confidence_threshold = confidence_threshold
        self.max_doc_chars = max_doc_chars

    @property
    def provider(self) -> LLMProvider:
        if self._provider is None:
            from agentguard.llm.base import get_provider

            self._provider = get_provider(
                self._provider_name, model=self._model, api_key=self._api_key
            )
        return self._provider

    async def validate(self, action: AgentAction) -> ValidationResult:
        # Merge grounding docs from constructor and action context
        docs = self.grounding_docs + action.context.grounding_docs
        if not docs:
            return ValidationResult(
                status=ValidationStatus.SKIPPED,
                reason="No grounding documents provided",
            )

        # Truncate docs to fit context
        combined_docs = "\n---\n".join(docs)
        if len(combined_docs) > self.max_doc_chars:
            combined_docs = combined_docs[: self.max_doc_chars] + "\n... (truncated)"

        user_prompt = (
            f"## Grounding Documents\n{combined_docs}\n\n"
            f"## Agent Action\n"
            f"Target: {action.target}\n"
            f"Action Type: {action.action_type.value}\n"
            f"Payload: {json.dumps(action.payload, default=str)}"
        )

        try:
            response = await self.provider.complete(
                system_prompt=SYSTEM_PROMPT,
                user_prompt=user_prompt,
                max_tokens=256,
            )
            result = self._parse_response(response.content)
        except Exception as e:
            logger.warning(f"SemanticChecker error: {e}")
            return ValidationResult(
                status=ValidationStatus.ESCALATE,
                reason=f"Semantic verification failed: {e}",
                confidence=0.0,
            )

        return result

    def _parse_response(self, content: str) -> ValidationResult:
        """Parse the LLM's JSON response into a ValidationResult."""
        try:
            # Handle potential markdown code blocks
            cleaned = content.strip()
            if cleaned.startswith("```"):
                cleaned = cleaned.split("\n", 1)[1].rsplit("```", 1)[0].strip()

            data = json.loads(cleaned)
        except (json.JSONDecodeError, IndexError):
            return ValidationResult(
                status=ValidationStatus.ESCALATE,
                reason=f"Could not parse semantic check response: {content[:200]}",
                confidence=0.0,
            )

        grounded = data.get("grounded", True)
        confidence = float(data.get("confidence", 0.5))
        reason = data.get("reason", "No reason provided")

        if grounded:
            return ValidationResult(
                status=ValidationStatus.APPROVED,
                reason=f"Semantically grounded: {reason}",
                confidence=confidence,
            )

        if confidence >= self.confidence_threshold:
            return ValidationResult(
                status=ValidationStatus.BLOCKED,
                reason=f"Hallucination detected: {reason}",
                confidence=confidence,
            )

        return ValidationResult(
            status=ValidationStatus.ESCALATE,
            reason=f"Possible hallucination (low confidence): {reason}",
            confidence=confidence,
        )
