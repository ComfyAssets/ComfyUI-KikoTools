"""API tokens for the downloaders, read on the server so shared workflows never carry them."""

import os
from pathlib import Path
from typing import Optional

# Environment variables checked per provider, first match wins.
ENV_VARS = {
    "civitai": ("CIVITAI_API_KEY", "CIVITAI_API_TOKEN", "CIVITAI_TOKEN"),
    "huggingface": ("HF_TOKEN", "HUGGING_FACE_HUB_TOKEN"),
}


def _huggingface_login_token() -> Optional[str]:
    """The token `hf auth login` saved, if any."""
    path = os.environ.get("HF_TOKEN_PATH")
    if not path:
        home = os.environ.get("HF_HOME") or os.path.join(
            Path.home(), ".cache", "huggingface"
        )
        path = os.path.join(home, "token")
    try:
        return Path(path).read_text(encoding="utf-8").strip() or None
    except OSError:
        return None


def resolve_token(provider: str, override: Optional[str] = None) -> Optional[str]:
    """Token for provider: a token typed on the node, else the server's own.

    Only Civitai and Hugging Face get server tokens, each its own, so a token
    is never sent to another host.
    """
    if override and override.strip():
        return override.strip()
    for name in ENV_VARS.get(provider, ()):
        value = os.environ.get(name, "").strip()
        if value:
            return value
    if provider == "huggingface":
        return _huggingface_login_token()
    return None
