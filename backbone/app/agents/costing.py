from app.contracts.agents import AgentEstimate


MODEL_COST_PER_1K_INPUT = {
    "gpt-4.1-mini": 0.0004,
    "gpt-4.1": 0.0020,
    "heuristic-fallback": 0.0,
}

MODEL_COST_PER_1K_OUTPUT = {
    "gpt-4.1-mini": 0.0016,
    "gpt-4.1": 0.0080,
    "heuristic-fallback": 0.0,
}

MODEL_LATENCY_MS = {
    "gpt-4.1-mini": 1200,
    "gpt-4.1": 2200,
    "heuristic-fallback": 120,
}


def estimate_usage(*, model: str, input_payload: dict, output_payload: dict) -> AgentEstimate:
    token_input = max(1, len(str(input_payload)) // 4)
    token_output = max(1, len(str(output_payload)) // 4)
    cost_input = MODEL_COST_PER_1K_INPUT.get(model, 0.0) * (token_input / 1000)
    cost_output = MODEL_COST_PER_1K_OUTPUT.get(model, 0.0) * (token_output / 1000)
    return AgentEstimate(
        model=model,
        estimated_input_tokens=token_input,
        estimated_output_tokens=token_output,
        estimated_cost_usd=round(cost_input + cost_output, 6),
        estimated_latency_ms=MODEL_LATENCY_MS.get(model, 2000),
    )

