def validate_system_prompt(prompt: str) -> bool:
    if not prompt:
        raise ValueError("System prompt cannot be empty.")
    invalid_chars = '<>{}'
    for c in prompt:
        if c in invalid_chars:
            raise ValueError(f"Invalid character in system prompt: {c}")
    return True