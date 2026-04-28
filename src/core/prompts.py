import os
import logging

def load_prompt(filename: str) -> str:
    """
    Loads a markdown prompt file containing the agent's core skill guidelines from the src/prompts directory.
    """
    filepath = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "prompts", filename)
    try:
        with open(filepath, "r", encoding="utf-8") as f:
            return f.read()
    except FileNotFoundError:
        logging.error(f"Prompt file '{filename}' not found at {filepath}")
        return ""
