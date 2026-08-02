# Partner Data Extract Generator

A reusable Python project that downloads Zite Manager report exports, filters them for one partner, and publishes a polished Excel workbook under a stable filename.

## Generated workbook

- **About** — generation timestamp, descriptions, and record counts
- **Site List** — partner sites where either `site_agency` or `site_type` matches the configured partner
- **Latest Site Assessment** — only the newest monitoring record for each partner site
- **Activity Report** — partner activity submissions
- **Activity Summary** — automatic summary including **Unique Sites**
- **Service Map** — contacts and service mapping
- **Site Alerts** — alerts on partner-supported sites plus alerts submitted by the partner on other sites

There is deliberately no site-assessment-history worksheet.

## Current transformation rules

- Remove `region_3_name`, `region_3_id`, and `geometry` from Site List.
- Move `Site Information/Location` from the alerts source into Site List as `Site Location`.
- Do not include that location field again in Site Alerts.
- Remove these fields from Activity Report:
  - `Location`
  - `Submission date (reformatted)`
  - `money spent on IEC improvements`
  - `voluntary project`
  - `labour days paid through CFW`
- Standardize recognized date fields as `YYYY-MM-DD`.
- Calculate Activity Summary indirect beneficiaries from `total indirect beneficiaries` rather than the yes/no field.
- Include Site Alerts where either the site is partner-supported or the reporting agency matches the partner.

## Local setup on Windows

```powershell
py -3.11 -m venv .venv
.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r requirements.txt
```

## Test using downloaded exports

Place the five exports together in one directory. The script finds the newest file matching each standard export prefix.

```powershell
python main.py --local-dir "C:\path\to\exports"
```

## Run using live Zite URLs

Set the values for the current PowerShell session:

```powershell
$env:PARTNER_NAME="MAAN"
$env:SITE_LIST_URL="YOUR FULL URL"
$env:ACTIVITY_URL="YOUR FULL URL"
$env:SITE_MONITORING_URL="YOUR FULL URL"
$env:CONTACTS_URL="YOUR FULL URL"
$env:SITE_ALERT_URL="YOUR FULL URL"
$env:REFERRALS_URL="YOUR FULL URL"
python main.py
```

The default result is:

```text
outputs/MAAN_Partner_Data.xlsx
```

## GitHub automation

The included workflow runs daily and can also be started manually. In the repository settings, create these Actions secrets:

- `SITE_LIST_URL`
- `ACTIVITY_URL`
- `SITE_MONITORING_URL`
- `CONTACTS_URL`
- `SITE_ALERT_URL`
- `REFERRALS_URL`

After the workbook is committed, the permanent direct-download address is:

```text
https://raw.githubusercontent.com/ACCOUNT/REPOSITORY/main/outputs/MAAN_Partner_Data.xlsx
```

Keep the repository private unless every exported field is appropriate for public access. A raw link from a private repository will not work anonymously for partners.


## Referral data protection

The Referrals worksheet uses a strict allow-list. It excludes household names, ID numbers, phone numbers, dates of birth, marital details, spouse information, household demographic breakdowns, consent/user fields, comments and free-text narratives. `Referral Type` is the first column so users can quickly filter between Household, Pipeline and Site referrals. Store the complete referral report URL as the `REFERRALS_URL` environment variable or GitHub Secret; never commit its access key.
