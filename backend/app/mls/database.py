"""
MLS-specific schema — fully separate tables from the World Cup schema
(app/database.py), sharing only the same SQLite file/connection.

Kept isolated on purpose: WC's teams.id/fixtures.id are external
API-native integers with no namespace, and WC's team_model_params/
model_globals/predictions/advancement_probs are unscoped singleton
tables (a refit does `DELETE FROM team_model_params` unconditionally).
Sharing any of those with a second competition risks ID collisions or
one league's refresh silently corrupting the other's data.
"""
from app.database import get_connection


def init_mls_db():
    conn = get_connection()
    cur = conn.cursor()

    cur.executescript("""
        CREATE TABLE IF NOT EXISTS mls_teams (
            id INTEGER PRIMARY KEY,
            name TEXT NOT NULL,
            short_name TEXT,
            abbreviation TEXT,
            logo TEXT,
            conference TEXT,
            venue_city TEXT,
            updated_at REAL DEFAULT (unixepoch())
        );

        CREATE TABLE IF NOT EXISTS mls_fixtures (
            id INTEGER PRIMARY KEY,
            season INTEGER,
            date_utc REAL,
            status TEXT,
            home_team_id INTEGER,
            away_team_id INTEGER,
            home_score INTEGER,
            away_score INTEGER,
            venue_name TEXT,
            venue_city TEXT,
            FOREIGN KEY (home_team_id) REFERENCES mls_teams(id),
            FOREIGN KEY (away_team_id) REFERENCES mls_teams(id)
        );

        CREATE TABLE IF NOT EXISTS mls_standings (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            team_id INTEGER NOT NULL,
            conference TEXT,
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
            FOREIGN KEY (team_id) REFERENCES mls_teams(id)
        );

        CREATE TABLE IF NOT EXISTS mls_match_probs (
            fixture_id INTEGER PRIMARY KEY,
            home_win_pct REAL,
            draw_pct REAL,
            away_win_pct REAL,
            btts_pct REAL,
            over_1_5_pct REAL,
            over_3_5_pct REAL,
            over_2_5_pct REAL,
            bookmaker_count INTEGER,
            computed_at REAL DEFAULT (unixepoch()),
            FOREIGN KEY (fixture_id) REFERENCES mls_fixtures(id)
        );

        CREATE TABLE IF NOT EXISTS mls_lineups (
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
            FOREIGN KEY (fixture_id) REFERENCES mls_fixtures(id),
            FOREIGN KEY (team_id) REFERENCES mls_teams(id)
        );

        CREATE TABLE IF NOT EXISTS mls_match_stats (
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
            FOREIGN KEY (fixture_id) REFERENCES mls_fixtures(id),
            FOREIGN KEY (team_id) REFERENCES mls_teams(id)
        );

        CREATE TABLE IF NOT EXISTS mls_team_season_stats (
            team_name TEXT PRIMARY KEY,
            corners INTEGER,
            shots INTEGER,
            fouls INTEGER,
            source TEXT DEFAULT 'fotmob.com',
            updated_at REAL DEFAULT (unixepoch())
        );

        CREATE TABLE IF NOT EXISTS mls_power_ratings (
            team_name TEXT PRIMARY KEY,
            rank INTEGER,
            source TEXT DEFAULT 'sonnymoorepowerratings.com',
            updated_at REAL DEFAULT (unixepoch())
        );

        CREATE INDEX IF NOT EXISTS idx_mls_fixtures_date ON mls_fixtures(date_utc);
        CREATE INDEX IF NOT EXISTS idx_mls_fixtures_teams ON mls_fixtures(home_team_id, away_team_id);
    """)

    # Migration: add over_1_5_pct column to mls_match_probs (added once the
    # alternate_totals market — not just the bulk totals market — was wired
    # up as an odds source; see app/mls/services/odds_api.py)
    try:
        cur.execute("ALTER TABLE mls_match_probs ADD COLUMN over_1_5_pct REAL")
        conn.commit()
    except Exception:
        pass  # column already exists

    conn.commit()
    conn.close()
