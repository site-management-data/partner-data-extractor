from __future__ import annotations

from typing import Mapping

import pandas as pd

from .config import Settings


SITE_COLUMNS_TO_REMOVE = ["region_3_name", "region_3_id", "geometry"]
ACTIVITY_COLUMNS_TO_REMOVE = [
    "Location",
    "Submission date (reformatted)",
    "money spent on IEC improvements",
    "voluntary project",
    "labour days paid through CFW",
]
ALERT_LOCATION_COLUMN = "Site Information/Location"

# Referrals use an allow-list so personally identifiable or sensitive fields
# cannot enter the partner extract merely because Zite adds a new column.
REFERRAL_SAFE_COLUMNS = [
    "Referral Type",
    "Site ID",
    "Site Name",
    "Case ID",
    "Url",
    "Submission Date (on Zite metada)",
    "Date Submitted",
    "Case Status",
    "Last reviewed date",
    "Referring Agency",
    "Cluster/Sector",
    "Cluster/Sector of Referral",
    "Service (including other)",
    "Service",
    "Target Group",
    "Agency providing services",
    "Date of service provision",
    "Has referral been closed?",
    "Resolution of referral",
    "Agency that resolved it",
    "Type of Agency",
    "Resolution Agency Final",
    "Date of Resolution",
    "Site Type",
    "Site Status",
    "Region",
]


def normalise_site_id(series: pd.Series) -> pd.Series:
    return series.astype("string").str.strip().str.upper()


def require_columns(df: pd.DataFrame, columns: list[str], dataset: str) -> None:
    missing = [column for column in columns if column not in df.columns]
    if missing:
        raise KeyError(f"{dataset} is missing required column(s): {', '.join(missing)}")


def _partner_match(series: pd.Series, partner_name: str) -> pd.Series:
    return (
        series.astype("string").str.strip().str.casefold()
        == partner_name.strip().casefold()
    )


def create_activity_summary(activities: pd.DataFrame) -> pd.DataFrame:
    if activities.empty:
        return pd.DataFrame(
            columns=[
                "Primary Activity",
                "Sub-Activity",
                "Number of Activities",
                "Achieved",
                "Direct Participants",
                "Indirect Beneficiaries",
                "Unique Sites",
            ]
        )

    activities = activities.copy()
    group_columns = [
        column
        for column in ["Primary Activity", "Sub-Activity"]
        if column in activities.columns
    ]
    if not group_columns:
        group_columns = ["Agency"]

    for column in ["Achieved", "total participants", "total indirect beneficiaries"]:
        if column in activities.columns:
            activities[column] = pd.to_numeric(activities[column], errors="coerce")

    aggregation: dict[str, tuple[str, str]] = {
        "Number of Activities": ("Site ID", "size"),
        "Unique Sites": ("Site ID", "nunique"),
    }
    if "Achieved" in activities.columns:
        aggregation["Achieved"] = ("Achieved", "sum")
    if "total participants" in activities.columns:
        aggregation["Direct Participants"] = ("total participants", "sum")
    if "total indirect beneficiaries" in activities.columns:
        aggregation["Indirect Beneficiaries"] = (
            "total indirect beneficiaries",
            "sum",
        )

    summary = (
        activities.groupby(group_columns, dropna=False)
        .agg(**aggregation)
        .reset_index()
    )

    ordered = group_columns + [
        column
        for column in [
            "Number of Activities",
            "Achieved",
            "Direct Participants",
            "Indirect Beneficiaries",
            "Unique Sites",
        ]
        if column in summary.columns
    ]
    return summary[ordered].sort_values(group_columns).reset_index(drop=True)


def standardise_dates(dataframe: pd.DataFrame) -> pd.DataFrame:
    """Convert date fields to real dates so Excel consistently shows YYYY-MM-DD."""
    dataframe = dataframe.copy()
    for column in dataframe.columns:
        name = str(column).strip().casefold()
        if "date" in name or name == "today":
            converted = pd.to_datetime(dataframe[column], errors="coerce")
            # Only replace the column when at least one actual date was recognised.
            if converted.notna().any():
                dataframe[column] = converted.dt.date
    return dataframe


def filter_partner_data(
    raw: Mapping[str, pd.DataFrame], settings: Settings
) -> dict[str, pd.DataFrame]:
    sites = raw["sites"].copy()
    require_columns(sites, ["Site ID", "site_agency", "site_type"], "Site list")
    sites["Site ID"] = normalise_site_id(sites["Site ID"])

    # Inclusive rule: retain a site when either coding field identifies the partner.
    agency_match = _partner_match(sites["site_agency"], settings.partner_name)
    type_match = _partner_match(sites["site_type"], settings.partner_name)
    partner_sites = sites[agency_match | type_match].copy()
    partner_sites = partner_sites.drop_duplicates(subset=["Site ID"], keep="last")
    site_ids = set(partner_sites["Site ID"].dropna())

    if not site_ids:
        raise ValueError(
            f"No sites found for {settings.partner_name!r} using site_agency or site_type."
        )

    activities = raw["activities"].copy()
    require_columns(
        activities,
        ["Site ID", settings.activity_partner_column],
        "Activity report",
    )
    activities["Site ID"] = normalise_site_id(activities["Site ID"])
    activities = activities[
        _partner_match(
            activities[settings.activity_partner_column], settings.partner_name
        )
    ].copy()
    activities = activities.drop(columns=ACTIVITY_COLUMNS_TO_REMOVE, errors="ignore")

    monitoring = raw["monitoring"].copy()
    require_columns(monitoring, ["Site ID", "today"], "Site monitoring")
    monitoring["Site ID"] = normalise_site_id(monitoring["Site ID"])
    monitoring["today"] = pd.to_datetime(monitoring["today"], errors="coerce")
    monitoring = monitoring[monitoring["Site ID"].isin(site_ids)].copy()
    monitoring = monitoring.sort_values(
        ["Site ID", "today"],
        ascending=[True, False],
        na_position="last",
    )
    latest_monitoring = monitoring.drop_duplicates(
        subset=["Site ID"], keep="first"
    ).reset_index(drop=True)

    contacts = raw["contacts"].copy()
    require_columns(contacts, ["Site ID"], "Contacts")
    contacts["Site ID"] = normalise_site_id(contacts["Site ID"])
    contacts = contacts[contacts["Site ID"].isin(site_ids)].copy()

    alerts = raw["alerts"].copy()
    if not alerts.empty:
        reporting_agency_column = "Details of Alert-Agency name"
        require_columns(alerts, ["Site ID", reporting_agency_column], "Site alerts")
        alerts["Site ID"] = normalise_site_id(alerts["Site ID"])

        # Include only alerts submitted by the partner.
        alerts = alerts[
            _partner_match(
                alerts[reporting_agency_column],
                settings.partner_name,
            )
        ].copy()

        # Site Location belongs on Site List, not on the alert output sheet.
        if ALERT_LOCATION_COLUMN in alerts.columns:
            site_locations = (
                alerts[["Site ID", ALERT_LOCATION_COLUMN]]
                .dropna(subset=[ALERT_LOCATION_COLUMN])
                .drop_duplicates(subset=["Site ID"], keep="last")
                .rename(columns={ALERT_LOCATION_COLUMN: "Site Location"})
            )
            partner_sites = partner_sites.merge(site_locations, on="Site ID", how="left")
            alerts = alerts.drop(columns=[ALERT_LOCATION_COLUMN])

    partner_sites = partner_sites.drop(columns=SITE_COLUMNS_TO_REMOVE, errors="ignore")

    referrals = raw.get("referrals", pd.DataFrame()).copy()
    if settings.include_referrals and not referrals.empty:
        require_columns(referrals, ["Site ID", "Referral Type"], "Referrals")
        referrals["Site ID"] = normalise_site_id(referrals["Site ID"])

        referral_agency_column = "Referring Agency"
        require_columns(
            referrals,
            ["Site ID", "Referral Type", referral_agency_column],
            "Referrals",
        )

        # Include only referrals submitted/referred by the partner.
        referrals = referrals[
            _partner_match(
                referrals[referral_agency_column],
                settings.partner_name,
            )
        ].copy()

        # Keep only explicitly approved operational fields. Household names, IDs,
        # phone numbers, dates of birth, marital details, demographic breakdowns,
        # consent/user fields, comments and free-text narratives are excluded.
        safe_columns = [
            column for column in REFERRAL_SAFE_COLUMNS if column in referrals.columns
        ]
        referrals = referrals[safe_columns]

        # Make Referral Type the left-most field for quick Excel filtering.
        referrals = referrals.sort_values(
            [column for column in ["Referral Type", "Date Submitted", "Site ID"] if column in referrals.columns],
            ascending=[True, False, True][:len([column for column in ["Referral Type", "Date Submitted", "Site ID"] if column in referrals.columns])],
            na_position="last",
        )

    sheets = {
        "Site List": standardise_dates(partner_sites.reset_index(drop=True)),
        "Latest Site Assessment": standardise_dates(latest_monitoring),
        "Activity Report": standardise_dates(activities.reset_index(drop=True)),
        "Activity Summary": create_activity_summary(activities),
        "Service Map": standardise_dates(contacts.reset_index(drop=True)),
    }
    if settings.include_referrals:
        sheets["Referrals"] = standardise_dates(referrals.reset_index(drop=True))
    if settings.include_alerts:
        sheets["Site Alerts"] = standardise_dates(alerts.reset_index(drop=True))
    return sheets
