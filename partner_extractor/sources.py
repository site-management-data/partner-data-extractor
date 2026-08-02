from __future__ import annotations

import io
from pathlib import Path

import pandas as pd
import requests

from .config import Settings


LOCAL_FILE_PATTERNS = {
    "sites": ("etl_sitelist*.xlsx",),
    "activities": ("activity-reporting-form*.xlsx",),
    "monitoring": ("etl_sitemonitoring*.xlsx",),
    "contacts": ("contacts*.xlsx",),
    "alerts": ("*site_alert*.xlsx", "*site-alert*.xlsx"),
    "referrals": ("*referrals*.xlsx", "*referral*.xlsx"),
}


def read_excel_url(url: str, label: str) -> pd.DataFrame:
    if not url:
        raise ValueError(f"No URL configured for {label}.")

    print(f"Downloading {label}...")

    response = requests.get(url, timeout=180)
    response.raise_for_status()

    content_type = response.headers.get("Content-Type", "").lower()

    print(
        f"  Status: {response.status_code} | "
        f"Content-Type: {content_type} | "
        f"Size: {len(response.content):,} bytes"
    )

    if "application/json" in content_type:
        data = response.json()

        if isinstance(data, list):
            return pd.DataFrame(data)

        if isinstance(data, dict):
            for key in ("results", "data", "items"):
                if key in data and isinstance(data[key], list):
                    return pd.DataFrame(data[key])

        raise ValueError(
            f"Could not interpret JSON response for {label}. "
            f"Expected a list of records."
        )

    try:
        return pd.read_excel(
            io.BytesIO(response.content),
            sheet_name="Main",
            engine="openpyxl",
        )
    except Exception as exc:
        preview = response.text[:200] if response.content else "<empty response>"
        raise ValueError(
            f"Could not read {label} as JSON or Excel. "
            f"Content-Type was {content_type}. "
            f"Response began with: {preview!r}"
        ) from exc

def _find_local_export(directory: Path, key: str) -> Path:
    matches: list[Path] = []
    for pattern in LOCAL_FILE_PATTERNS[key]:
        matches.extend(directory.glob(pattern))

    matches = sorted(set(matches), key=lambda path: path.stat().st_mtime, reverse=True)
    if not matches:
        patterns = ", ".join(LOCAL_FILE_PATTERNS[key])
        raise FileNotFoundError(
            f"No local {key} export found in {directory}. Expected: {patterns}"
        )
    return matches[0]


def read_local_export(directory: Path, key: str) -> pd.DataFrame:
    path = _find_local_export(directory, key)
    return pd.read_excel(path, sheet_name="Main")


def load_sources(
    settings: Settings, local_dir: Path | None = None
) -> dict[str, pd.DataFrame]:
    if local_dir:
        sources = {
            "sites": read_local_export(local_dir, "sites"),
            "activities": read_local_export(local_dir, "activities"),
            "monitoring": read_local_export(local_dir, "monitoring"),
            "contacts": read_local_export(local_dir, "contacts"),
        }
        sources["alerts"] = (
            read_local_export(local_dir, "alerts")
            if settings.include_alerts
            else pd.DataFrame()
        )
        sources["referrals"] = (
            read_local_export(local_dir, "referrals")
            if settings.include_referrals
            else pd.DataFrame()
        )
        return sources

    return {
        "sites": read_excel_url(settings.site_list_url, "site list"),
        "activities": read_excel_url(settings.activity_url, "activity report"),
        "monitoring": read_excel_url(
            settings.site_monitoring_url, "site monitoring"
        ),
        "contacts": read_excel_url(settings.contacts_url, "contacts"),
        "alerts": read_excel_url(settings.site_alert_url, "site alerts")
        if settings.include_alerts
        else pd.DataFrame(),
        "referrals": read_excel_url(settings.referrals_url, "referrals")
        if settings.include_referrals
        else pd.DataFrame(),
    }
