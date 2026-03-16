from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml
from pydantic import BaseModel, Field, field_validator


class RetryConfig(BaseModel):
    max_attempts: int = Field(default=3, ge=1, le=10)
    delay_seconds: list[float] = Field(default_factory=lambda: [1.0, 2.0, 5.0])


class LLMConfig(BaseModel):
    provider: str = "koboldcpp"
    url: str = "http://localhost:5001"
    model: str = "Llama-4-Scout-17B-16E-Instruct-IQ2_XXS.gguf"

    n_gpu_layers: int = 32
    n_cpu_moe: int = 16
    flash_attention: bool = True
    kv_cache_quant: str = "q4_1"

    max_context_tokens: int = Field(default=16384, ge=512, le=131072)
    max_response_tokens: int = Field(default=512, ge=64, le=4096)

    temperature: float = Field(default=0.7, ge=0.0, le=2.0)
    top_p: float = Field(default=0.9, ge=0.0, le=1.0)
    top_k: int = Field(default=40, ge=0)

    retry: RetryConfig = Field(default_factory=RetryConfig)

    @field_validator("provider")
    @classmethod
    def validate_provider(cls, v: str) -> str:
        allowed = {"koboldcpp", "lmstudio", "ollama", "openai"}
        if v not in allowed:
            raise ValueError(f"Unsupported provider: {v}. Allowed: {allowed}")
        return v

    @field_validator("url")
    @classmethod
    def validate_url(cls, v: str) -> str:
        if not v.startswith(("http://", "https://")):
            raise ValueError("URL must start with http:// or https://")
        return v


class LoreConfig(BaseModel):
    directory: str = "./lore"
    cache_embeddings: bool = True
    embedding_model: str = "all-MiniLM-L6-v2"


class MemoryConfig(BaseModel):
    max_context_tokens: int = Field(default=12288, ge=512)
    summary_threshold: int = Field(default=50, ge=10)
    summary_every: int = Field(default=30, ge=5)
    summary_max_tokens: int = Field(default=500, ge=50)
    summary_model: str | None = None
    max_key_facts: int = Field(default=50, ge=1)
    embedding_cache_ttl: int = Field(default=3600, ge=60)
    embedding_cache_maxsize: int = Field(default=1000, ge=10)


class DiceConfig(BaseModel):
    seed: int | None = None
    log_rolls: bool = True


class InventoryConfig(BaseModel):
    max_slots: int = Field(default=100, ge=1)
    max_weight: float = Field(default=100.0, ge=0.0)


class CharacterConfig(BaseModel):
    max_level: int = Field(default=20, ge=1)
    hp_per_level: int = Field(default=10, ge=1)
    mana_per_level: int = Field(default=5, ge=0)


class CombatConfig(BaseModel):
    max_rounds: int = Field(default=50, ge=1)
    actions_per_turn: int = Field(default=1, ge=1, le=5)
    base_damage_dice: str = "1d6"
    spell_damage_dice: str = "1d8"
    critical_multiplier: float = Field(default=2.0, ge=1.0)
    minimum_damage: int = Field(default=1, ge=0)
    flee_dc: int = Field(default=12, ge=1)


class GameConfig(BaseModel):
    dice: DiceConfig = Field(default_factory=DiceConfig)
    inventory: InventoryConfig = Field(default_factory=InventoryConfig)
    character: CharacterConfig = Field(default_factory=CharacterConfig)
    combat: CombatConfig = Field(default_factory=CombatConfig)


class BackupConfig(BaseModel):
    enabled: bool = True
    interval_hours: int = Field(default=6, ge=1)
    max_backups: int = Field(default=10, ge=1)


class PersistenceConfig(BaseModel):
    database: str = "data/game.db"
    saves_directory: str = "data/saves"
    logs_directory: str = "data/logs"
    backup: BackupConfig = Field(default_factory=BackupConfig)


class RotationConfig(BaseModel):
    max_size_mb: int = Field(default=100, ge=1)
    backup_count: int = Field(default=5, ge=1)


class LoggingConfig(BaseModel):
    level: str = "INFO"
    format: str = "json"
    file: str = "data/logs/app.log"
    rotation: RotationConfig = Field(default_factory=RotationConfig)


class RateLimitConfig(BaseModel):
    requests_per_minute: int = Field(default=60, ge=1)


class APIConfig(BaseModel):
    host: str = "127.0.0.1"
    port: int = Field(default=8000, ge=1, le=65535)
    cors_origins: list[str] = Field(default_factory=lambda: ["http://localhost:8000"])
    rate_limit: RateLimitConfig = Field(default_factory=RateLimitConfig)


class AppConfig(BaseModel):
    name: str = "mon-rpg-ia"
    version: str = "0.1.0"
    debug: bool = False


class Config(BaseModel):
    app: AppConfig = Field(default_factory=AppConfig)
    llm: LLMConfig = Field(default_factory=LLMConfig)
    lore: LoreConfig = Field(default_factory=LoreConfig)
    memory: MemoryConfig = Field(default_factory=MemoryConfig)
    game: GameConfig = Field(default_factory=GameConfig)
    persistence: PersistenceConfig = Field(default_factory=PersistenceConfig)
    logging: LoggingConfig = Field(default_factory=LoggingConfig)
    api: APIConfig = Field(default_factory=APIConfig)


def load_config(path: str | Path = "config/default.yaml") -> Config:
    config_path = Path(path)
    if not config_path.exists():
        return Config()

    with open(config_path, encoding="utf-8") as f:
        raw: dict[str, Any] = yaml.safe_load(f) or {}

    return Config.model_validate(raw)
