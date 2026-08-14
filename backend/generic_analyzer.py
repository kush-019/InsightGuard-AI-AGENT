import pandas as pd
import numpy as np


# ============================================================
# CONFIGURATION
# ============================================================

DEFAULT_BASELINE_PERIODS = 30

# Minimum robust deviation required
ANOMALY_Z_THRESHOLD = 4.0

# Minimum percentage movement
ANOMALY_CHANGE_THRESHOLD = 30.0

# Extreme anomaly rule
EXTREME_Z_THRESHOLD = 6.0
EXTREME_CHANGE_THRESHOLD = 50.0


# ============================================================
# CALCULATE ROBUST BASELINE
# ============================================================

def calculate_baseline(
    df,
    date_column,
    metric,
    target_date,
    baseline_periods=DEFAULT_BASELINE_PERIODS
):

    data = df.copy()

    data[date_column] = pd.to_datetime(
        data[date_column],
        errors="coerce"
    )

    data = data.dropna(
        subset=[date_column]
    )

    target_date = pd.to_datetime(
        target_date
    )

    historical_data = data[
        data[date_column] < target_date
    ].sort_values(
        date_column,
        ascending=False
    )

    baseline_data = historical_data.head(
        baseline_periods
    )

    baseline_values = pd.to_numeric(
        baseline_data[metric],
        errors="coerce"
    ).dropna()

    if len(baseline_values) < baseline_periods:

        return None

    # Median
    median = baseline_values.median()

    # Median Absolute Deviation
    absolute_deviations = (
        baseline_values - median
    ).abs()

    mad = absolute_deviations.median()

    # Standard deviation as fallback
    std = baseline_values.std(
        ddof=1
    )

    return {

        "median": median,

        "mad": mad,

        "std": std,

        "count": len(baseline_values)

    }


# ============================================================
# CALCULATE ROBUST Z-SCORE
# ============================================================

def calculate_robust_z_score(
    actual,
    median,
    mad,
    std
):

    # MAD-based robust Z-score
    if mad > 0:

        return (

            0.6745
            * (actual - median)
            / mad

        )

    # Fallback if MAD is zero
    if std > 0:

        return (
            (actual - median)
            / std
        )

    # Completely constant history
    if actual == median:

        return 0.0

    return float("inf")


# ============================================================
# CALCULATE PERCENTAGE CHANGE
# ============================================================

def calculate_percentage_change(
    actual,
    baseline
):

    if baseline == 0:

        return None

    return (

        (actual - baseline)
        / baseline

    ) * 100


# ============================================================
# CLASSIFY METRIC
# ============================================================

def classify_metric(
    robust_z,
    percentage_change
):

    if (
        robust_z is None
        or percentage_change is None
    ):

        return "UNKNOWN"

    absolute_z = abs(
        robust_z
    )

    absolute_change = abs(
        percentage_change
    )

    # --------------------------------------------------------
    # EXTREME ANOMALY
    # --------------------------------------------------------

    if (

        absolute_z >= EXTREME_Z_THRESHOLD

        and

        absolute_change >= EXTREME_CHANGE_THRESHOLD

    ):

        return "ANOMALY"


    # --------------------------------------------------------
    # REGULAR ANOMALY
    # --------------------------------------------------------

    if (

        absolute_z >= ANOMALY_Z_THRESHOLD

        and

        absolute_change >= ANOMALY_CHANGE_THRESHOLD

    ):

        return "ANOMALY"


    # --------------------------------------------------------
    # WATCH
    #
    # Statistically unusual but not strong enough
    # to call a true anomaly.
    # --------------------------------------------------------

    if absolute_z >= 2.5:

        return "WATCH"


    # --------------------------------------------------------
    # NORMAL
    # --------------------------------------------------------

    return "NORMAL"


# ============================================================
# ANALYZE SINGLE METRIC
# ============================================================

def analyze_metric(
    df,
    date_column,
    metric,
    target_date,
    baseline_periods=DEFAULT_BASELINE_PERIODS
):

    data = df.copy()

    # --------------------------------------------------------
    # Convert dates
    # --------------------------------------------------------

    data[date_column] = pd.to_datetime(
        data[date_column],
        errors="coerce"
    )

    data = data.dropna(
        subset=[date_column]
    )

    target_date = pd.to_datetime(
        target_date
    )

    # --------------------------------------------------------
    # Find target row
    # --------------------------------------------------------

    target_rows = data[
        data[date_column] == target_date
    ]

    if target_rows.empty:

        return {

            "metric": metric,

            "date": target_date,

            "actual": None,

            "baseline": None,

            "std": None,

            "z_score": None,

            "change": None,

            "status": "NO_DATA"

        }

    # --------------------------------------------------------
    # Get actual value
    # --------------------------------------------------------

    actual = pd.to_numeric(
        target_rows[metric].iloc[0],
        errors="coerce"
    )

    if pd.isna(actual):

        return {

            "metric": metric,

            "date": target_date,

            "actual": None,

            "baseline": None,

            "std": None,

            "z_score": None,

            "change": None,

            "status": "INVALID_DATA"

        }

    # --------------------------------------------------------
    # Calculate baseline
    # --------------------------------------------------------

    baseline_stats = calculate_baseline(

        df=data,

        date_column=date_column,

        metric=metric,

        target_date=target_date,

        baseline_periods=baseline_periods

    )

    # --------------------------------------------------------
    # Insufficient history
    # --------------------------------------------------------

    if baseline_stats is None:

        return {

            "metric": metric,

            "date": target_date,

            "actual": float(actual),

            "baseline": None,

            "std": None,

            "z_score": None,

            "change": None,

            "status": "INSUFFICIENT_HISTORY"

        }

    # --------------------------------------------------------
    # Statistics
    # --------------------------------------------------------

    median = baseline_stats["median"]

    mad = baseline_stats["mad"]

    std = baseline_stats["std"]

    # --------------------------------------------------------
    # Robust Z-score
    # --------------------------------------------------------

    robust_z = calculate_robust_z_score(

        actual=actual,

        median=median,

        mad=mad,

        std=std

    )

    # --------------------------------------------------------
    # Percentage change
    # --------------------------------------------------------

    percentage_change = (
        calculate_percentage_change(
            actual,
            median
        )
    )

    # --------------------------------------------------------
    # Classification
    # --------------------------------------------------------

    status = classify_metric(

        robust_z=robust_z,

        percentage_change=
            percentage_change

    )

    return {

        "metric": metric,

        "date": target_date,

        "actual": float(actual),

        "baseline": float(median),

        "std": float(std),

        "z_score": float(robust_z),

        "change": (

            float(percentage_change)

            if percentage_change is not None

            else None

        ),

        "status": status

    }


# ============================================================
# ANALYZE MULTIPLE METRICS
# ============================================================

def analyze_metrics(
    df,
    date_column,
    metrics,
    target_date,
    baseline_periods=DEFAULT_BASELINE_PERIODS
):

    results = []

    for metric in metrics:

        result = analyze_metric(

            df=df,

            date_column=date_column,

            metric=metric,

            target_date=target_date,

            baseline_periods=baseline_periods

        )

        results.append(
            result
        )

    return results


# ============================================================
# GET ANOMALIES
# ============================================================

def get_anomalies(
    results
):

    return [

        result

        for result in results

        if result["status"]
        == "ANOMALY"

    ]


# ============================================================
# TEST
# ============================================================

if __name__ == "__main__":

    df = pd.read_excel(
        "data/shopkart_daily_metrics.xlsx"
    )

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

    target_date = "2026-06-15"

    results = analyze_metrics(

        df=df,

        date_column=date_column,

        metrics=metrics,

        target_date=target_date,

        baseline_periods=30

    )

    print("\n" + "=" * 75)

    print(
        "INSIGHTGUARD BUSINESS-AWARE ANALYZER"
    )

    print("=" * 75)

    print(
        f"\nAnalysis Date: "
        f"{target_date}"
    )

    print(
        f"Baseline: "
        f"{DEFAULT_BASELINE_PERIODS} observations"
    )

    for result in results:

        print(
            "\n" + "-" * 75
        )

        print(
            f"Metric: "
            f"{result['metric']}"
        )

        if result["actual"] is not None:

            print(
                f"Actual: "
                f"{result['actual']:.2f}"
            )

        else:

            print(
                "Actual: N/A"
            )

        if result["baseline"] is not None:

            print(
                f"Baseline: "
                f"{result['baseline']:.2f}"
            )

        else:

            print(
                "Baseline: N/A"
            )

        if result["std"] is not None:

            print(
                f"Std Dev: "
                f"{result['std']:.2f}"
            )

        else:

            print(
                "Std Dev: N/A"
            )

        if result["z_score"] is not None:

            if np.isinf(
                result["z_score"]
            ):

                print(
                    "Robust Z-Score: INF"
                )

            else:

                print(
                    f"Robust Z-Score: "
                    f"{result['z_score']:.2f}"
                )

        else:

            print(
                "Robust Z-Score: N/A"
            )

        if result["change"] is not None:

            print(
                f"Change: "
                f"{result['change']:.2f}%"
            )

        else:

            print(
                "Change: N/A"
            )

        print(
            f"Status: "
            f"{result['status']}"
        )

    # --------------------------------------------------------
    # Anomalies
    # --------------------------------------------------------

    anomalies = get_anomalies(
        results
    )

    print(
        "\n" + "=" * 75
    )

    print(
        "ANOMALIES DETECTED"
    )

    print(
        "=" * 75
    )

    if anomalies:

        for anomaly in anomalies:

            z = anomaly["z_score"]

            if np.isinf(z):

                z_display = "INF"

            else:

                z_display = (
                    f"{z:.2f}"
                )

            print(

                f"🔴 "
                f"{anomaly['metric']} → "
                f"{anomaly['change']:.2f}% "
                f"(Robust Z={z_display})"

            )

    else:

        print(
            "✅ No anomalies detected."
        )