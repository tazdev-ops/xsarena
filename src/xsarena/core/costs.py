def approx_tokens(s: str) -> int:
    """Approximate token count by dividing character count by 4"""
    return (len(s) + 3) // 4


def estimate_cost(messages, provider: str = "openrouter"):
    """
    Estimate cost of messages based on provider pricing.
    messages: list of message dicts with role and content
    """
    input_tokens = 0
    output_tokens = 0

    for msg in messages:
        content = msg.get("content", "")
        if isinstance(content, str):
            if msg.get("role") == "user":
                input_tokens += approx_tokens(content)
            else:
                output_tokens += approx_tokens(content)

    # Default OpenRouter pricing (approximate)
    pricing = {
        "openrouter": {
            "input_token_cost": 0.0000005,  # $0.50 per 1M input tokens
            "output_token_cost": 0.0000015,  # $1.50 per 1M output tokens
        }
    }

    provider_pricing = pricing.get(provider, pricing["openrouter"])

    input_cost = input_tokens * provider_pricing["input_token_cost"]
    output_cost = output_tokens * provider_pricing["output_token_cost"]
    total_cost = input_cost + output_cost

    return {
        "input_tokens": input_tokens,
        "output_tokens": output_tokens,
        "input_cost": input_cost,
        "output_cost": output_cost,
        "estimated_cost": total_cost,
    }
