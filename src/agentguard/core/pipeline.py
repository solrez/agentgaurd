"""Validator pipeline — runs a chain of validators against an action."""

from __future__ import annotations

import asyncio
import time
from typing import Sequence

from agentguard.core.action import AgentAction
from agentguard.validators.base import BaseValidator, ValidationResult, ValidationStatus


class PipelineResult:
    """Aggregated result from running all validators in the pipeline."""

    def __init__(self, results: list[ValidationResult], latency_ms: float):
        self.results = results
        self.latency_ms = latency_ms

    @property
    def all_passed(self) -> bool:
        return all(r.passed for r in self.results)

    @property
    def blocked(self) -> bool:
        return any(r.status == ValidationStatus.BLOCKED for r in self.results)

    @property
    def needs_escalation(self) -> bool:
        return any(r.status == ValidationStatus.ESCALATE for r in self.results)

    @property
    def has_modifications(self) -> bool:
        return any(r.status == ValidationStatus.MODIFIED for r in self.results)

    @property
    def block_reasons(self) -> list[str]:
        return [r.reason for r in self.results if r.status == ValidationStatus.BLOCKED]

    @property
    def suggested_fixes(self) -> list[dict]:
        return [r.suggested_fix for r in self.results if r.suggested_fix is not None]

    def __repr__(self) -> str:
        statuses = [r.status.value for r in self.results]
        return f"<PipelineResult statuses={statuses} latency={self.latency_ms:.1f}ms>"


class ValidatorPipeline:
    """Runs validators against an agent action.

    Validators run concurrently by default. Use `sequential=True` for ordered execution
    that stops on the first block.
    """

    def __init__(
        self,
        validators: Sequence[BaseValidator],
        sequential: bool = False,
        fail_fast: bool = True,
    ):
        self.validators = list(validators)
        self.sequential = sequential
        self.fail_fast = fail_fast
        self._initialized = False

    async def setup(self) -> None:
        if not self._initialized:
            await asyncio.gather(*(v.setup() for v in self.validators))
            self._initialized = True

    async def run(self, action: AgentAction) -> PipelineResult:
        await self.setup()
        start = time.perf_counter()

        if self.sequential:
            results = await self._run_sequential(action)
        else:
            results = await self._run_concurrent(action)

        latency_ms = (time.perf_counter() - start) * 1000
        return PipelineResult(results=results, latency_ms=latency_ms)

    async def _run_concurrent(self, action: AgentAction) -> list[ValidationResult]:
        tasks = [v.validate(action) for v in self.validators]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        validated = []
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                validated.append(
                    ValidationResult(
                        validator_name=self.validators[i].name,
                        status=ValidationStatus.ESCALATE,
                        reason=f"Validator error: {result}",
                        confidence=0.0,
                    )
                )
            else:
                result.validator_name = self.validators[i].name
                validated.append(result)
        return validated

    async def _run_sequential(self, action: AgentAction) -> list[ValidationResult]:
        results = []
        for validator in self.validators:
            try:
                result = await validator.validate(action)
                result.validator_name = validator.name
                results.append(result)

                if self.fail_fast and result.status == ValidationStatus.BLOCKED:
                    break
            except Exception as e:
                results.append(
                    ValidationResult(
                        validator_name=validator.name,
                        status=ValidationStatus.ESCALATE,
                        reason=f"Validator error: {e}",
                        confidence=0.0,
                    )
                )
                if self.fail_fast:
                    break
        return results

    async def teardown(self) -> None:
        await asyncio.gather(*(v.teardown() for v in self.validators))

    def __repr__(self) -> str:
        names = [v.name for v in self.validators]
        return f"<ValidatorPipeline validators={names}>"
