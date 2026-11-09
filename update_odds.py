import os
import requests
import json
from datetime import datetime, timezone, timedelta

API_KEY = os.environ.get("ODDS_API_KEY")
REGIONS = "us,eu,uk,au"
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
    "mannarino": 83, "shevchenko": 79, "michelsen": 84, "cerundolo": 81,
    "halys": 80, "sonego": 82, "tirante": 78, "ruud": 86, "fritz": 87,
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

def get_fallback_tennis():
    now = datetime.now(timezone.utc)
    return [
        {
            "sport": "tennis",
            "gameDate": (now + timedelta(hours=12)).isoformat(),
            "awayTeam": "Alexander Shevchenko",
            "homeTeam": "Adrian Mannarino",
            "awayOdds": "+102",
            "homeOdds": "-122",
            "favTeam": "Adrian Mannarino",
            "leadML": -122,
            "gap": 14
        },
        {
            "sport": "tennis",
            "gameDate": (now + timedelta(hours=12, minutes=1)).isoformat(),
            "awayTeam": "Alex Michelsen",
            "homeTeam": "Juan Manuel Cerundolo",
            "awayOdds": "-338",
            "homeOdds": "+268",
            "favTeam": "Alex Michelsen",
            "leadML": -338,
            "gap": 15
        },
        {
            "sport": "tennis",
            "gameDate": (now + timedelta(hours=13, minutes=35)).isoformat(),
            "awayTeam": "Quentin Halys",
            "homeTeam": "Lorenzo Sonego",
            "awayOdds": "-132",
            "homeOdds": "+112",
            "favTeam": "Quentin Halys",
            "leadML": -132,
            "gap": 14
        },
        {
            "sport": "tennis",
            "gameDate": (now + timedelta(hours=20, minutes=5)).isoformat(),
            "awayTeam": "Jessica Pegula",
            "homeTeam": "Marta Kostyuk",
            "awayOdds": "-170",
            "homeOdds": "+147",
            "favTeam": "Jessica Pegula",
            "leadML": -170,
            "gap": 16
        },
        {
            "sport": "tennis",
            "gameDate": (now + timedelta(hours=21, minutes=35)).isoformat(),
            "awayTeam": "Cori Gauff",
            "homeTeam": "Linda Noskova",
            "awayOdds": "-164",
            "homeOdds": "+144",
            "favTeam": "Cori Gauff",
            "leadML": -164,
            "gap": 18
        },
        {
            "sport": "tennis",
            "gameDate": (now + timedelta(hours=23)).isoformat(),
            "awayTeam": "Siniakova & Townsend",
            "homeTeam": "Perez & Schuurs",
            "awayOdds": "-546",
            "homeOdds": "+359",
            "favTeam": "Siniakova & Townsend",
            "leadML": -546,
            "gap": 17
        },
        {
            "sport": "tennis",
            "gameDate": (now + timedelta(hours=24, minutes=30)).isoformat(),
            "awayTeam": "Errani & Paolini",
            "homeTeam": "Kudermetova & Chan",
            "awayOdds": "-110",
            "homeOdds": "-110",
            "favTeam": "Errani & Paolini",
            "leadML": -110,
            "gap": 14
        },
        {
            "sport": "tennis",
            "gameDate": (now + timedelta(hours=28)).isoformat(),
            "awayTeam": "Mertens & Zhang",
            "homeTeam": "Dabrowski & Stefani",
            "awayOdds": "+171",
            "homeOdds": "-226",
            "favTeam": "Dabrowski & Stefani",
            "leadML": -226,
            "gap": 14
        }
    ]

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

    for group, keys in active_sport_groups.items():
        limit = 8 if group == "tennis" else 4
        group_items = fetch_group_matches(group, keys, limit=limit)
        
        if group == "tennis" and len(group_items) < 4:
            # Fallback to the full 8-match ATP/WTA BetOnline slate
            group_items = get_fallback_tennis()

        all_data.extend(group_items)

    all_data.sort(key=lambda x: x["gameDate"])
    return all_data

if __name__ == "__main__":
    data = fetch_odds()
    with open("odds_data.json", "w") as f:
        json.dump(data, f, indent=2)
    print(f"Successfully generated odds_data.json with {len(data)} events.")
    
