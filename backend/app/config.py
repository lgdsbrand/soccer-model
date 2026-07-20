from pydantic_settings import BaseSettings
from functools import lru_cache


class Settings(BaseSettings):
    api_football_key: str = ""
    football_data_key: str = ""
    openweathermap_key: str = ""
    tavily_key: str = ""
    groq_api_key: str = ""
    google_genai_key: str = ""
    odds_api_key: str = ""
    app_env: str = "development"
    frontend_url: str = "http://localhost:3000"
    scraper_ingest_key: str = ""  # shared secret for the GitHub Actions team-stats scraper

    # API-Football constants
    api_football_base: str = "https://v3.football.api-sports.io"
    wc_league_id: int = 1
    wc_season: int = 2026

    # ESPN public API constants (MLS teams/fixtures/standings — no key required;
    # api_football_key's account was found suspended, see PROJECT_LOG for details)
    espn_soccer_base: str = "https://site.api.espn.com/apis/site/v2/sports/soccer"
    espn_soccer_v2_base: str = "https://site.api.espn.com/apis/v2/sports/soccer"
    mls_espn_league_slug: str = "usa.1"
    mls_season: int = 2026

    # The Odds API constants
    odds_api_base: str = "https://api.the-odds-api.com/v4"
    odds_api_sport_key: str = "soccer_usa_mls"

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
