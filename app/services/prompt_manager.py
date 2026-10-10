import re
from functools import lru_cache
from pathlib import Path

PROMPT_DIR = Path(__file__).resolve().parent.parent / "prompts"
_VAR = re.compile(r"\{(\w+)\}")


@lru_cache(maxsize=None)
def _load(name: str) -> str:
    return (PROMPT_DIR / f"{name}.txt").read_text(encoding="utf-8")


def render(name: str, **values) -> str:
    """Fill {placeholders}; literal JSON braces in templates are left untouched."""
    return _VAR.sub(lambda m: str(values.get(m.group(1), m.group(0))), _load(name))
