from __future__ import annotations

import numpy as np
import pandas as pd

CONTINENT_MAP = {
    "angola": "africa",
    "argentina": "south america",
    "australia": "oceania",
    "bahamas": "north america",
    "bangladesh": "asia",
    "belgium": "europe",
    "belize": "north america",
    "benin": "africa",
    "brazil": "south america",
    "cambodia": "asia",
    "cameroon": "africa",
    "canada": "north america",
    "china": "asia",
    "colombia": "south america",
    "costa rica": "north america",
    "cuba": "north america",
    "cyprus": "europe",
    "democratic republic of the congo": "africa",
    "denmark": "europe",
    "dominican republic": "north america",
    "ecuador": "south america",
    "egypt": "africa",
    "el salvador": "north america",
    "estonia": "europe",
    "fiji": "oceania",
    "france": "europe",
    "gabon": "africa",
    "germany": "europe",
    "ghana": "africa",
    "greece": "europe",
    "guinea-bissau": "africa",
    "honduras": "north america",
    "india": "asia",
    "indonesia": "asia",
    "iran": "asia",
    "ireland": "europe",
    "italy": "europe",
    "japan": "asia",
    "jordan": "asia",
    "kenya": "africa",
    "madagascar": "africa",
    "malaysia": "asia",
    "malta": "europe",
    "mexico": "north america",
    "micronesia": "oceania",
    "morocco": "africa",
    "mozambique": "africa",
    "netherlands": "europe",
    "new zealand": "oceania",
    "nigeria": "africa",
    "norway": "europe",
    "pakistan": "asia",
    "palau": "oceania",
    "panama": "north america",
    "philippines": "asia",
    "portugal": "europe",
    "russian federation": "europe",
    "saudi arabia": "asia",
    "senegal": "africa",
    "singapore": "asia",
    "south africa": "africa",
    "south korea": "asia",
    "spain": "europe",
    "sri lanka": "asia",
    "swaziland": "africa",
    "tanzania": "africa",
    "thailand": "asia",
    "united arab emirates": "asia",
    "united kingdom": "europe",
    "united states": "north america",
    "vietnam": "asia",
}

REFERENCE_CONTINENTS = ["africa", "asia", "europe", "north america", "south america", "oceania"]


# Helper function
def _map_country_to_continent(country: str) -> str | None:
    return CONTINENT_MAP.get(country.strip().lower())


def compute_coverage_summary(som_bd_df: pd.DataFrame) -> dict:
    if som_bd_df.empty or "area" not in som_bd_df.columns:
        return {
            "country_counts": pd.Series(dtype=int),
            "continent_counts": pd.Series(dtype=int),
            "missing_continents": sorted(REFERENCE_CONTINENTS),
            "present_countries": [],
        }

    country_counts = som_bd_df["area"].dropna().str.strip().value_counts()
    countries_lower = som_bd_df["area"].dropna().str.strip().str.lower()
    continents = countries_lower.map(lambda c: CONTINENT_MAP.get(c, "unknown") if isinstance(c, str) else "unknown")
    continent_counts = continents.value_counts()

    present_continents = set(continent_counts.index) - {"unknown"}
    expected = set(REFERENCE_CONTINENTS)
    missing = sorted(expected - present_continents)

    return {
        "country_counts": country_counts,
        "continent_counts": continent_counts,
        "missing_continents": missing,
        "present_countries": sorted(country_counts.index.tolist()),
    }


def compute_underrepresented_areas(som_bd_df: pd.DataFrame, threshold_percentile: int = 10) -> pd.Series:
    if som_bd_df.empty or "area" not in som_bd_df.columns:
        return pd.Series(dtype=int)

    counts = som_bd_df["area"].dropna().str.strip().value_counts()
    if counts.empty:
        return pd.Series(dtype=int)

    threshold = np.percentile(counts.to_numpy(), threshold_percentile)
    return counts[counts <= threshold].sort_values()


def generate_gap_hints(som_bd_df: pd.DataFrame) -> list[dict]:
    hints: list[dict] = []
    coverage = compute_coverage_summary(som_bd_df)

    for continent in coverage["missing_continents"]:
        hints.append(
            {
                "level": "danger",
                "text": f"{continent.title()} — no data points found for this continent. Consider prioritizing data collection.",
            }
        )

    continent_counts = coverage["continent_counts"]
    if not continent_counts.empty:
        median_count = int(continent_counts[continent_counts.index != "unknown"].median())
        for continent, count in continent_counts.items():
            if continent == "unknown":
                continue
            if count < median_count * 0.1 and continent not in coverage["missing_continents"]:
                hints.append(
                    {
                        "level": "warning",
                        "text": f"{str(continent).title()} — only {count} records (median: {median_count}). This continent may be understudied.",
                    }
                )

    underrep = compute_underrepresented_areas(som_bd_df)
    if not underrep.empty:
        country_counts = coverage["country_counts"]
        median_country = int(country_counts.median()) if not country_counts.empty else 0
        for country, count in underrep.items():
            hints.append(
                {
                    "level": "warning",
                    "text": f"{str(country)} — only {count} records (country median: {median_country}). This area may be understudied.",
                }
            )

    if not hints:
        hints.append({"level": "info", "text": "Geographic coverage appears balanced across known areas."})

    return hints
