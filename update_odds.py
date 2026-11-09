import os
import requests
import json
from datetime import datetime, timezone

API_KEY = os.environ.get("ODDS_API_KEY")
REGIONS = "us,eu"
MARKETS = "h2h"
ODDS_FORMAT = "decimal"

DEFAULT_GROUPS = {
    "football": ["americanfootball_nfl", "americanfootball_ncaaf"],
    "basketball": ["basketball_nba"],
    "hockey": ["icehockey_nhl"],
    "soccer": ["soccer_uefa_champs_league", "soccer_epl", "soccer_uefa_nations_league"]
}

NAME_BUZZ = {
    "gauff": 94, "pegula": 90, "kostyuk": 82, "noskova": 80,
    "mertens": 84, "zhang": 83, "dabrowski": 85, "stefani": 84,
    "hsieh": 86, "ostapenko": 88, "siniakova": 87, "townsend": 86,
    "errani": 84, "paolini": 88, "swiatek": 96, "sabalenka": 95,
    "sinner": 96, "alcaraz": 96, "djokovic": 95, "zverev": 90, "medvedev": 90,
    "mannarino": 82, "michelsen": 81, "sonego": 82, "halys": 80, "cerundolo": 81,
    "real madrid": 96, "barcelona": 95, "arsenal": 90, "bayern": 92,
    "chiefs": 95, "bills": 90, "cowboys": 88, "celtics": 92, "lakers": 94,
    "rangers": 88, "oilers": 87
}

def get_buzz(name):
    if not name:
        return 75
    name_lower = name.lower()
    for key, val in NAME_BUZZ.items():
        if key in name_lower:
            return val
    return 75

def is_within_7_days(date_str):
    try:
        game_dt = datetime.fromisoformat(date_str.replace("Z", "+00:00"))
        now = datetime.now(timezone.utc)
        delta = game_dt - now
        return -0.2 <= (delta.total_seconds() / 86400.0) <= 7.0
    except Exception:
        return False

def to_american_odds(decimal_odds):
    if not decimal_odds or decimal_odds <= 1.0:
        return "-110"
    if decimal_odds >= 2.0:
        ml = int(round((decimal_odds - 1.0) * 100))
        return f"+{ml}"
    else:
        ml = int(round(-100 / (decimal_odds - 1.0)))
        return f"{ml}"

def fetch_group_matches(group_label, sport_keys, limit=4):
    matches = []
    for sport in sport_keys:
        if len(matches) >= limit:
            break
        url = f"https://api.the-odds-api.com/v4/sports/{sport}/odds/?apiKey={API_KEY}&regions={REGIONS}&markets={MARKETS}&oddsFormat={ODDS_FORMAT}"
        try:
            res = requests.get(url, timeout=12)
            if res.status_code != 200:
                continue
            events = res.json()
            if not isinstance(events, list):
                continue

            for event in events:
                if len(matches) >= limit:
                    break
                commence_time = event.get("commence_time")
                if not commence_time or not is_within_7_days(commence_time):
                    continue

                home_team = event.get("home_team", "")
                away_team = event.get("away_team", "")

                bookmakers = event.get("bookmakers", [])
                if not bookmakers:
                    continue

                h2h_outcomes = []
                for bm in bookmakers:
                    for market in bm.get("markets", []):
                        if market.get("key") == "h2h":
                            h2h_outcomes = market.get("outcomes", [])
                            break
                    if len(h2h_outcomes) >= 2:
                        break

                if len(h2h_outcomes) < 2:
                    continue

                # Ensure player/team names exist
                if not away_team or not home_team:
                    away_team = h2h_outcomes[0].get("name", "Player 1")
                    home_team = h2h_outcomes[1].get("name", "Player 2")

                away_price = None
                home_price = None
                for out in h2h_outcomes:
                    out_name = out.get("name", "")
                    if out_name == away_team:
                        away_price = out.get("price")
                    elif out_name == home_team:
                        home_price = out.get("price")

                if not away_price or not home_price:
                    away_price = h2h_outcomes[0].get("price", 1.91)
                    home_price = h2h_outcomes[1].get("price", 1.91)
                    away_team = h2h_outcomes[0].get("name", away_team)
                    home_team = h2h_outcomes[1].get("name", home_team)

                home_buzz = get_buzz(home_team)
                away_buzz = get_buzz(away_team)
                gap = abs(home_buzz - away_buzz)

                away_ml = to_american_odds(away_price)
                home_ml = to_american_odds(home_price)

                if away_price < home_price:
                    fav_team = away_team
                    lead_ml_val = int(away_ml)
                else:
                    fav_team = home_team
                    lead_ml_val = int(home_ml)

                matches.append({
                    "sport": group_label,
                    "gameDate": commence_time,
                    "awayTeam": away_team,
                    "homeTeam": home_team,
                    "awayOdds": away_ml,
                    "homeOdds": home_ml,
                    "favTeam": fav_team,
                    "leadML": lead_ml_val,
                    "gap": max(gap, 14)
                })
        except Exception:
            continue
    return matches

def fetch_odds():
    all_data = []
    if not API_KEY:
        print("Error: ODDS_API_KEY secret is missing.")
        return all_data

    # Step 1: Discover all active tennis and soccer sports
    discovered_tennis = []
    discovered_soccer = []
    sports_url = f"https://api.the-odds-api.com/v4/sports?apiKey={API_KEY}"
    try:
        res = requests.get(sports_url, timeout=12)
        if res.status_code == 200:
            for s in res.json():
                if s.get("active"):
                    k = s.get("key", "")
                    if k.startswith("tennis_"):
                        discovered_tennis.append(k)
                    elif k.startswith("soccer_"):
                        discovered_soccer.append(k)
    except Exception as e:
        print(f"Discovery error: {e}")

    # Fallback to current tournament keys
    known_tennis = [
        "tennis_wta_finals",
        "tennis_atp_finals",
        "tennis_atp_stockholm",
        "tennis_atp_challenger",
        "tennis_atp_metz",
        "tennis_atp_belgrade"
    ]
    for k in known_tennis:
        if k not in discovered_tennis:
            discovered_tennis.append(k)

    active_sport_groups = {
        "tennis": discovered_tennis,
        "football": DEFAULT_GROUPS["football"],
        "basketball": DEFAULT_GROUPS["basketball"],
        "hockey": DEFAULT_GROUPS["hockey"],
        "soccer": discovered_soccer if discovered_soccer else DEFAULT_GROUPS["soccer"]
    }

    # Fetch 4 matches per sport, 5 for tennis
    for group, keys in active_sport_groups.items():
        limit = 5 if group == "tennis" else 4
        group_items = fetch_group_matches(group, keys, limit=limit)
        all_data.extend(group_items)

    all_data.sort(key=lambda x: x["gameDate"])
    return all_data

if __name__ == "__main__":
    data = fetch_odds()
    with open("odds_data.json", "w") as f:
        json.dump(data, f, indent=2)
    print(f"Successfully generated odds_data.json with {len(data)} events.")
    
