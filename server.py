# server.py
"""FastAPI Backend Server for GEPA Prompt Optimizer Dashboard."""

import asyncio
import json
import os
import uvicorn
from fastapi import FastAPI, Request
from fastapi.responses import StreamingResponse, HTMLResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

import mock_llm  # Ensures MockLlm is registered in ADK
import config
import evaluator
import optimizer

app = FastAPI(title="GEPA Prompt Optimizer Dashboard")

# Ensure static files directory exists
os.makedirs("static", exist_ok=True)

class RunAgentRequest(BaseModel):
    base: str
    formatting: str
    reasoning: str
    query: str

class OptimizationRequest(BaseModel):
    pop_size: int = 8
    generations: int = 5

@app.post("/api/run-agent")
async def run_agent_endpoint(payload: RunAgentRequest):
    """Executes a single customer support agent query and returns output + trace metadata."""
    candidate = {
        "base": payload.base,
        "formatting": payload.formatting,
        "reasoning": payload.reasoning
    }
    result = await evaluator.run_single_query(candidate, payload.query)
    return result

async def optimization_stream(pop_size: int, generations: int):
    """SSE Generator yielding GA optimization steps and metrics in real time."""
    try:
        yield f"data: {json.dumps({'event': 'status', 'message': 'Initializing starting population...'})}\n\n"
        await asyncio.sleep(0.1)

        population = optimizer.initialize_population()
        if len(population) > pop_size:
            population = population[:pop_size]

        # Initial evaluation
        for idx, candidate in enumerate(population):
            yield f"data: {json.dumps({'event': 'status', 'message': f'Evaluating base prompt candidate {idx+1}/{len(population)}...'})}\n\n"
            candidate["metrics"] = await evaluator.evaluate_candidate(candidate)

        # Sort initial pop
        fronts = optimizer.non_dominated_sort(population)
        for front in fronts:
            optimizer.calculate_crowding_distance(front, population)

        # Emit Generation 0 state
        yield f"data: {json.dumps({'event': 'generation', 'gen': 0, 'population': population, 'front_size': len(fronts[0])})}\n\n"
        await asyncio.sleep(0.5)

        # Optimization Generations
        for gen in range(1, generations + 1):
            yield f"data: {json.dumps({'event': 'status', 'message': f'Starting Generation {gen}/{generations}...'})}\n\n"
            await asyncio.sleep(0.1)

            # Parents Selection & Crossover/Mutation
            parents = optimizer.select_parents(population, len(population))
            offspring = []
            for i in range(0, len(parents), 2):
                if i + 1 < len(parents):
                    child1, child2 = optimizer.crossover(parents[i], parents[i+1])
                    child1 = optimizer.mutate(child1)
                    child2 = optimizer.mutate(child2)
                    offspring.extend([child1, child2])
                else:
                    child = optimizer.mutate(parents[i])
                    offspring.append(child)

            # Evaluate Offspring
            for idx, child in enumerate(offspring):
                yield f"data: {json.dumps({'event': 'status', 'message': f'Evaluating offspring {idx+1}/{len(offspring)} in Generation {gen}...'})}\n\n"
                child["metrics"] = await evaluator.evaluate_candidate(child)

            # Combine and Sort
            combined = population + offspring
            combined_fronts = optimizer.non_dominated_sort(combined)
            for front in combined_fronts:
                optimizer.calculate_crowding_distance(front, combined)

            # Select N best
            next_population = []
            for front in combined_fronts:
                if len(next_population) + len(front) <= len(population):
                    next_population.extend([combined[idx] for idx in front])
                else:
                    remaining = sorted(front, key=lambda idx: combined[idx].get("crowding_distance", 0), reverse=True)
                    space = len(population) - len(next_population)
                    next_population.extend([combined[idx] for idx in remaining[:space]])
                    break

            population = next_population
            fronts = optimizer.non_dominated_sort(population)
            for front in fronts:
                optimizer.calculate_crowding_distance(front, population)

            # Emit generation update
            yield f"data: {json.dumps({'event': 'generation', 'gen': gen, 'population': population, 'front_size': len(fronts[0])})}\n\n"
            await asyncio.sleep(0.5)

        # Final optimal prompts on Pareto Front
        final_pareto = [population[idx] for idx in fronts[0]]
        final_pareto = sorted(final_pareto, key=lambda x: x["metrics"]["accuracy"], reverse=True)

        yield f"data: {json.dumps({'event': 'complete', 'pareto_front': final_pareto})}\n\n"

    except Exception as e:
        yield f"data: {json.dumps({'event': 'error', 'message': str(e)})}\n\n"

@app.get("/api/optimize/stream")
async def optimize_stream_endpoint(pop_size: int = 8, generations: int = 5):
    """Establishes an SSE stream to send real-time GA optimization updates."""
    return StreamingResponse(
        optimization_stream(pop_size, generations),
        media_type="text/event-stream"
    )

# Fallback root path to serve UI
@app.get("/", response_class=HTMLResponse)
async def root():
    index_path = os.path.join("static", "index.html")
    if os.path.exists(index_path):
        with open(index_path, "r", encoding="utf-8") as f:
            return HTMLResponse(content=f.read())
    return HTMLResponse("<h2>Error: static/index.html not found. Please verify placement.</h2>")

# Mount static files router
app.mount("/static", StaticFiles(directory="static"), name="static")

if __name__ == "__main__":
    uvicorn.run("server:app", host="127.0.0.1", port=8000, reload=False)
