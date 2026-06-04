# Automated Prompt Optimization using GEPA Framework in Google ADK

This directory contains a prototype of the **Genetic Pareto (GEPA)** prompt optimization framework. The framework optimizes prompts over multiple conflicting objectives (Accuracy, Latency, and Token Cost) using the **Google Antigravity SDK (ADK)** and its native **OpenTelemetry** integration.

## How it Works

1. **Prompt Genomes**: A prompt template is represented as three combined genes:
   - `base`: General instructions (e.g., "Classify review sentiment.")
   - `formatting`: Output structure directives (e.g., "Respond in JSON format.")
   - `reasoning`: Cognitive/constraint directives (e.g., "Explain step-by-step.")
2. **Mock LLM Simulation (`mock_llm.py`)**: Subclasses `google.adk.models.BaseLlm` and registers it in `LLMRegistry` to simulate realistic model behaviors. It generates answers and telemetry dynamically:
   - Base classification correctness depends on review difficulty (easy, medium, hard).
   - Reasoning genes ("step-by-step") increase accuracy, but add token counts and latency.
   - Formatting rules improve output structuring.
   - Conflicting constraints (e.g., "Explain step-by-step" + "be brief") trigger accuracy penalties.
3. **Observability Trace Metrics (`telemetry.py`)**: Initialized with an in-memory span exporter. When the ADK agent runs, it automatically emits telemetry spans (`invoke_agent`, `call_llm`, `generate_content`). We extract:
   - **Cost (Tokens)**: `gen_ai.usage.input_tokens` and `gen_ai.usage.output_tokens`.
   - **Latency**: Actual duration (start to end time of `call_llm` span).
   - **Accuracy**: Checked directly from the response content extracted from the span attribute.
4. **Pareto Domination Selection (`optimizer.py`)**: Uses the NSGA-II algorithm to sort the population into fronts of non-dominated candidates. It calculates crowding distance to preserve diversity along the trade-off front (Pareto Front).
5. **Genetic Operators**: Parents are selected using tournament selection. Crossover swaps segments, and mutation introduces new base prompts, formatting rules, or reasoning constraints.

## Project Structure

- **`config.py`**: Evaluation dataset (8 reviews with mixed difficulty) and genetic parameters (population size, mutation rate).
- **`mock_llm.py`**: Custom registered LLM simulating real LLM performance and token costs.
- **`telemetry.py`**: Intercepts OpenTelemetry spans emitted by Google ADK to collect execution metrics.
- **`evaluator.py`**: Executes the Google ADK `InMemoryRunner` for each evaluation task and compiles average metrics.
- **`optimizer.py`**: Implements Pareto sorting, crowding distance calculation, tournament selection, crossover, and mutation.
- **`main.py`**: Main application that runs the optimization loop, prints logs per generation, and writes `optimization_report.md`.

## Execution

Ensure that Python 3.11+ is installed. In this directory, run the driver script:

```bash
py main.py
```

Upon completion, a report file `optimization_report.md` will be created with a trade-off matrix showing the Pareto front prompts.
