import os
from dataclasses import dataclass


@dataclass(frozen=True)
class AppConfig:
    OPENAI_API_KEY: str
    GRID_API_KEY: str
    GRID_API_URL: str | None = None


def get_config() -> AppConfig:
    try:
        return AppConfig(
            OPENAI_API_KEY=os.environ["OPENAI_API_KEY"],
            GRID_API_KEY=os.environ["GRID_API_KEY"],
            GRID_API_URL=os.environ.get("GRID_API_URL"),
        )
    except KeyError as e:
        raise KeyError(f"Missing environment variable: {e}") from e
