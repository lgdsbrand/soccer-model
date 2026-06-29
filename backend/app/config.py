from pydantic_settings import BaseSettings
from functools import lru_cache


class Settings(BaseSettings):
    api_football_key: str = ""
    football_data_key: str = ""
    openweathermap_key: str = ""
    tavily_key: str = ""
    groq_api_key: str = ""
    google_genai_key: str = ""
    app_env: str = "development"
    frontend_url: str = "http://localhost:3000"

    # API-Football constants
    api_football_base: str = "https://v3.football.api-sports.io"
    wc_league_id: int = 1
    wc_season: int = 2026

    # Model settings
    dc_time_decay: float = 0.0065  # Dixon-Coles time decay lambda
    mc_simulations: int = 10000    # Monte Carlo simulation count

    # Cache TTLs (seconds)
    cache_fixtures_ttl: int = 3600        # 1 hour
    cache_standings_ttl: int = 3600
    cache_last5_ttl: int = 86400          # 24 hours
    cache_match_stats_ttl: int = 86400
    cache_lineups_ttl: int = 1800         # 30 min (match day)
    cache_llm_ttl: int = 86400
    cache_weather_ttl: int = 3600

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8"}


@lru_cache()
def get_settings() -> Settings:
    return Settings()
