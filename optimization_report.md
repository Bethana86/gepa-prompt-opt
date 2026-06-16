# GEPA Prompt Optimization Report

This report presents the Pareto Front prompts discovered during the genetic optimization run.

## Pareto Front Trade-off Matrix

| Rank | Accuracy | Latency (s) | Token Cost / Run | Description |
| :--- | :--- | :--- | :--- | :--- |
| 1 | 100.0% | 0.1564s | 59.0 | Base: 'Classify review sentiment....', Format: 'Begin your response with the w...' |
| 2 | 62.5% | 0.1295s | 61.0 | Base: 'Classify review sentiment....', Format: 'Output only the label: Positiv...' |

## Detailed Pareto-Optimal Prompts

### Candidate #1
- **Accuracy**: 100.0%
- **Latency**: 0.1564 seconds
- **Cost**: 59.0 tokens/run

```markdown
Classify review sentiment.

Formatting: Begin your response with the word: Sentiment:

Constraint: Think carefully before answering.
```

---

### Candidate #2
- **Accuracy**: 62.5%
- **Latency**: 0.1295 seconds
- **Cost**: 61.0 tokens/run

```markdown
Classify review sentiment.

Formatting: Output only the label: Positive, Negative, or Neutral.

Constraint: Do not write any explanation, just print the label.
```

---

