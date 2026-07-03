import csv
import json
from pathlib import Path

INPUT_FILE = Path("data/nba/games_with_elo.csv")
OUTPUT_FILE = Path("data/nba/teams.json")


def main():
    teams = {}

    with INPUT_FILE.open("r", encoding="utf-8", newline="") as f:
        reader = csv.DictReader(f)

        for row in reader:
            season = int(row["season"])

            for side in ["home", "visitor"]:
                team_id = row[f"{side}_team_id"]
                team_name = row[f"{side}_team_name"]

                if team_id not in teams:
                    teams[team_id] = {
                        "team_id": team_id,
                        "team_name": team_name,
                        "first_season": season,
                        "last_season": season
                    }

                teams[team_id]["first_season"] = min(
                    teams[team_id]["first_season"],
                    season
                )

                teams[team_id]["last_season"] = max(
                    teams[team_id]["last_season"],
                    season
                )

                teams[team_id]["team_name"] = team_name

    latest_season = max(team["last_season"] for team in teams.values())

    output = []

    for team in teams.values():
        team["active"] = team["last_season"] == latest_season
        output.append(team)

    output.sort(key=lambda x: (not x["active"], x["team_name"]))

    OUTPUT_FILE.parent.mkdir(parents=True, exist_ok=True)

    with OUTPUT_FILE.open("w", encoding="utf-8") as f:
        json.dump(output, f, indent=2, ensure_ascii=False)

    print(f"Generated {OUTPUT_FILE}")
    print(f"Teams: {len(output)}")
    print(f"Latest season: {latest_season}")


if __name__ == "__main__":
    main()
