import pandas as pd

from generic_analyzer import analyze_metrics


# ============================================================
# CONFIGURATION
# ============================================================

BASELINE_PERIODS = 30

MAJOR_CHANGE_THRESHOLD = 50.0

CRITICAL_METRIC_COUNT = 3

HIGH_METRIC_COUNT = 2


# ============================================================
# DETERMINE INCIDENT SEVERITY
# ============================================================

def determine_severity(flagged_metrics):

    # --------------------------------------------------------
    # No anomaly
    # --------------------------------------------------------

    if not flagged_metrics:
        return "NORMAL"


    # --------------------------------------------------------
    # Number of anomalous metrics
    # --------------------------------------------------------

    anomaly_count = len(
        flagged_metrics
    )


    # --------------------------------------------------------
    # Percentage changes
    # --------------------------------------------------------

    changes = [

        abs(result["change"])

        for result in flagged_metrics

        if result["change"] is not None

    ]


    # --------------------------------------------------------
    # Largest percentage movement
    # --------------------------------------------------------

    largest_change = (

        max(changes)

        if changes

        else 0

    )


    # --------------------------------------------------------
    # Count major movements
    # --------------------------------------------------------

    major_metric_count = sum(

        1

        for result in flagged_metrics

        if (

            result["change"] is not None

            and

            abs(result["change"])
            >= MAJOR_CHANGE_THRESHOLD

        )

    )


    # ========================================================
    # CRITICAL
    # ========================================================

    # A very large anomaly
    # OR
    # multiple major anomalous metrics

    if largest_change >= 50:

        return "CRITICAL"


    if major_metric_count >= CRITICAL_METRIC_COUNT:

        return "CRITICAL"


    # ========================================================
    # HIGH
    # ========================================================

    if anomaly_count >= HIGH_METRIC_COUNT:

        return "HIGH"


    if largest_change >= 40:

        return "HIGH"


    # ========================================================
    # MEDIUM
    # ========================================================

    return "MEDIUM"


# ============================================================
# ANALYZE ENTIRE DATASET
# ============================================================

def analyze_historical_data(
    df,
    date_column,
    metrics,
    baseline_periods=BASELINE_PERIODS
):

    data = df.copy()


    # --------------------------------------------------------
    # Convert date column
    # --------------------------------------------------------

    data[date_column] = pd.to_datetime(
        data[date_column],
        errors="coerce"
    )


    # Remove invalid dates

    data = data.dropna(
        subset=[date_column]
    )


    # --------------------------------------------------------
    # Normalize dates
    # --------------------------------------------------------

    data[date_column] = (
        data[date_column]
        .dt.normalize()
    )


    # --------------------------------------------------------
    # Get unique dates
    # --------------------------------------------------------

    dates = sorted(
        data[date_column].unique()
    )


    historical_results = []


    # ========================================================
    # ANALYZE EACH DATE
    # ========================================================

    for date in dates:

        date_string = pd.Timestamp(
            date
        ).strftime(
            "%Y-%m-%d"
        )


        # ----------------------------------------------------
        # Analyze every metric
        # ----------------------------------------------------

        results = analyze_metrics(

            df=data,

            date_column=date_column,

            metrics=metrics,

            target_date=date_string,

            baseline_periods=baseline_periods

        )


        # ----------------------------------------------------
        # Keep ONLY true anomalies
        #
        # WATCH is not treated as an incident.
        # ----------------------------------------------------

        flagged_metrics = [

            result

            for result in results

            if result["status"] == "ANOMALY"

        ]


        # ----------------------------------------------------
        # Determine severity
        # ----------------------------------------------------

        severity = determine_severity(
            flagged_metrics
        )


        # ----------------------------------------------------
        # Create incident object
        # ----------------------------------------------------

        incident = {

            "date": date_string,

            "severity": severity,

            "metrics": flagged_metrics,

            "all_results": results

        }


        historical_results.append(
            incident
        )


    return historical_results


# ============================================================
# GET ALL INCIDENTS
# ============================================================

def get_incidents(
    historical_results
):

    return [

        result

        for result in historical_results

        if result["severity"] != "NORMAL"

    ]


# ============================================================
# GET CRITICAL INCIDENTS
# ============================================================

def get_critical_incidents(
    historical_results
):

    return [

        result

        for result in historical_results

        if result["severity"] == "CRITICAL"

    ]


# ============================================================
# GET HIGH INCIDENTS
# ============================================================

def get_high_incidents(
    historical_results
):

    return [

        result

        for result in historical_results

        if result["severity"] == "HIGH"

    ]


# ============================================================
# GET MEDIUM INCIDENTS
# ============================================================

def get_medium_incidents(
    historical_results
):

    return [

        result

        for result in historical_results

        if result["severity"] == "MEDIUM"

    ]


# ============================================================
# PRINT SINGLE INCIDENT
# ============================================================

def print_incident(
    incident
):

    print(
        f"\n{incident['date']} "
        f"→ {incident['severity']}"
    )


    for metric in incident["metrics"]:

        change = metric["change"]


        if change is not None:

            print(

                f"• "
                f"{metric['metric']}: "
                f"{change:.2f}% "
                f"(ANOMALY)"

            )


# ============================================================
# PRINT HISTORICAL SUMMARY
# ============================================================

def print_historical_summary(
    historical_results
):

    print(
        "\n" + "=" * 75
    )

    print(
        "INSIGHTGUARD HISTORICAL ANALYSIS"
    )

    print(
        "=" * 75
    )


    # --------------------------------------------------------
    # Get incident groups
    # --------------------------------------------------------

    total_dates = len(
        historical_results
    )


    incidents = get_incidents(
        historical_results
    )


    critical = get_critical_incidents(
        historical_results
    )


    high = get_high_incidents(
        historical_results
    )


    medium = get_medium_incidents(
        historical_results
    )


    # --------------------------------------------------------
    # Summary
    # --------------------------------------------------------

    print(
        f"\nDates analyzed: "
        f"{total_dates}"
    )


    print(
        f"Total incidents: "
        f"{len(incidents)}"
    )


    print(
        f"Critical incidents: "
        f"{len(critical)}"
    )


    print(
        f"High incidents: "
        f"{len(high)}"
    )


    print(
        f"Medium incidents: "
        f"{len(medium)}"
    )


    # ========================================================
    # PRIMARY INCIDENTS
    #
    # Only Critical + High
    # ========================================================

    primary_incidents = (

        critical + high

    )


    primary_incidents = sorted(

        primary_incidents,

        key=lambda x: x["date"]

    )


    print(
        "\n" + "=" * 75
    )

    print(
        "PRIMARY INCIDENTS"
    )

    print(
        "=" * 75
    )


    if not primary_incidents:

        print(
            "No critical or high incidents."
        )

    else:

        for incident in primary_incidents:

            print_incident(
                incident
            )


    # ========================================================
    # HIGH INCIDENTS
    # ========================================================

    print(
        "\n" + "=" * 75
    )

    print(
        "HIGH INCIDENTS"
    )

    print(
        "=" * 75
    )


    if not high:

        print(
            "No high incidents."
        )

    else:

        for incident in high:

            print_incident(
                incident
            )


    # ========================================================
    # MEDIUM INCIDENTS
    # ========================================================

    print(
        "\n" + "=" * 75
    )

    print(
        "MEDIUM INCIDENTS"
    )

    print(
        "=" * 75
    )


    if not medium:

        print(
            "No medium incidents."
        )

    else:

        print(

            f"{len(medium)} "
            f"medium incidents hidden "
            f"from the primary feed."

        )

        print(
            "These can be reviewed from "
            "the dashboard."
        )


# ============================================================
# TEST
# ============================================================

if __name__ == "__main__":

    # --------------------------------------------------------
    # Load dataset
    # --------------------------------------------------------

    df = pd.read_excel(
        "data/shopkart_daily_metrics.xlsx"
    )


    # --------------------------------------------------------
    # Temporary configuration
    # --------------------------------------------------------

    date_column = "Date"


    metrics = [

        "Revenue",

        "Orders",

        "Traffic",

        "Conversion_Rate",

        "Refunds",

        "Ad_Spend",

        "Avg_Order_Value"

    ]


    # --------------------------------------------------------
    # Run historical analysis
    # --------------------------------------------------------

    historical_results = (
        analyze_historical_data(

            df=df,

            date_column=date_column,

            metrics=metrics,

            baseline_periods=BASELINE_PERIODS

        )
    )


    # --------------------------------------------------------
    # Print results
    # --------------------------------------------------------

    print_historical_summary(
        historical_results
    )