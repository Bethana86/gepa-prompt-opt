# main.py
"""Entry point for running the GEPA automated prompt optimization prototype."""

import sys
import asyncio
import os

import mock_llm  # Registers MockLlm
import config
import evaluator
import optimizer

async def run_optimization():
    print("=" * 70)
    print("         GEPA AUTOMATED PROMPT OPTIMIZER USING GOOGLE ADK")
    print("=" * 70)
    print(f"Population Size: {config.POPULATION_SIZE}")
    print(f"Generations    : {config.GENERATIONS}")
    print(f"Mutation Rate  : {config.MUTATION_RATE}")
    print(f"Crossover Rate : {config.CROSSOVER_RATE}")
    print(f"Dataset Size   : {len(config.EVAL_DATASET)} items")
    print("=" * 70)

    # 1. Initialize population
    print("\nInitializing population...")
    population = optimizer.initialize_population()

    # Initial evaluation of the population
    for idx, candidate in enumerate(population):
        print(f"Evaluating candidate {idx + 1}/{config.POPULATION_SIZE}...")
        candidate["metrics"] = await evaluator.evaluate_candidate(candidate)

    # Run initial sort
    fronts = optimizer.non_dominated_sort(population)
    for front in fronts:
        optimizer.calculate_crowding_distance(front, population)

    # 2. Main generation loop
    for gen in range(1, config.GENERATIONS + 1):
        print("\n" + "=" * 60)
        print(f" GENERATION {gen}/{config.GENERATIONS}")
        print("=" * 60)

        # Print current population stats
        print(f"{'No.':<4}{'Accuracy':<10}{'Latency (s)':<13}{'Tokens/Run':<12}{'Rank':<6}{'Crowd Dist':<10}")
        print("-" * 60)
        for idx, cand in enumerate(population):
            m = cand["metrics"]
            crowd = f"{cand.get('crowding_distance', 0.0):.4f}" if cand.get('crowding_distance') != float('inf') else "inf"
            print(f"{idx+1:<4}{m['accuracy']*100:>7.1f}%   {m['latency']:>9.4f}s  {m['tokens']:>10.1f}   {cand.get('rank', 0):<6}{crowd:<10}")

        # Print current Pareto front (Rank 0)
        pareto_front = [population[idx] for idx in fronts[0]]
        print(f"\nCurrent Pareto Front contains {len(pareto_front)} candidates.")

        # If it's the last generation, we don't need to generate offspring
        if gen == config.GENERATIONS:
            break

        # Generate Offspring
        print("\nGenerating offspring...")
        parents = optimizer.select_parents(population, config.POPULATION_SIZE)
        offspring = []
        
        for i in range(0, config.POPULATION_SIZE, 2):
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
            print(f"Evaluating offspring {idx + 1}/{len(offspring)}...")
            child["metrics"] = await evaluator.evaluate_candidate(child)

        # Combine parents and offspring
        combined = population + offspring
        
        # Sort and select N best
        combined_fronts = optimizer.non_dominated_sort(combined)
        for front in combined_fronts:
            optimizer.calculate_crowding_distance(front, combined)

        # Build next generation
        next_population = []
        for front in combined_fronts:
            if len(next_population) + len(front) <= config.POPULATION_SIZE:
                next_population.extend([combined[idx] for idx in front])
            else:
                # Sort remaining front by crowding distance descending and fill
                remaining = sorted(front, key=lambda idx: combined[idx].get("crowding_distance", 0), reverse=True)
                space = config.POPULATION_SIZE - len(next_population)
                next_population.extend([combined[idx] for idx in remaining[:space]])
                break

        population = next_population
        fronts = optimizer.non_dominated_sort(population)
        for front in fronts:
            optimizer.calculate_crowding_distance(front, population)

    # 3. Final Report & Pareto front summaries
    final_pareto = [population[idx] for idx in fronts[0]]
    
    # Sort Pareto front by Accuracy descending
    final_pareto = sorted(final_pareto, key=lambda x: x["metrics"]["accuracy"], reverse=True)

    print("\n" + "=" * 70)
    print("                     FINAL OPTIMIZATION SUMMARY")
    print("=" * 70)
    print(f"Total generations: {config.GENERATIONS}")
    print(f"Pareto optimal prompts found: {len(final_pareto)}")
    print("-" * 70)
    
    for rank, cand in enumerate(final_pareto):
        m = cand["metrics"]
        print(f"\n[Pareto Candidate #{rank + 1}]")
        print(f"  - Accuracy: {m['accuracy']*100:.1f}%")
        print(f"  - Latency : {m['latency']:.4f} seconds/run")
        print(f"  - Cost    : {m['tokens']:.1f} tokens/run")
        print("  - Prompt Template:")
        print(f"    - Base Instruction  : {cand['base']}")
        print(f"    - Formatting Rules  : {cand['formatting']}")
        print(f"    - Reasoning Style   : {cand['reasoning']}")

    # Save final report to a markdown file
    report_path = "optimization_report.md"
    with open(report_path, "w", encoding="utf-8") as f:
        f.write("# GEPA Prompt Optimization Report\n\n")
        f.write("This report presents the Pareto Front prompts discovered during the genetic optimization run.\n\n")
        
        f.write("## Pareto Front Trade-off Matrix\n\n")
        f.write("| Rank | Accuracy | Latency (s) | Token Cost / Run | Description |\n")
        f.write("| :--- | :--- | :--- | :--- | :--- |\n")
        for i, cand in enumerate(final_pareto):
            m = cand["metrics"]
            desc = f"Base: '{cand['base'][:30]}...', Format: '{cand['formatting'][:30]}...'"
            f.write(f"| {i+1} | {m['accuracy']*100:.1f}% | {m['latency']:.4f}s | {m['tokens']:.1f} | {desc} |\n")

        f.write("\n## Detailed Pareto-Optimal Prompts\n\n")
        for i, cand in enumerate(final_pareto):
            m = cand["metrics"]
            f.write(f"### Candidate #{i+1}\n")
            f.write(f"- **Accuracy**: {m['accuracy']*100:.1f}%\n")
            f.write(f"- **Latency**: {m['latency']:.4f} seconds\n")
            f.write(f"- **Cost**: {m['tokens']:.1f} tokens/run\n\n")
            f.write("```markdown\n")
            f.write(f"{cand['base']}\n\n")
            f.write(f"Formatting: {cand['formatting']}\n\n")
            f.write(f"Constraint: {cand['reasoning']}\n")
            f.write("```\n\n")
            f.write("---\n\n")

    print("\n" + "=" * 70)
    print(f"Markdown report generated: {os.path.abspath(report_path)}")
    print("=" * 70)

if __name__ == "__main__":
    sys.stdout.reconfigure(encoding='utf-8')
    asyncio.run(run_optimization())
