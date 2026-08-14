import os
import html
from datetime import datetime

import resend
from dotenv import load_dotenv

load_dotenv()

RESEND_API_KEY = os.getenv("RESEND_API_KEY")
ALERT_EMAIL = os.getenv("ALERT_EMAIL")

if RESEND_API_KEY:
    resend.api_key = RESEND_API_KEY


# ============================================================
# FORMATTING
# ============================================================

def format_date(value):
    if not value:
        return "Unknown Date"

    try:
        value = str(value).replace("T", " ").split(" ")[0]
        d = datetime.strptime(value, "%Y-%m-%d")
        day = d.day
        suffix = "th" if 11 <= day <= 13 else {1: "st", 2: "nd", 3: "rd"}.get(day % 10, "th")
        return f"{day}{suffix} {d.strftime('%B')} {d.year}"
    except Exception:
        return str(value)


def format_number(value):
    if value is None or value == "":
        return "N/A"
    try:
        return f"{float(value):,.2f}"
    except (ValueError, TypeError):
        return str(value)


def format_change(value):
    if value is None or value == "":
        return "N/A"
    try:
        value = float(value)
        sign = "+" if value > 0 else ""
        return f"{sign}{value:.2f}%"
    except (ValueError, TypeError):
        return str(value)


def get_change_arrow(value):
    try:
        value = float(value)
        if value < 0:
            return "↓"
        if value > 0:
            return "↑"
        return "→"
    except (ValueError, TypeError):
        return ""


def clean_metric_name(name):
    replacements = {
        "Conversion_Rate": "Conversion Rate",
        "Avg_Order_Value": "Average Order Value",
        "Ad_Spend": "Ad Spend",
        "Units_Shipped": "Units Shipped",
        "Downtime_Hours": "Downtime Hours",
        "Energy_Usage_kWh": "Energy Usage (kWh)",
        "Labor_Hours": "Labor Hours",
    }
    return replacements.get(name, str(name).replace("_", " "))


# ============================================================
# METRIC TABLE
# ============================================================

def build_metric_rows(incident):
    rows = []

    for metric in incident.get("metrics", []) or []:
        raw_name = metric.get("metric") or metric.get("name") or "Unknown Metric"
        name = clean_metric_name(raw_name)
        actual = metric.get("actual")
        baseline = metric.get("baseline")
        change = metric.get("change")
        arrow = get_change_arrow(change)

        rows.append(f"""
        <tr>
            <td valign="middle" style="width:34%;padding:11px 7px;border-top:1px solid #e5e7eb;font-family:Arial,Helvetica,sans-serif;font-size:11px;line-height:16px;color:#25282d;font-weight:700;word-break:break-word;overflow-wrap:anywhere;">
                {html.escape(str(name))}
            </td>
            <td align="right" valign="middle" style="width:22%;padding:11px 5px;border-top:1px solid #e5e7eb;font-family:Arial,Helvetica,sans-serif;font-size:10px;line-height:16px;color:#25282d;white-space:nowrap;">
                {html.escape(format_number(actual))}
            </td>
            <td align="right" valign="middle" style="width:22%;padding:11px 5px;border-top:1px solid #e5e7eb;font-family:Arial,Helvetica,sans-serif;font-size:10px;line-height:16px;color:#25282d;white-space:nowrap;">
                {html.escape(format_number(baseline))}
            </td>
            <td align="right" valign="middle" style="width:22%;padding:11px 6px;border-top:1px solid #e5e7eb;font-family:Arial,Helvetica,sans-serif;font-size:10px;line-height:16px;color:#d52f2f;font-weight:700;white-space:nowrap;">
                {html.escape(format_change(change))} {html.escape(arrow)}
            </td>
        </tr>
        """)

    if not rows:
        return """
        <tr>
            <td colspan="4" style="padding:14px;font-family:Arial,Helvetica,sans-serif;font-size:11px;color:#6b7280;">
                No affected metrics were supplied for this incident.
            </td>
        </tr>
        """

    return "".join(rows)


# ============================================================
# AI SECTION PARSER + HTML
# ============================================================

AI_HEADINGS = (
    "What Happened",
    "Key Metrics",
    "Likely Reason",
    "What to Investigate",
)


def extract_ai_sections(explanation):
    sections = {heading: [] for heading in AI_HEADINGS}

    if not explanation:
        return {heading: "" for heading in AI_HEADINGS}

    current = None

    for raw_line in str(explanation).replace("\r\n", "\n").replace("\r", "\n").split("\n"):
        line = raw_line.strip()
        if not line:
            continue

        normalized = line.rstrip(":").strip().lower()
        matched = next(
            (heading for heading in AI_HEADINGS if normalized == heading.lower()),
            None,
        )

        if matched:
            current = matched
            continue

        if current:
            sections[current].append(line)

    return {
        heading: " ".join(parts).strip()
        for heading, parts in sections.items()
    }


def build_ai_analysis(explanation):
    """
    Render the exact Gemini explanation from the dashboard.

    IMPORTANT: the four AI sections are deliberately stacked.
    They are NOT placed in columns, because Gmail/iPhone can
    otherwise squeeze each column down to a few characters.
    """

    sections = extract_ai_sections(explanation)

    fallback = {
        "What Happened": "AI analysis was not provided for this incident.",
        "Key Metrics": "See the affected metrics table above.",
        "Likely Reason": "The available data does not confirm a specific cause.",
        "What to Investigate": "Review the affected business activity around this date.",
    }

    for heading in AI_HEADINGS:
        if not sections[heading]:
            sections[heading] = fallback[heading]

    icons = {
        "What Happened": "▰",
        "Key Metrics": "◔",
        "Likely Reason": "♧",
        "What to Investigate": "⌕",
    }

    content = []

    for index, heading in enumerate(AI_HEADINGS):
        top_border = "border-top:1px solid #f0dada;" if index else ""

        content.append(f"""
        <tr>
            <td style="padding:15px 0 5px 0;{top_border}font-family:Arial,Helvetica,sans-serif;">
                <div style="font-size:13px;line-height:19px;font-weight:800;color:#20242a;">
                    <span style="color:#df3232;font-size:14px;">{icons[heading]}</span>&nbsp;{html.escape(heading)}
                </div>
            </td>
        </tr>
        <tr>
            <td style="padding:0 0 15px 0;font-family:Arial,Helvetica,sans-serif;font-size:13px;line-height:21px;color:#4b5563;word-break:normal;overflow-wrap:break-word;">
                {html.escape(sections[heading])}
            </td>
        </tr>
        """)

    return f"""
    <table role="presentation" width="100%" cellpadding="0" cellspacing="0" border="0" style="width:100%;margin:0 0 24px 0;border:1px solid #f1cccc;border-left:4px solid #e63232;background:#fffafa;border-radius:10px;">
        <tr>
            <td style="padding:18px 18px 8px 18px;font-family:Arial,Helvetica,sans-serif;">
                <div style="font-size:15px;line-height:21px;font-weight:800;color:#d92c2c;">
                    ✦&nbsp; AI ANALYSIS
                </div>
            </td>
        </tr>
        <tr>
            <td style="padding:0 18px 2px 18px;">
                <table role="presentation" width="100%" cellpadding="0" cellspacing="0" border="0" style="width:100%;">
                    {''.join(content)}
                </table>
            </td>
        </tr>
    </table>
    """


# ============================================================
# CONSOLIDATED EMAIL
# ============================================================

def build_consolidated_email_html(incidents):
    incidents = incidents or []
    count = len(incidents)
    incident_word = "incident" if count == 1 else "incidents"

    if not incidents:
        raise ValueError("No incidents were supplied for the email report.")

    blocks = []

    for incident in incidents:
        date = format_date(incident.get("date"))
        severity = str(incident.get("severity") or "CRITICAL").upper()
        explanation = str(incident.get("ai_explanation") or "").strip()

        # NEVER replace a missing dashboard explanation with a generic report.
        if not explanation:
            raise ValueError(
                f"Missing AI explanation for {date}. Generate the dashboard AI analysis before sending the report."
            )

        metrics_html = build_metric_rows(incident)
        ai_html = build_ai_analysis(explanation)

        blocks.append(f"""
        <tr>
            <td style="padding:0 0 24px 0;">
                <table role="presentation" width="100%" cellpadding="0" cellspacing="0" border="0" style="width:100%;border:1px solid #e3e5e8;background:#ffffff;border-radius:12px;">

                    <!-- INCIDENT HEADER -->
                    <tr>
                        <td style="padding:22px 20px 16px 20px;">
                            <table role="presentation" width="100%" cellpadding="0" cellspacing="0" border="0" style="width:100%;">
                                <tr>
                                    <td valign="middle" style="font-family:Arial,Helvetica,sans-serif;font-size:21px;line-height:27px;font-weight:800;color:#17191c;">
                                        {html.escape(date)}
                                    </td>
                                    <td align="right" valign="middle" style="font-family:Arial,Helvetica,sans-serif;width:105px;">
                                        <span style="display:inline-block;background:#e95757;color:#ffffff;padding:8px 12px;border-radius:18px;font-size:10px;line-height:12px;font-weight:800;letter-spacing:.5px;">
                                            {html.escape(severity)}
                                        </span>
                                    </td>
                                </tr>
                            </table>
                        </td>
                    </tr>

                    <!-- METRICS -->
                    <tr>
                        <td style="padding:0 20px 20px 20px;">
                            <div style="font-family:Arial,Helvetica,sans-serif;font-size:13px;line-height:18px;font-weight:800;color:#17191c;margin-bottom:10px;">
                                📈&nbsp; AFFECTED METRICS
                            </div>

                            <table role="presentation" width="100%" cellpadding="0" cellspacing="0" border="0" style="width:100%;table-layout:fixed;border:1px solid #dfe2e6;">
                                <tr style="background:#eef1f5;">
                                    <th align="left" width="34%" style="width:34%;padding:10px 7px;font-family:Arial,Helvetica,sans-serif;font-size:10px;line-height:14px;color:#25282d;font-weight:800;">Metric</th>
                                    <th align="right" width="22%" style="width:22%;padding:10px 5px;font-family:Arial,Helvetica,sans-serif;font-size:10px;line-height:14px;color:#25282d;font-weight:800;">Actual</th>
                                    <th align="right" width="22%" style="width:22%;padding:10px 5px;font-family:Arial,Helvetica,sans-serif;font-size:10px;line-height:14px;color:#25282d;font-weight:800;">Baseline</th>
                                    <th align="right" width="22%" style="width:22%;padding:10px 6px;font-family:Arial,Helvetica,sans-serif;font-size:10px;line-height:14px;color:#25282d;font-weight:800;">Change</th>
                                </tr>
                                {metrics_html}
                            </table>
                        </td>
                    </tr>

                    <!-- AI -->
                    <tr>
                        <td style="padding:0 20px 0 20px;">
                            {ai_html}
                        </td>
                    </tr>

                </table>
            </td>
        </tr>
        """)

    return f"""<!DOCTYPE html>
<html>
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>InsightGuard Critical Report</title>
</head>
<body style="margin:0;padding:0;background:#f4f5f7;">

<table role="presentation" width="100%" cellpadding="0" cellspacing="0" border="0" style="width:100%;background:#f4f5f7;">
<tr>
<td align="center" style="padding:18px 8px;">

<table role="presentation" width="100%" cellpadding="0" cellspacing="0" border="0" style="width:100%;max-width:760px;background:#ffffff;border:1px solid #e5e7eb;border-radius:14px;">

    <!-- HEADER -->
    <tr>
        <td style="padding:24px 20px 18px 20px;border-bottom:1px solid #e5e7eb;">
            <div style="font-family:Arial,Helvetica,sans-serif;font-size:21px;line-height:27px;font-weight:800;color:#17191c;">
                Insight<span style="color:#e22b2b;">Guard</span>
            </div>
            <div style="margin-top:5px;font-family:Arial,Helvetica,sans-serif;font-size:12px;line-height:18px;color:#6b7280;">
                Consolidated Critical Incident Report
            </div>
        </td>
    </tr>

    <!-- HERO -->
    <tr>
        <td style="padding:20px 20px 22px 20px;">
            <div style="font-family:Arial,Helvetica,sans-serif;font-size:23px;line-height:29px;font-weight:800;color:#17191c;">
                Critical Anomalies Detected
            </div>
            <div style="margin-top:5px;font-family:Arial,Helvetica,sans-serif;font-size:13px;line-height:19px;color:#6b7280;">
                {count} critical {incident_word} detected across the uploaded dataset.
            </div>
        </td>
    </tr>

    <!-- INCIDENTS -->
    <tr>
        <td style="padding:0 12px;">
            <table role="presentation" width="100%" cellpadding="0" cellspacing="0" border="0" style="width:100%;">
                {''.join(blocks)}
            </table>
        </td>
    </tr>

    <!-- FOOTER -->
    <tr>
        <td style="padding:20px;border-top:1px solid #e5e7eb;background:#fafafa;">
            <div style="font-family:Arial,Helvetica,sans-serif;font-size:11px;line-height:17px;color:#6b7280;">
                <strong style="color:#4b5563;">🛡 InsightGuard</strong><br>
                This consolidated report was generated by InsightGuard.<br>
                The AI analysis shown here is the same analysis generated for the InsightGuard dashboard.
            </div>
        </td>
    </tr>

</table>

</td>
</tr>
</table>

</body>
</html>
"""


# ============================================================
# SINGLE ALERT COMPATIBILITY FUNCTION
# ============================================================

def build_email_html(incident, root_cause=""):
    explanation = incident.get("ai_explanation") or root_cause
    if not explanation:
        raise ValueError("Missing AI explanation for the incident.")

    payload = dict(incident)
    payload["ai_explanation"] = explanation
    return build_consolidated_email_html([payload])


def send_alert_email(incident, root_cause="", recipient=None):
    if not RESEND_API_KEY:
        raise ValueError("RESEND_API_KEY not found in .env")

    html_content = build_email_html(incident, root_cause)

    response = resend.Emails.send({
        "from": os.getenv("RESEND_FROM_EMAIL", "onboarding@resend.dev"),
        "to": [recipient or ALERT_EMAIL],
        "subject": (
            "🔴 InsightGuard Alert — Critical Anomaly on "
            f"{format_date(incident.get('date'))}"
        ),
        "html": html_content,
    })

    return response