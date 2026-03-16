import pytest

from src.core.config import Config, LLMConfig, load_config


class TestConfig:
    def test_default_config(self) -> None:
        config = Config()
        assert config.app.name == "mon-rpg-ia"
        assert config.llm.provider == "koboldcpp"
        assert config.llm.temperature == 0.7
        assert config.game.dice.log_rolls is True

    def test_load_from_yaml(self) -> None:
        config = load_config("config/default.yaml")
        assert config.app.name == "mon-rpg-ia"
        assert config.llm.url == "http://localhost:5001"
        assert config.game.inventory.max_slots == 100

    def test_load_missing_file_returns_default(self) -> None:
        config = load_config("nonexistent.yaml")
        assert config.app.name == "mon-rpg-ia"

    def test_llm_provider_validation(self) -> None:
        with pytest.raises(ValueError):
            LLMConfig(provider="invalid_provider")  # type: ignore[call-arg]

    def test_llm_url_validation(self) -> None:
        with pytest.raises(ValueError):
            LLMConfig(url="ftp://invalid")  # type: ignore[call-arg]

    def test_temperature_bounds(self) -> None:
        config = LLMConfig(temperature=0.0)
        assert config.temperature == 0.0

        config = LLMConfig(temperature=2.0)
        assert config.temperature == 2.0

        with pytest.raises(ValueError):
            LLMConfig(temperature=3.0)  # type: ignore[call-arg]
