from pathlib import Path
import json
import pandas as pd
import numpy as np

ROOT = Path(__file__).resolve().parents[1]
INPUT = ROOT / "data" / "nba_games.csv"
OUT_DIR = ROOT / "public" / "data" / "nba"

K_FACTOR = 20
HOME_ADV = 90
REGRESSION = 1 / 3
MOV_C = 0.10


def build_nba_elo():
    OUT_DIR.mkdir(parents=True, exist_ok=True)

    df = pd.read_csv(INPUT)

    df["date"] = pd.to_datetime(df[["year", "month", "day"]])
    df = df.sort_values(["date", "game_id"]).reset_index(drop=True)

    gap = df["date"].diff().dt.days
    df["season"] = (gap > 60).cumsum()
    df.loc[df["season"] == 74, "season"] = 73  # COVID popravak

    ratings = {}
    new_columns = []
    prev_season = None

    for row in df.itertuples():
        if prev_season is not None and row.season != prev_season:
            for t in ratings:
                ratings[t] = ratings[t] + REGRESSION * (1500 - ratings[t])
        prev_season = row.season

        h, v = row.home_team_id, row.visitor_team_id
        ratings.setdefault(h, 1500.0)
        ratings.setdefault(v, 1500.0)

        elo_h_before = ratings[h]
        elo_v_before = ratings[v]

        difference = (elo_h_before + HOME_ADV) - elo_v_before
        expected = 1 / (1 + 10 ** (-difference / 400))

        outcome = 1.0 if row.home_pts > row.visitor_pts else 0.0

        mov = abs(row.home_pts - row.visitor_pts)
        mov_factor = 1 + MOV_C * np.log1p(mov)

        delta = K_FACTOR * mov_factor * (outcome - expected)

        ratings[h] = elo_h_before + delta
        ratings[v] = elo_v_before - delta

        new_columns.append((
            elo_h_before,
            ratings[h],
            elo_v_before,
            ratings[v],
            round(expected, 4),
            mov,
            round(mov_factor, 4),
        ))

    df[
        [
            "home_elo_pre",
            "home_elo_post",
            "visitor_elo_pre",
            "visitor_elo_post",
            "home_win_prob",
            "mov",
            "mov_factor",
        ]
    ] = new_columns

    df.to_csv(OUT_DIR / "games_with_elo.csv", index=False)

    latest = pd.concat(
        [
            df[["date", "home_team_id", "home_team_name", "home_elo_post"]]
            .rename(columns={
                "home_team_id": "team_id",
                "home_team_name": "team_name",
                "home_elo_post": "elo",
            }),
            df[["date", "visitor_team_id", "visitor_team_name", "visitor_elo_post"]]
            .rename(columns={
                "visitor_team_id": "team_id",
                "visitor_team_name": "team_name",
                "visitor_elo_post": "elo",
            }),
        ],
        ignore_index=True,
    )

    latest = latest.sort_values("date")
    rankings = latest.loc[latest.groupby("team_id")["date"].idxmax()].copy()
    rankings = rankings.sort_values("elo", ascending=False).reset_index(drop=True)
    rankings["rank"] = rankings.index + 1
    rankings["elo"] = rankings["elo"].round(1)

    rankings[["rank", "team_id", "team_name", "elo"]].to_json(
        OUT_DIR / "rankings.json",
        orient="records",
        indent=2,
        force_ascii=False,
    )

    metadata = {
        "league": "NBA",
        "k_factor": K_FACTOR,
        "home_adv": HOME_ADV,
        "regression": REGRESSION,
        "mov_c": MOV_C,
        "games": int(len(df)),
        "last_game_date": str(df["date"].max().date()),
    }

    with open(OUT_DIR / "metadata.json", "w", encoding="utf-8") as f:
        json.dump(metadata, f, indent=2, ensure_ascii=False)

    print(f"Saved: {OUT_DIR / 'games_with_elo.csv'}")
    print(f"Saved: {OUT_DIR / 'rankings.json'}")
    print(f"Saved: {OUT_DIR / 'metadata.json'}")


if __name__ == "__main__":
    build_nba_elo()