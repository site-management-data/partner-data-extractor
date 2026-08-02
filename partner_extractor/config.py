from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()


@dataclass(frozen=True)
class Settings:
    partner_name: str
    output_filename: str
    output_directory: Path
    site_list_url: str
    activity_url: str
    site_monitoring_url: str
    contacts_url: str
    site_alert_url: str
    referrals_url: str
    activity_partner_column: str = "Agency"
    include_alerts: bool = True
    include_referrals: bool = True


def _bool_env(name: str, default: bool = True) -> bool:
    value = os.getenv(name)
    if value is None:
        return default
    return value.strip().casefold() in {"1", "true", "yes", "y", "on"}


def get_settings() -> Settings:
    partner = os.getenv("PARTNER_NAME", "MAAN").strip()
    output_filename = os.getenv(
        "OUTPUT_FILENAME", f"{partner}_Partner_Data.xlsx"
    ).strip()

    return Settings(
        partner_name=partner,
        output_filename=output_filename,
        output_directory=Path(os.getenv("OUTPUT_DIRECTORY", "outputs")),
        site_list_url=os.getenv("SITE_LIST_URL", "").strip(),
        activity_url=os.getenv("ACTIVITY_URL", "").strip(),
        site_monitoring_url=os.getenv("SITE_MONITORING_URL", "").strip(),
        contacts_url=os.getenv("CONTACTS_URL", "").strip(),
        site_alert_url=os.getenv("SITE_ALERT_URL", "").strip(),
        referrals_url=os.getenv("REFERRALS_URL", "").strip(),
        activity_partner_column=os.getenv("ACTIVITY_PARTNER_COLUMN", "Agency").strip(),
        include_alerts=_bool_env("INCLUDE_ALERTS", True),
        include_referrals=_bool_env("INCLUDE_REFERRALS", True),
    )
