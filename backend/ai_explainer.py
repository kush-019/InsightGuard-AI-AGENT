from dotenv import load_dotenv
from google import genai
import os
import math


# ============================================================
# 1. LOAD ENVIRONMENT VARIABLES
# ============================================================

load_dotenv()

api_key = os.getenv("GEMINI_API_KEY")

if not api_key:
    print("❌ GEMINI_API_KEY not found in .env")
    raise ValueError("Missing GEMINI_API_KEY")

print("✅ Gemini API key loaded!")

client = genai.Client(api_key=api_key)


# ============================================================
# HELPERS
# ============================================================

def _num(value):
    """Return a finite float or None."""
    try:
        x = float(value)
        return x if math.isfinite(x) else None
    except (TypeError, ValueError):
        return None


def _fmt(value):
    """Compact numeric formatting for the prompt."""
    x = _num(value)

    if x is None:
        return "N/A"

    if abs(x) >= 1000:
        return f"{x:,.2f}"

    return f"{x:.2f}"


def _metric_name(result):
    """
    Support both backend formats:

        metric
        name

    This prevents AI evidence from disappearing when the
    backend/frontend uses a different field name.
    """

    if not isinstance(result, dict):
        return None

    value = (
        result.get("metric")
        or result.get("name")
    )

    if value is None:
        return None

    return str(value).strip()


def _metric_map(all_results):
    """
    Create a normalized metric lookup.

    Supports both:
        {"metric": "Revenue"}
    and:
        {"name": "Revenue"}
    """

    result = {}

    for r in all_results or []:

        if not isinstance(r, dict):
            continue

        name = _metric_name(r)

        if not name:
            continue

        result[name.lower()] = r

    return result


def _get(m, *names):

    for name in names:

        r = m.get(
            name.lower()
        )

        if r is not None:
            return r

    return None


def _pct_change(actual, baseline):

    actual = _num(actual)
    baseline = _num(baseline)

    if (
        actual is None
        or baseline in (None, 0)
    ):
        return None

    return (
        (actual - baseline)
        / abs(baseline)
    ) * 100


# ============================================================
# DERIVED BUSINESS RELATIONSHIPS
# ============================================================

def _build_derived_relationships(all_results):

    """
    Calculate business relationships in Python so Gemini receives
    verified derived evidence instead of being asked to invent math.
    """

    m = _metric_map(
        all_results
    )

    lines = []

    revenue = _get(
        m,
        "revenue"
    )

    orders = _get(
        m,
        "orders"
    )

    traffic = _get(
        m,
        "traffic"
    )

    conversion = _get(
        m,
        "conversion_rate",
        "conversion rate"
    )

    aov = _get(
        m,
        "avg_order_value",
        "average_order_value",
        "average order value"
    )


    # ========================================================
    # REVENUE / ORDERS / AOV
    # ========================================================

    if revenue and orders:

        rev_actual = _num(
            revenue.get("actual")
        )

        rev_base = _num(
            revenue.get("baseline")
        )

        ord_actual = _num(
            orders.get("actual")
        )

        ord_base = _num(
            orders.get("baseline")
        )

        if (
            rev_actual is not None
            and rev_base is not None
            and ord_actual is not None
            and ord_base is not None
            and ord_actual != 0
            and ord_base != 0
        ):

            implied_aov_actual = (
                rev_actual / ord_actual
            )

            implied_aov_baseline = (
                rev_base / ord_base
            )

            implied_aov_change = _pct_change(
                implied_aov_actual,
                implied_aov_baseline
            )

            lines.append(

                "Revenue vs Orders: "
                f"Revenue changed "
                f"{_fmt(_pct_change(rev_actual, rev_base))}%, "
                f"while Orders changed "
                f"{_fmt(_pct_change(ord_actual, ord_base))}%. "
                f"Implied average order value changed "
                f"{_fmt(implied_aov_change)}% "
                f"(actual "
                f"{_fmt(implied_aov_actual)}, "
                f"baseline "
                f"{_fmt(implied_aov_baseline)})."

            )


    # ========================================================
    # EXPLICIT AOV
    # ========================================================

    if aov:

        aov_actual = _num(
            aov.get("actual")
        )

        aov_base = _num(
            aov.get("baseline")
        )

        if (
            aov_actual is not None
            and aov_base is not None
        ):

            lines.append(

                "Average Order Value: "
                f"actual {_fmt(aov_actual)}, "
                f"baseline {_fmt(aov_base)}, "
                f"change "
                f"{_fmt(_pct_change(aov_actual, aov_base))}%."

            )


    # ========================================================
    # ORDERS / TRAFFIC / CONVERSION
    # ========================================================

    if (
        orders
        and traffic
        and conversion
    ):

        ord_actual = _num(
            orders.get("actual")
        )

        ord_base = _num(
            orders.get("baseline")
        )

        traf_actual = _num(
            traffic.get("actual")
        )

        traf_base = _num(
            traffic.get("baseline")
        )

        conv_actual = _num(
            conversion.get("actual")
        )

        conv_base = _num(
            conversion.get("baseline")
        )

        if (
            ord_actual is not None
            and ord_base is not None
            and traf_actual is not None
            and traf_base is not None
            and conv_actual is not None
            and conv_base is not None
            and traf_actual != 0
            and traf_base != 0
        ):

            implied_traffic_actual = (

                ord_actual / conv_actual

                if conv_actual != 0

                else None

            )

            implied_traffic_baseline = (

                ord_base / conv_base

                if conv_base != 0

                else None

            )

            implied_traffic_change = _pct_change(

                implied_traffic_actual,

                implied_traffic_baseline

            )

            actual_traffic_change = _pct_change(

                traf_actual,

                traf_base

            )

            conversion_change = _pct_change(

                conv_actual,

                conv_base

            )

            lines.append(

                "Orders / Conversion Rate / Traffic relationship: "
                f"Orders changed "
                f"{_fmt(_pct_change(ord_actual, ord_base))}%, "
                f"Conversion Rate changed "
                f"{_fmt(conversion_change)}%, "
                f"observed Traffic changed "
                f"{_fmt(actual_traffic_change)}%. "
                f"Traffic implied by Orders/Conversion Rate "
                f"changed "
                f"{_fmt(implied_traffic_change)}%."

            )


            # ------------------------------------------------
            # CONSISTENCY CHECK
            # ------------------------------------------------

            if implied_traffic_change is not None:

                gap = abs(
                    implied_traffic_change
                    - actual_traffic_change
                )

                if gap > 10:

                    lines.append(

                        "Important consistency note: "
                        "the observed Traffic metric does not "
                        "closely reconcile with Orders and "
                        "Conversion Rate, so do not claim that "
                        "Traffic is mathematically implied by "
                        "those two metrics."

                    )


    # ========================================================
    # NO RELATIONSHIPS
    # ========================================================

    if not lines:

        lines.append(

            "No additional metric relationship could be safely "
            "derived from the available columns."

        )


    return "\n".join(
        lines
    )


# ============================================================
# METRIC EVIDENCE
# ============================================================

def _build_metric_evidence(
    metrics,
    all_results
):

    anomaly_lines = []

    normal_lines = []

    # --------------------------------------------------------
    # USE COMPLETE DATE SNAPSHOT
    # --------------------------------------------------------

    for result in all_results or []:

        name = _metric_name(
            result
        )

        actual = result.get(
            "actual"
        )

        baseline = result.get(
            "baseline"
        )

        change = result.get(
            "change"
        )

        status = result.get(
            "status"
        )

        line = (

            f"{name}: "
            f"actual={_fmt(actual)}, "
            f"baseline={_fmt(baseline)}, "
            f"change={_fmt(change)}%, "
            f"status={status}"

        )

        if status == "ANOMALY":

            anomaly_lines.append(
                line
            )

        elif status == "NORMAL":

            normal_lines.append(
                line
            )


    # --------------------------------------------------------
    # FALLBACK
    # --------------------------------------------------------

    if not anomaly_lines:

        for result in metrics or []:

            name = _metric_name(
                result
            )

            anomaly_lines.append(

                f"{name}: "
                f"actual={_fmt(result.get('actual'))}, "
                f"baseline={_fmt(result.get('baseline'))}, "
                f"change={_fmt(result.get('change'))}%, "
                f"status={result.get('status', 'ANOMALY')}"

            )


    return (
        "\n".join(anomaly_lines),
        "\n".join(normal_lines)
    )


# ============================================================
# GENERATE AI BUSINESS EXPLANATION
# ============================================================

def generate_explanation(
    incident
):

    """
    Generate a date-specific business explanation.

    Both the website and email use this same function.
    """

    if not isinstance(incident, dict):

        raise ValueError(
            "Incident must be a dictionary."
        )


    date = str(
        incident.get(
            "date",
            "Unknown date"
        )
    )


    severity = str(
        incident.get(
            "severity",
            "UNKNOWN"
        )
    )


    metrics = (
        incident.get(
            "metrics"
        )
        or []
    )


    all_results = (
        incident.get(
            "all_results"
        )
        or []
    )


    # --------------------------------------------------------
    # BUILD EVIDENCE
    # --------------------------------------------------------

    (
        anomaly_findings,
        normal_findings
    ) = _build_metric_evidence(

        metrics,

        all_results

    )


    # --------------------------------------------------------
    # BUILD RELATIONSHIPS
    # --------------------------------------------------------

    derived_relationships = (
        _build_derived_relationships(
            all_results
        )
    )


    # ========================================================
    # GEMINI PROMPT
    # ========================================================

    prompt = f"""

You are InsightGuard, an AI business analyst.

Your job is to explain ONE business anomaly in very simple,
clear language that a non-technical business manager can
understand immediately.

Analyze ONLY this date:

{date}

Do not combine it with any other date.

Do not use outside information.

Do not invent facts.

The numbers provided below have already been verified by the
analytics system. Your job is to explain what those numbers
mean for the business.


============================================================
INCIDENT DATE
============================================================

{date}


============================================================
SEVERITY
============================================================

{severity}


============================================================
METRICS THAT CHANGED A LOT
============================================================

{anomaly_findings}


============================================================
OTHER METRICS ON THE SAME DATE
============================================================

{normal_findings}


============================================================
CALCULATED BUSINESS RELATIONSHIPS
============================================================

{derived_relationships}


============================================================
HOW TO REASON
============================================================

1. Explain the situation in everyday business language.

2. Do not simply repeat the percentages.

Instead, explain what the numbers mean.

For example:

BAD:
"Orders decreased by 60% and Revenue decreased by 61%."

GOOD:
"Revenue fell sharply because the business received far fewer
orders than usual."

3. Look at related metrics together.

For example:

If Traffic is normal but Orders are much lower:
say that people were still visiting the business, but fewer
of them completed purchases.

If Orders and Revenue fall together while Average Order Value
stays normal:
say that the main problem appears to be fewer purchases,
not customers spending less per purchase.

If Traffic, Orders and Revenue all fall together:
say that fewer visitors appear to be reaching the business,
which is contributing to fewer purchases.

If Conversion Rate falls while Traffic stays normal:
say that visitors were still arriving, but fewer of them
were turning into customers.

4. Use normal metrics to make the explanation clearer.

For example, if Ad Spend is normal, do not say that the
problem was caused by reduced advertising.

5. Never claim that something definitely happened unless
the supplied data proves it.

Do NOT say:

"Payment gateway failed."

"Website was down."

"Inventory was unavailable."

"Customers encountered checkout errors."

Instead say:

"The pattern suggests that the problem may have happened
during the purchase process."

6. Do not use complicated business or technical words.

AVOID:

"conversion funnel"
"order-driven"
"top-of-funnel"
"downstream"
"customer acquisition"
"operational root cause"
"mathematically implied"
"statistical deviation"
"metric relationships"
"execution failure"

Use simple alternatives:

"website visits"
"number of purchases"
"customers completing purchases"
"amount spent per order"
"something may have gone wrong"
"the available data suggests"

7. Do not sound dramatic.

Do not say:

"critical failure"

"severe execution breakdown"

"catastrophic event"

unless the supplied data explicitly proves such an event.

8. Separate facts from possible explanations.

Use phrases like:

"This suggests..."

"This may indicate..."

"The data points toward..."

"The available data cannot confirm..."

9. The explanation should teach the reader something useful
that is not immediately obvious from the raw numbers.

10. Keep the explanation easy enough that someone with no
data analytics background can understand it.


============================================================
RESPONSE FORMAT
============================================================

What Happened

Write 2-3 short sentences.

Start with:

"On {date}, ..."

Explain the main business change and what caused the largest
part of that change based on the available metrics.


Key Metrics

Show only the 3 most important metrics.

Use simple lines such as:

Revenue: down 61% from normal

Orders: down 60% from normal

Conversion Rate: down 61% from normal


Likely Reason

Write 2-3 short sentences.

Explain the most likely explanation supported by the numbers.

Do not claim a specific technical or operational cause unless
the data proves it.

Use normal metrics to explain what probably did NOT cause
the problem.


What to Investigate

Write 2-3 short sentences.

Give practical things the business team should check next.

Explain why those areas are worth checking.


============================================================
LANGUAGE STYLE
============================================================

Use very simple English.

Write like you are explaining the problem to a manager in a
30-second conversation.

Short sentences.

No complicated terminology.

No technical jargon.

No corporate buzzwords.

No unnecessary repetition.

No emojis.

No markdown symbols.

No bullet symbols.

No tables.

No mention of Python, Gemini, prompts, algorithms,
Z-scores, anomaly detection, or code.

Do not repeat the same idea in different words.

Be confident when the data is clear.

Be cautious when the cause is not proven.

Maximum 180 words.

Leave one blank line between sections.

"""


    # ========================================================
    # SEND REQUEST
    # ========================================================

    try:

        response = (
            client.models.generate_content(

                model="gemini-3.6-flash",

                contents=prompt

            )
        )

    except Exception as error:

        print("\n" + "=" * 80)
        print("❌ GEMINI API ERROR")
        print("=" * 80)
        print(f"Incident date: {date}")
        print(f"Error type: {type(error).__name__}")
        print(f"Error: {error}")
        print("=" * 80 + "\n")

        # IMPORTANT:
        # Do not silently return the old generic fallback.
        # If Gemini fails, expose the real error so we know
        # exactly what needs fixing.

        raise RuntimeError(
            f"Gemini API failed for {date}: {error}"
        ) from error


    # ========================================================
    # EMPTY RESPONSE
    # ========================================================

    if not response.text:

        raise RuntimeError(

            f"Gemini returned an empty response "
            f"for incident {date}"

        )


    return response.text.strip()


# ============================================================
# TEST
# ============================================================

if __name__ == "__main__":

    test_incident = {

        "date":
            "2026-06-15",

        "severity":
            "CRITICAL",

        "metrics": [

            {

                "metric":
                    "Revenue",

                "actual":
                    287227.71,

                "baseline":
                    986000.00,

                "change":
                    -71.39,

                "z_score":
                    -7.20,

                "status":
                    "ANOMALY"

            },

            {

                "metric":
                    "Orders",

                "actual":
                    147.00,

                "baseline":
                    504.00,

                "change":
                    -70.78,

                "z_score":
                    -8.00,

                "status":
                    "ANOMALY"

            },

            {

                "metric":
                    "Conversion_Rate",

                "actual":
                    1.50,

                "baseline":
                    4.90,

                "change":
                    -69.85,

                "z_score":
                    -8.50,

                "status":
                    "ANOMALY"

            }

        ],


        "all_results": [

            {

                "metric":
                    "Revenue",

                "actual":
                    287227.71,

                "baseline":
                    986000.00,

                "change":
                    -71.39,

                "status":
                    "ANOMALY"

            },

            {

                "metric":
                    "Orders",

                "actual":
                    147.00,

                "baseline":
                    504.00,

                "change":
                    -70.78,

                "status":
                    "ANOMALY"

            },

            {

                "metric":
                    "Conversion_Rate",

                "actual":
                    1.50,

                "baseline":
                    4.90,

                "change":
                    -69.85,

                "status":
                    "ANOMALY"

            },

            {

                "metric":
                    "Traffic",

                "actual":
                    9805.00,

                "baseline":
                    9853.71,

                "change":
                    -0.49,

                "status":
                    "NORMAL"

            },

            {

                "metric":
                    "Refunds",

                "actual":
                    16.00,

                "baseline":
                    18.71,

                "change":
                    -14.50,

                "status":
                    "NORMAL"

            },

            {

                "metric":
                    "Ad_Spend",

                "actual":
                    120204.83,

                "baseline":
                    117347.65,

                "change":
                    2.43,

                "status":
                    "NORMAL"

            },

            {

                "metric":
                    "Avg_Order_Value",

                "actual":
                    1953.93,

                "baseline":
                    1971.85,

                "change":
                    -0.91,

                "status":
                    "NORMAL"

            }

        ]

    }


    print(
        "\n" + "=" * 75
    )

    print(
        "INSIGHTGUARD AI EXPLAINER TEST"
    )

    print(
        "=" * 75
    )


    print(
        "\n" +
        generate_explanation(
            test_incident
        )
    )


    print(
        "\n" + "=" * 75
    )