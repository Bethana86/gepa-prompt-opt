# GEPA Prompt Optimization Report

This report presents the Pareto Front prompts discovered during the genetic optimization run.

## Pareto Front Trade-off Matrix

| Rank | Accuracy | Latency (s) | Token Cost / Run | Description |
| :--- | :--- | :--- | :--- | :--- |
| 1 | 100.0% | 0.1617s | 64.0 | Base: 'Categorize review sentiment as...', Format: 'Begin your response with the w...' |
| 2 | 62.5% | 0.1270s | 57.0 | Base: 'Classify review sentiment....', Format: 'Output only the label: Positiv...' |
| 3 | 50.0% | 0.1236s | 53.0 | Base: 'Classify review sentiment....', Format: 'Provide a single-word response...' |

## Detailed Pareto-Optimal Prompts

### Candidate #1
- **Accuracy**: 100.0%
- **Latency**: 0.1617 seconds
- **Cost**: 64.0 tokens/run

```markdown
Categorize review sentiment as Positive, Negative, or Neutral.

Formatting: Begin your response with the word: Sentiment:

Constraint: Think carefully before answering.
```

---

### Candidate #2
- **Accuracy**: 62.5%
- **Latency**: 0.1270 seconds
- **Cost**: 57.0 tokens/run

```markdown
Classify review sentiment.

Formatting: Output only the label: Positive, Negative, or Neutral.

Constraint: Output directly the final classification.
```

---

### Candidate #3
- **Accuracy**: 50.0%
- **Latency**: 0.1236 seconds
- **Cost**: 53.0 tokens/run

```markdown
Classify review sentiment.

Formatting: Provide a single-word response.

Constraint: Output directly the final classification.
```

---

