# evaluator.py
"""Evaluation module that runs the ADK Agent and compiles Pareto objectives."""

import asyncio
from google.adk.agents.llm_agent import LlmAgent
from google.adk.runners import InMemoryRunner
from google.genai import types

import telemetry
import config

# Setup telemetry exporter (only once)
telemetry.setup_telemetry()

def verify_response(response_text: str, expected: str) -> bool:
    """Verifies if the LLM response contains the correct sentiment classification.

    Handles JSON formatting and plain-text output matching.
    """
    clean_resp = response_text.lower().strip()
    clean_exp = expected.lower()

    # JSON extraction helper
    if "{" in clean_resp and "}" in clean_resp:
        # Check if the expected sentiment is the value of the sentiment key
        pattern = rf'"sentiment"\s*:\s*"{clean_exp}"'
        if re_match := re_search(pattern, clean_resp):
            return True

    # Single word or prefix match
    # Ensure word boundaries to avoid matching 'positive' in 'not positive'
    if clean_exp in clean_resp:
        if f"not {clean_exp}" in clean_resp or f"isn't {clean_exp}" in clean_resp:
            return False
        return True

    return False

import re
def re_search(pattern, text):
    try:
        return bool(re.search(pattern, text))
    except Exception:
        return False

async def evaluate_candidate(candidate: dict) -> dict:
    """Runs a prompt candidate over the evaluation dataset and gathers trace metrics.

    Args:
        candidate (dict): A dictionary representing the prompt genome (base, formatting, reasoning).

    Returns:
        dict: Compiled objective metrics containing 'accuracy', 'latency', and 'tokens'.
    """
    # 1. Compile system instruction from candidate genome
    system_instruction = (
        f"{candidate['base']}\n\n"
        f"Formatting: {candidate['formatting']}\n\n"
        f"Constraint: {candidate['reasoning']}"
    )

    # 2. Instantiate Google ADK LlmAgent
    # The name must be a valid Python identifier (no dashes)
    agent = LlmAgent(
        name="prompt_evaluation_agent",
        model="mock-model",
        instruction=system_instruction
    )

    total_accuracy = 0
    total_latency = 0.0
    total_tokens = 0

    # 3. Iterate over the dataset and evaluate
    for idx, item in enumerate(config.EVAL_DATASET):
        # Clear telemetry spans for a fresh capture
        telemetry.clear_spans()

        user_msg = types.Content(
            role="user",
            parts=[types.Part(text=f"Review: {item['input']}")]
        )

        try:
            # InMemoryRunner handles local execution
            async with InMemoryRunner(agent=agent) as runner:
                runner.auto_create_session = True
                
                # Run evaluation synchronously/asynchronously
                # InMemoryRunner.run returns a generator of events
                events = list(runner.run(
                    user_id=f"eval_user_{idx}",
                    session_id=f"eval_session_{idx}",
                    new_message=user_msg
                ))

            # Retrieve telemetry data captured from OpenTelemetry spans
            metrics = telemetry.get_captured_metrics()
            
            # Record metrics
            is_correct = verify_response(metrics["response_text"], item["expected"])
            total_accuracy += 1 if is_correct else 0
            total_latency += metrics["latency"]
            total_tokens += (metrics["input_tokens"] + metrics["output_tokens"])

        except Exception as e:
            # Handle execution failures gracefully
            print(f"Error during evaluation of dataset item {idx}: {e}")
            total_tokens += 100  # Penalty tokens
            total_latency += 1.0  # Penalty latency

    num_items = len(config.EVAL_DATASET)
    return {
        "accuracy": total_accuracy / num_items,
        "latency": total_latency / num_items,
        "tokens": total_tokens / num_items
    }
