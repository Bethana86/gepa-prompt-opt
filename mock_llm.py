# mock_llm.py
"""Simulated LLM for testing the GEPA optimizer without requiring API keys."""

import asyncio
import re
from typing import AsyncGenerator
from google.adk.models.base_llm import BaseLlm
from google.adk.models.llm_request import LlmRequest
from google.adk.models.llm_response import LlmResponse
from google.adk.models.registry import LLMRegistry
from google.genai import types

class MockLlm(BaseLlm):
    """A simulated LLM provider that mimics realistic LLM behavior.

    Optimizes performance metrics (latency, cost, accuracy) dynamically based on 
    the system instructions and prompt complexity.
    """
    model: str = "mock-model"

    @classmethod
    def supported_models(cls) -> list[str]:
        return ["mock-model.*"]

    async def generate_content_async(
        self, llm_request: LlmRequest, stream: bool = False
    ) -> AsyncGenerator[LlmResponse, None]:
        # 1. Parse system instruction and user prompt
        system_instruction = ""
        if llm_request.config and llm_request.config.system_instruction:
            inst = llm_request.config.system_instruction
            if isinstance(inst, str):
                system_instruction = inst
            elif hasattr(inst, 'parts') and inst.parts:
                system_instruction = "".join(p.text for p in inst.parts if p.text)

        user_prompt = ""
        if llm_request.contents:
            for content in llm_request.contents:
                if content.parts:
                    user_prompt += "".join(p.text for p in content.parts if p.text)

        # 2. Evaluate prompt quality metrics
        has_reasoning = any(word in system_instruction.lower() for word in ["reasoning", "step-by-step", "think carefully"])
        has_brief = any(word in system_instruction.lower() for word in ["just print the label", "single-word", "directly"])
        has_json = "json" in system_instruction.lower()
        has_prefix = "sentiment:" in system_instruction.lower()

        # Compute prompt quality score (affects accuracy)
        quality_score = 0.55  # Base accuracy factor

        if has_reasoning:
            quality_score += 0.25  # Reasoning gives a large accuracy boost
        if has_json or has_prefix or "output only" in system_instruction.lower():
            quality_score += 0.15  # Formatting constraints help structure output

        # Contradiction penalties
        if has_reasoning and has_brief:
            quality_score -= 0.35  # Conflicting instructions hurt accuracy significantly
        if "json" in system_instruction.lower() and "single-word" in system_instruction.lower():
            quality_score -= 0.20  # Another minor format conflict

        # Clip quality score
        quality_score = max(0.10, min(1.0, quality_score))

        # 3. Classify sentiment deterministically based on input content
        # Find expected sentiment from user prompt keywords (matching config.py dataset)
        expected = "Neutral"
        if any(w in user_prompt.lower() for w in ["perfectly", "recommended", "exceptional", "delighted"]):
            expected = "Positive"
        elif any(w in user_prompt.lower() for w in ["terrible", "broke", "garbage", "bad"]):
            expected = "Negative"

        # Determine difficulty of classification
        # Hard reviews have mixed sentiments or subtle tones
        is_hard = any(w in user_prompt.lower() for w in ["color", "spectacular", "value for money"])
        is_medium = any(w in user_prompt.lower() for w in ["overpriced", "alright"])

        # Determine if classifed correctly based on prompt quality
        correct = False
        if is_hard:
            correct = (quality_score >= 0.85)  # Hard reviews need reasoning + format
        elif is_medium:
            correct = (quality_score >= 0.70)  # Medium reviews need at least one of them
        else:
            correct = (quality_score >= 0.40)  # Easy reviews are classified by almost any prompt

        actual_sentiment = expected if correct else ("Negative" if expected == "Positive" else "Positive")

        # 4. Construct output format
        if has_json:
            response_text = f'{{"sentiment": "{actual_sentiment}"}}'
            output_tokens = 15
        elif has_prefix:
            response_text = f"Sentiment: {actual_sentiment}"
            output_tokens = 6
        elif has_brief:
            response_text = actual_sentiment
            output_tokens = 2
        else:
            if has_reasoning:
                response_text = (
                    f"The user review contains key terms. Analyzing tone... "
                    f"Reasoning: The words suggest a classification. "
                    f"Therefore, the sentiment is {actual_sentiment}."
                )
                output_tokens = 50
            else:
                response_text = f"I classify this review sentiment as {actual_sentiment}."
                output_tokens = 10

        # Calculate simulated token counts
        input_tokens = len(system_instruction.split()) + len(user_prompt.split()) + 15
        total_tokens = input_tokens + output_tokens

        # Calculate simulated latency (base + prompt ingestion + generation time)
        simulated_latency = 0.05 + (input_tokens * 0.001) + (output_tokens * 0.008)
        await asyncio.sleep(simulated_latency)

        # 5. Build and yield response
        content = types.Content(
            role="model",
            parts=[types.Part(text=response_text)]
        )
        usage = types.GenerateContentResponseUsageMetadata(
            prompt_token_count=input_tokens,
            candidates_token_count=output_tokens,
            total_token_count=total_tokens
        )

        yield LlmResponse(
            content=content,
            partial=False,
            finish_reason=types.FinishReason.STOP,
            usage_metadata=usage
        )

# Automatically register MockLlm upon import
LLMRegistry.register(MockLlm)
print("MockLlm successfully registered with ADK LLMRegistry.")
