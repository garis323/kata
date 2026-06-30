from __future__ import annotations

import os

DEFAULT_REGISTRY_URL = (
    "https://raw.githubusercontent.com/entrius/gittensor/test/"
    "gittensor/validator/weights/master_repositories.json"
)
DEFAULT_VALIDATOR_MODEL = "Qwen3-32B"


def resolve_registry_url(explicit_url: str | None = None) -> str:
    if explicit_url:
        return explicit_url
    return os.environ.get("KATA_REGISTRY_URL", DEFAULT_REGISTRY_URL)


def resolve_validator_model(explicit_model: str | None = None) -> str:
    if explicit_model:
        return explicit_model
    return os.environ.get("KATA_VALIDATOR_MODEL", DEFAULT_VALIDATOR_MODEL)


def resolve_validator_api_base() -> str:
    return os.environ.get("KATA_VALIDATOR_API_BASE", "")


def resolve_validator_api_key() -> str:
    return os.environ.get("KATA_VALIDATOR_API_KEY", "")
