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
    "soccer": ["soccer_uefa_champs_league", "soccer_epl", "soccer_uefa_nations_league", "soccer_usa_mls"]
}

NAME_BUZZ = {
    "djokovic": 96, "alcaraz": 96, "sinner": 95, "medvedev": 90, 
    "zverev": 89, "tsitsipas": 85, "rublev": 84, "rune": 84, "fritz": 86,
    "de minaur": 85, "ruud": 85, "paul": 82, "tiafoe": 83, "shelton": 84,
    "swiatek": 95, "sabalenka": 94, "gauff": 94, "rybakina": 90, "paolini": 86, "zheng": 88,
    "real madrid": 96, "barcelona": 95, "arsenal": 90, "bayern": 92,
    "manchester city": 94, "liverpool": 93, "chelsea": 88, "inter": 88,
    "chiefs": 95, "bills": 90, "cowboys": 88, "patriots": 85, "packers": 87, "lions": 86,
    "celtics": 92, "lakers": 94, "warriors": 91, "heat": 85, "knicks": 87, "cavaliers": 85,
    "maple leafs": 89, "rangers": 88, "oilers": 87, "blackhawks": 86, "flyers": 82
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

                home_team = event.get("home_team")
                away_team = event.get("away_team")
                if not home_team or not away_team:
                    continue

                home_buzz = get_buzz(home_team)
                away_buzz = get_buzz(away_team)
                gap = abs(home_buzz - away_buzz)

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

                away_price = None
                home_price = None
                for out in h2h_outcomes:
                    out_name = out.get("name", "")
                    if out_name == away_team:
                        away_price = out.get("price")
                    elif out_name == home_team:
                        home_price = out.get("price")

                if not away_price or not home_price:
                    away_price = h2h_outcomes[0].get("price")
                    home_price = h2h_outcomes[1].get("price")

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

    # Query active sports catalogue dynamically
    tennis_keys = []
    soccer_keys = []
    sports_url = f"https://api.the-odds-api.com/v4/sports?apiKey={API_KEY}"
    try:
        res = requests.get(sports_url, timeout=12)
        if res.status_code == 200:
            for s in res.json():
                if s.get("active") and not s.get("has_outrights"):
                    k = s.get("key", "")
                    if k.startswith("tennis_"):
                        tennis_keys.append(k)
                    elif k.startswith("soccer_"):
                        soccer_keys.append(k)
    except Exception as e:
        print(f"Error fetching active sports: {e}")

    # Fallback to known circuits if dynamic discovery is quiet
    if not tennis_keys:
        tennis_keys = [
            "tennis_atp_challenger", 
            "tennis_atp_finals", 
            "tennis_wta_finals", 
            "tennis_atp_aus_open", 
            "tennis_wta_aus_open"
        ]

    active_sport_groups = {
        "tennis": tennis_keys,
        "football": DEFAULT_GROUPS["football"],
        "basketball": DEFAULT_GROUPS["basketball"],
        "hockey": DEFAULT_GROUPS["hockey"],
        "soccer": soccer_keys if soccer_keys else DEFAULT_GROUPS["soccer"]
    }

    for group, keys in active_sport_groups.items():
        # Fetch up to 4 matches per sport
        group_items = fetch_group_matches(group, keys, limit=4)
        all_data.extend(group_items)

    all_data.sort(key=lambda x: x["gameDate"])
    return all_data

if __name__ == "__main__":
    data = fetch_odds()
    with open("odds_data.json", "w") as f:
        json.dump(data, f, indent=2)
    print(f"Successfully generated odds_data.json with {len(data)} events.")
    
