# config.py
"""Configuration settings and datasets for the GEPA Prompt Optimizer."""

# Genetic Algorithm Parameters
POPULATION_SIZE = 8
GENERATIONS = 6
MUTATION_RATE = 0.4
CROSSOVER_RATE = 0.7

# Evaluation Dataset
# Each item has an 'input' review and 'expected' classification.
EVAL_DATASET = [
    {
        "input": "The product arrived on time, was extremely easy to install, and works perfectly. Best purchase this year!",
        "expected": "Positive"
    },
    {
        "input": "Terrible. It broke within 10 minutes of use. Customer support refused to refund.",
        "expected": "Negative"
    },
    {
        "input": "It is okay, works as expected but is quite overpriced for the quality.",
        "expected": "Neutral"
    },
    {
        "input": "I didn't like the color, and the shipping took three weeks. However, customer service was helpful.",
        "expected": "Neutral"
    },
    {
        "input": "Unbelievably good service and high-quality build. Highly recommended!",
        "expected": "Positive"
    },
    {
        "input": "Absolute garbage, do not buy! It doesn't even turn on.",
        "expected": "Negative"
    },
    {
        "input": "It performs alright. Nothing spectacular, but gets the basic job done.",
        "expected": "Neutral"
    },
    {
        "input": "Exceptional value for money. Very durable and functional.",
        "expected": "Positive"
    }
]

# Base components for generating initial prompts and applying mutations
BASE_INSTRUCTIONS = [
    "Classify review sentiment.",
    "Analyze the product review and determine its sentiment.",
    "You are a helpful assistant. Classify the user feedback into Positive, Negative, or Neutral.",
    "Categorize review sentiment as Positive, Negative, or Neutral."
]

FORMATTING_CONSTRAINTS = [
    "Output only the label: Positive, Negative, or Neutral.",
    "Respond in JSON format: {'sentiment': label}",
    "Provide a single-word response.",
    "Begin your response with the word: Sentiment:"
]

REASONING_INSTRUCTIONS = [
    "Do not write any explanation, just print the label.",
    "Explain your reasoning step-by-step before deciding.",
    "Think carefully before answering.",
    "Output directly the final classification."
]

# Seed prompts representing the initial population
INITIAL_PROMPTS = [
    {
        "base": "Classify review sentiment.",
        "formatting": "Output only the label: Positive, Negative, or Neutral.",
        "reasoning": "Do not write any explanation, just print the label."
    },
    {
        "base": "Analyze the product review and determine its sentiment.",
        "formatting": "Respond in JSON format: {'sentiment': label}",
        "reasoning": "Explain your reasoning step-by-step before deciding."
    },
    {
        "base": "You are a helpful assistant. Classify the user feedback into Positive, Negative, or Neutral.",
        "formatting": "Provide a single-word response.",
        "reasoning": "Output directly the final classification."
    },
    {
        "base": "Categorize review sentiment as Positive, Negative, or Neutral.",
        "formatting": "Begin your response with the word: Sentiment:",
        "reasoning": "Think carefully before answering."
    }
]
