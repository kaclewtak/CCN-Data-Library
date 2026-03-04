from __future__ import annotations

import pandas as pd


def zoom_for_span(span_degrees: float) -> int:
    if span_degrees <= 0.02:
        return 15
    if span_degrees <= 0.05:
        return 14
    if span_degrees <= 0.1:
        return 13
    if span_degrees <= 0.25:
        return 12
    if span_degrees <= 0.5:
        return 11
    if span_degrees <= 1.0:
        return 10
    if span_degrees <= 2.0:
        return 9
    if span_degrees <= 5.0:
        return 8
    if span_degrees <= 10.0:
        return 7
    if span_degrees <= 20.0:
        return 6
    return 4


def normalized_table_points(table_points: pd.DataFrame) -> pd.DataFrame:
    if table_points.empty:
        return table_points

    points = table_points.copy()
    points["latitude"] = pd.to_numeric(points["latitude"], errors="coerce")
    points["longitude"] = pd.to_numeric(points["longitude"], errors="coerce")
    points = points.dropna(subset=["latitude", "longitude"])
    return points


def compute_imported_view(
    table_points: pd.DataFrame,
) -> tuple[tuple[float, float], int, tuple[int, float, float, float]] | None:
    points = normalized_table_points(table_points)
    if points.empty:
        return None

    center_lat = float(points["latitude"].mean())
    center_lng = float(points["longitude"].mean())
    lat_span = float(points["latitude"].max() - points["latitude"].min())
    lng_span = float(points["longitude"].max() - points["longitude"].min())
    span = max(lat_span, lng_span)
    zoom = zoom_for_span(span)

    view_key = (len(points), round(center_lat, 5), round(center_lng, 5), round(span, 5))
    return (center_lat, center_lng), zoom, view_key
