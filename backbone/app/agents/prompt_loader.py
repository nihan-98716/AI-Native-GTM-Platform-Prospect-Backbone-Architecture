from pathlib import Path


PROMPT_DIR = Path(__file__).resolve().parent / "prompts"


def load_system_prompt(prompt_name: str) -> str:
    path = PROMPT_DIR / prompt_name
    if not path.exists():
        raise FileNotFoundError(f"Missing agent prompt file: {path}")
    return path.read_text(encoding="utf-8").strip()

