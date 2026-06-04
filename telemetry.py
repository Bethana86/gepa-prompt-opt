# telemetry.py
"""OpenTelemetry integration for capturing execution metrics from Google ADK."""

import json
from opentelemetry import trace
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import SimpleSpanProcessor
from opentelemetry.sdk.trace.export.in_memory_span_exporter import InMemorySpanExporter

# Global telemetry components
_provider = None
_exporter = None

def setup_telemetry():
    """Initializes the OpenTelemetry TracerProvider with an InMemorySpanExporter."""
    global _provider, _exporter
    if _provider is None:
        _provider = TracerProvider()
        _exporter = InMemorySpanExporter()
        processor = SimpleSpanProcessor(_exporter)
        _provider.add_span_processor(processor)
        trace.set_tracer_provider(_provider)
    return _exporter

def clear_spans():
    """Resets the in-memory exporter, clearing previously captured spans."""
    if _exporter is not None:
        _exporter.clear()

def get_captured_metrics():
    """Parses captured spans to retrieve latency, token usage, and response text.

    Returns:
        dict: A dictionary containing:
            - 'latency' (float): Execution time in seconds.
            - 'input_tokens' (int): Number of prompt tokens used.
            - 'output_tokens' (int): Number of response tokens generated.
            - 'response_text' (str): The raw textual output from the model.
    """
    if _exporter is None:
        return {"latency": 0.0, "input_tokens": 0, "output_tokens": 0, "response_text": ""}

    spans = _exporter.get_finished_spans()
    metrics = {
        "latency": 0.0,
        "input_tokens": 0,
        "output_tokens": 0,
        "response_text": ""
    }

    # Find the 'call_llm' span which contains the full request and response attributes
    for span in spans:
        if span.name == "call_llm":
            metrics["latency"] = (span.end_time - span.start_time) / 1e9
            metrics["input_tokens"] = span.attributes.get("gen_ai.usage.input_tokens", 0)
            metrics["output_tokens"] = span.attributes.get("gen_ai.usage.output_tokens", 0)

            # Try to parse the response text from gcp.vertex.agent.llm_response attribute
            resp_str = span.attributes.get("gcp.vertex.agent.llm_response")
            if resp_str:
                try:
                    resp_dict = json.loads(resp_str)
                    parts = resp_dict.get("content", {}).get("parts", [])
                    if parts:
                        metrics["response_text"] = "".join(p.get("text", "") for p in parts if "text" in p)
                except Exception:
                    pass
            break

    # Fallback to 'generate_content' if 'call_llm' wasn't captured or was empty
    if not metrics["response_text"]:
        for span in spans:
            if "generate_content" in span.name:
                metrics["latency"] = max(metrics["latency"], (span.end_time - span.start_time) / 1e9)
                metrics["input_tokens"] = max(metrics["input_tokens"], span.attributes.get("gen_ai.usage.input_tokens", 0))
                metrics["output_tokens"] = max(metrics["output_tokens"], span.attributes.get("gen_ai.usage.output_tokens", 0))

    return metrics
