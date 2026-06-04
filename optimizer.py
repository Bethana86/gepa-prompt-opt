# optimizer.py
"""Implementation of the NSGA-II Genetic Algorithm for prompt optimization."""

import random
import config
import evaluator

def dominates(cand_a: dict, cand_b: dict) -> bool:
    """Returns True if candidate A dominates candidate B.

    A dominates B if it is better in at least one objective and not worse in any.
    Objectives: accuracy (maximize), latency (minimize), tokens (minimize).
    """
    better_in_at_least_one = False
    
    for obj in ["accuracy", "latency", "tokens"]:
        val_a = cand_a["metrics"][obj]
        val_b = cand_b["metrics"][obj]
        
        if obj == "accuracy":
            # Higher accuracy is better
            if val_a < val_b:
                return False
            elif val_a > val_b:
                better_in_at_least_one = True
        else:
            # Lower latency/tokens is better
            if val_a > val_b:
                return False
            elif val_a < val_b:
                better_in_at_least_one = True
                
    return better_in_at_least_one

def non_dominated_sort(population: list) -> list:
    """Sorts population into ranks of non-dominated fronts (NSGA-II).

    Returns:
        list of list: Indices of population sorted into fronts. Front 0 is the Pareto Front.
    """
    fronts = [[]]
    domination_count = {}
    dominated_candidates = {}
    
    for p_idx, p in enumerate(population):
        domination_count[p_idx] = 0
        dominated_candidates[p_idx] = []
        
        for q_idx, q in enumerate(population):
            if p_idx == q_idx:
                continue
            if dominates(p, q):
                dominated_candidates[p_idx].append(q_idx)
            elif dominates(q, p):
                domination_count[p_idx] += 1
                
        if domination_count[p_idx] == 0:
            p["rank"] = 0
            fronts[0].append(p_idx)
            
    i = 0
    while len(fronts[i]) > 0:
        next_front = []
        for p_idx in fronts[i]:
            for q_idx in dominated_candidates[p_idx]:
                domination_count[q_idx] -= 1
                if domination_count[q_idx] == 0:
                    population[q_idx]["rank"] = i + 1
                    next_front.append(q_idx)
        i += 1
        fronts.append(next_front)
        
    if not fronts[-1]:
        fronts.pop()
        
    return fronts

def calculate_crowding_distance(front_indices: list, population: list):
    """Calculates the crowding distance of candidates in a front to maintain diversity."""
    if not front_indices:
        return
        
    num_members = len(front_indices)
    if num_members <= 2:
        for idx in front_indices:
            population[idx]["crowding_distance"] = float('inf')
        return
        
    for idx in front_indices:
        population[idx]["crowding_distance"] = 0.0
        
    for obj in ["accuracy", "latency", "tokens"]:
        # Sort based on objective value
        sorted_indices = sorted(front_indices, key=lambda idx: population[idx]["metrics"][obj])
        
        # Boundaries get infinite distance
        population[sorted_indices[0]]["crowding_distance"] = float('inf')
        population[sorted_indices[-1]]["crowding_distance"] = float('inf')
        
        min_val = population[sorted_indices[0]]["metrics"][obj]
        max_val = population[sorted_indices[-1]]["metrics"][obj]
        
        range_val = max_val - min_val
        if range_val == 0:
            continue
            
        for i in range(1, num_members - 1):
            curr_idx = sorted_indices[i]
            prev_idx = sorted_indices[i - 1]
            next_idx = sorted_indices[i + 1]
            
            population[curr_idx]["crowding_distance"] += (
                (population[next_idx]["metrics"][obj] - population[prev_idx]["metrics"][obj]) / range_val
            )

def select_parents(population: list, num_parents: int) -> list:
    """Selects parents using tournament selection based on Rank and Crowding Distance."""
    parents = []
    for _ in range(num_parents):
        # Sample 3 random candidates for a tournament
        tournament = random.sample(population, 3)
        # Sort by rank (lower is better), then crowding distance (higher is better)
        tournament_sorted = sorted(
            tournament, 
            key=lambda x: (x.get("rank", 999), -x.get("crowding_distance", 0))
        )
        parents.append(tournament_sorted[0])
    return parents

def crossover(parent1: dict, parent2: dict) -> tuple:
    """Performs single-point crossover by swapping instruction genes."""
    child1 = {
        "base": parent1["base"],
        "formatting": parent1["formatting"],
        "reasoning": parent1["reasoning"]
    }
    child2 = {
        "base": parent2["base"],
        "formatting": parent2["formatting"],
        "reasoning": parent2["reasoning"]
    }
    
    if random.random() < config.CROSSOVER_RATE:
        # Pick a gene to swap
        gene = random.choice(["base", "formatting", "reasoning"])
        child1[gene] = parent2[gene]
        child2[gene] = parent1[gene]
        
    return child1, child2

def mutate(candidate: dict) -> dict:
    """Mutates genes randomly based on defined mutation rate."""
    mutated = candidate.copy()
    
    if random.random() < config.MUTATION_RATE:
        gene = random.choice(["base", "formatting", "reasoning"])
        if gene == "base":
            mutated["base"] = random.choice(config.BASE_INSTRUCTIONS)
        elif gene == "formatting":
            mutated["formatting"] = random.choice(config.FORMATTING_CONSTRAINTS)
        elif gene == "reasoning":
            mutated["reasoning"] = random.choice(config.REASONING_INSTRUCTIONS)
            
    return mutated

def initialize_population() -> list:
    """Generates initial population combining seed prompts and random combinations."""
    population = []
    
    # 1. Add initial seed prompts
    for p in config.INITIAL_PROMPTS:
        population.append({
            "base": p["base"],
            "formatting": p["formatting"],
            "reasoning": p["reasoning"],
            "metrics": None
        })
        
    # 2. Fill the rest of the population with random combinations
    while len(population) < config.POPULATION_SIZE:
        population.append({
            "base": random.choice(config.BASE_INSTRUCTIONS),
            "formatting": random.choice(config.FORMATTING_CONSTRAINTS),
            "reasoning": random.choice(config.REASONING_INSTRUCTIONS),
            "metrics": None
        })
        
    return population
