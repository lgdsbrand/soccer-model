"""
Seed static FIFA Men's World Ranking for all 48 WC2026 teams.

Source: FIFA/Coca-Cola Men's World Ranking, official update 11 June 2026
(next official update 20 July 2026 — rankings barely move within a
tournament window, so a static snapshot is sufficient here).

Run from backend/:
    python scripts/seed_fifa_ranks.py
"""
from app.database import get_connection

FIFA_RANKS = {
    "Argentina": 1,
    "Spain": 2,
    "France": 3,
    "England": 4,
    "Portugal": 5,
    "Brazil": 6,
    "Morocco": 7,
    "Netherlands": 8,
    "Belgium": 9,
    "Germany": 10,
    "Croatia": 11,
    "Colombia": 13,
    "Mexico": 14,
    "Senegal": 15,
    "Uruguay": 16,
    "United States": 17,
    "Japan": 18,
    "Switzerland": 19,
    "Iran": 20,
    "Turkey": 22,
    "Ecuador": 23,
    "Austria": 24,
    "South Korea": 25,
    "Australia": 27,
    "Algeria": 28,
    "Egypt": 29,
    "Canada": 30,
    "Norway": 31,
    "Ivory Coast": 33,
    "Panama": 34,
    "Sweden": 38,
    "Czechia": 40,
    "Paraguay": 41,
    "Scotland": 42,
    "Tunisia": 45,
    "Congo DR": 46,
    "Uzbekistan": 50,
    "Qatar": 56,
    "Iraq": 57,
    "South Africa": 60,
    "Saudi Arabia": 61,
    "Jordan": 63,
    "Bosnia-Herzegovina": 64,
    "Cape Verde Islands": 67,
    "Ghana": 73,
    "Curaçao": 82,
    "Haiti": 83,
    "New Zealand": 85,
}


def main():
    conn = get_connection()
    cur = conn.cursor()

    updated = 0
    missing = []
    cur.execute("SELECT id, name FROM teams WHERE name != 'TBD'")
    for row in cur.fetchall():
        rank = FIFA_RANKS.get(row["name"])
        if rank is None:
            missing.append(row["name"])
            continue
        cur.execute("UPDATE teams SET fifa_rank = ? WHERE id = ?", (rank, row["id"]))
        updated += 1

    conn.commit()
    conn.close()

    print(f"Updated {updated} teams with FIFA rank.")
    if missing:
        print(f"No rank mapping found for: {missing}")


if __name__ == "__main__":
    main()
