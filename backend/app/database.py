import sqlite3
import os
from pathlib import Path

DB_PATH = Path(__file__).parent.parent / "wc2026.db"


def get_connection() -> sqlite3.Connection:
    conn = sqlite3.connect(str(DB_PATH), check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    return conn


def init_db():
    conn = get_connection()
    cur = conn.cursor()

    cur.executescript("""
        CREATE TABLE IF NOT EXISTS teams (
            id INTEGER PRIMARY KEY,
            name TEXT NOT NULL,
            code TEXT,
            country TEXT,
            logo TEXT,
            group_letter TEXT,
            coach TEXT,
            formation_default TEXT,
            style_of_play TEXT,
            updated_at REAL DEFAULT (unixepoch())
        );

        CREATE TABLE IF NOT EXISTS players (
            id INTEGER PRIMARY KEY,
            name TEXT NOT NULL,
            age INTEGER,
            nationality TEXT,
            team_id INTEGER,
            position TEXT,
            number INTEGER,
            photo TEXT,
            club TEXT,
            club_logo TEXT,
            is_key_player INTEGER DEFAULT 0,
            goals_intl INTEGER DEFAULT 0,
            assists_intl INTEGER DEFAULT 0,
            FOREIGN KEY (team_id) REFERENCES teams(id)
        );

        CREATE TABLE IF NOT EXISTS fixtures (
            id INTEGER PRIMARY KEY,
            league_id INTEGER,
            season INTEGER,
            round TEXT,
            date_utc REAL,
            status TEXT,
            home_team_id INTEGER,
            away_team_id INTEGER,
            home_score INTEGER,
            away_score INTEGER,
            home_score_ht INTEGER,
            away_score_ht INTEGER,
            venue_name TEXT,
            venue_city TEXT,
            venue_lat REAL,
            venue_lon REAL,
            FOREIGN KEY (home_team_id) REFERENCES teams(id),
            FOREIGN KEY (away_team_id) REFERENCES teams(id)
        );

        CREATE TABLE IF NOT EXISTS standings (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            team_id INTEGER NOT NULL,
            group_letter TEXT,
            rank INTEGER,
            points INTEGER DEFAULT 0,
            played INTEGER DEFAULT 0,
            won INTEGER DEFAULT 0,
            drawn INTEGER DEFAULT 0,
            lost INTEGER DEFAULT 0,
            goals_for INTEGER DEFAULT 0,
            goals_against INTEGER DEFAULT 0,
            goal_diff INTEGER DEFAULT 0,
            form TEXT,
            updated_at REAL DEFAULT (unixepoch()),
            UNIQUE(team_id),
            FOREIGN KEY (team_id) REFERENCES teams(id)
        );

        CREATE TABLE IF NOT EXISTS match_stats (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            fixture_id INTEGER NOT NULL,
            team_id INTEGER NOT NULL,
            shots_total INTEGER,
            shots_on_target INTEGER,
            corners INTEGER,
            fouls INTEGER,
            yellow_cards INTEGER,
            red_cards INTEGER,
            possession TEXT,
            passes_total INTEGER,
            passes_accuracy TEXT,
            offsides INTEGER,
            UNIQUE(fixture_id, team_id),
            FOREIGN KEY (fixture_id) REFERENCES fixtures(id),
            FOREIGN KEY (team_id) REFERENCES teams(id)
        );

        CREATE TABLE IF NOT EXISTS lineups (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            fixture_id INTEGER NOT NULL,
            team_id INTEGER NOT NULL,
            formation TEXT,
            player_id INTEGER,
            player_name TEXT,
            player_number INTEGER,
            player_pos TEXT,
            player_grid TEXT,
            is_substitute INTEGER DEFAULT 0,
            is_predicted INTEGER DEFAULT 0,
            FOREIGN KEY (fixture_id) REFERENCES fixtures(id),
            FOREIGN KEY (team_id) REFERENCES teams(id)
        );

        CREATE TABLE IF NOT EXISTS historical_results (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            match_date TEXT,
            home_team TEXT NOT NULL,
            away_team TEXT NOT NULL,
            home_goals INTEGER NOT NULL,
            away_goals INTEGER NOT NULL,
            tournament TEXT,
            neutral INTEGER DEFAULT 0,
            days_ago REAL,
            weight REAL DEFAULT 1.0,
            UNIQUE(match_date, home_team, away_team)
        );

        CREATE TABLE IF NOT EXISTS team_model_params (
            team_name TEXT PRIMARY KEY,
            attack REAL,
            defense REAL,
            fitted_at REAL DEFAULT (unixepoch())
        );

        CREATE TABLE IF NOT EXISTS model_globals (
            key TEXT PRIMARY KEY,
            value REAL NOT NULL,
            fitted_at REAL DEFAULT (unixepoch())
        );

        CREATE TABLE IF NOT EXISTS predictions (
            fixture_id INTEGER PRIMARY KEY,
            home_win_pct REAL,
            draw_pct REAL,
            away_win_pct REAL,
            btts_pct REAL,
            over_1_5_pct REAL,
            over_2_5_pct REAL,
            expected_home_goals REAL,
            expected_away_goals REAL,
            home_attack REAL,
            home_defense REAL,
            away_attack REAL,
            away_defense REAL,
            computed_at REAL DEFAULT (unixepoch()),
            FOREIGN KEY (fixture_id) REFERENCES fixtures(id)
        );

        CREATE TABLE IF NOT EXISTS advancement_probs (
            team_id INTEGER PRIMARY KEY,
            r32_pct REAL DEFAULT 0,
            r16_pct REAL DEFAULT 0,
            qf_pct REAL DEFAULT 0,
            sf_pct REAL DEFAULT 0,
            final_pct REAL DEFAULT 0,
            winner_pct REAL DEFAULT 0,
            computed_at REAL DEFAULT (unixepoch()),
            FOREIGN KEY (team_id) REFERENCES teams(id)
        );

        CREATE TABLE IF NOT EXISTS llm_cache (
            cache_key TEXT PRIMARY KEY,
            content TEXT NOT NULL,
            generated_at REAL DEFAULT (unixepoch())
        );

        CREATE TABLE IF NOT EXISTS weather_cache (
            venue_key TEXT PRIMARY KEY,
            data TEXT NOT NULL,
            fetched_at REAL DEFAULT (unixepoch())
        );

        CREATE TABLE IF NOT EXISTS tavily_match_probs (
            home_team TEXT NOT NULL,
            away_team TEXT NOT NULL,
            home_win_pct REAL NOT NULL,
            draw_pct REAL NOT NULL,
            away_win_pct REAL NOT NULL,
            expected_home_goals REAL,
            expected_away_goals REAL,
            fetched_at REAL NOT NULL,
            PRIMARY KEY (home_team, away_team)
        );

        CREATE INDEX IF NOT EXISTS idx_fixtures_date ON fixtures(date_utc);
        CREATE INDEX IF NOT EXISTS idx_fixtures_teams ON fixtures(home_team_id, away_team_id);
        CREATE INDEX IF NOT EXISTS idx_historical_teams ON historical_results(home_team, away_team);
    """)

    # Migration: add api_football_id column if not present
    try:
        conn.execute("ALTER TABLE fixtures ADD COLUMN api_football_id INTEGER")
        conn.commit()
    except Exception:
        pass

    # Migration: add Tavily odds columns to advancement_probs
    for col in ("tavily_winner_pct", "tavily_final_pct", "tavily_sf_pct"):
        try:
            conn.execute(f"ALTER TABLE advancement_probs ADD COLUMN {col} REAL")
            conn.commit()
        except Exception:
            pass  # column already exists

    conn.commit()
    conn.close()
