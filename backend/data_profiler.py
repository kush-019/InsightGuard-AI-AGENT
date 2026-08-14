import pandas as pd


# ============================================================
# DETECT DATA FREQUENCY
# ============================================================

def detect_frequency(date_series):

    dates = pd.to_datetime(
        date_series,
        errors="coerce"
    )

    dates = (
        dates
        .dropna()
        .sort_values()
        .drop_duplicates()
    )

    if len(dates) < 3:
        return "INSUFFICIENT_DATA"

    differences = dates.diff().dropna()

    median_difference = differences.median()

    days = (
        median_difference.total_seconds()
        / 86400
    )

    if days <= 1.5:
        return "DAILY"

    elif days <= 10:
        return "WEEKLY"

    elif days <= 45:
        return "MONTHLY"

    elif days <= 120:
        return "QUARTERLY"

    else:
        return "IRREGULAR"


# ============================================================
# CHECK WHETHER VALUES LOOK LIKE REAL DATES
# ============================================================

def get_date_conversion(column):

    # Already a datetime column
    if pd.api.types.is_datetime64_any_dtype(column):

        return pd.to_datetime(
            column,
            errors="coerce"
        )

    # Numeric columns should not automatically
    # be treated as dates
    if pd.api.types.is_numeric_dtype(column):

        return None

    # Try converting text values
    converted = pd.to_datetime(
        column,
        errors="coerce"
    )

    valid_ratio = (
        converted.notna().mean()
    )

    if valid_ratio < 0.80:

        return None

    valid_dates = (
        converted
        .dropna()
    )

    if valid_dates.empty:

        return None

    # Reject unrealistic dates
    minimum_year = valid_dates.dt.year.min()
    maximum_year = valid_dates.dt.year.max()

    if minimum_year < 1900 or maximum_year > 2100:

        return None

    return converted


# ============================================================
# SCORE DATE COLUMN
# ============================================================

def score_date_column(df, column):

    score = 0

    column_name = str(column).lower()

    date_keywords = [
        "date",
        "time",
        "timestamp",
        "datetime",
        "day"
    ]

    if any(
        keyword in column_name
        for keyword in date_keywords
    ):

        score += 40

    converted = get_date_conversion(
        df[column]
    )

    if converted is None:

        return None

    valid_ratio = (
        converted.notna().mean()
    )

    score += 40

    unique_dates = (
        converted
        .dropna()
        .nunique()
    )

    if unique_dates >= 3:

        score += 20

    return {

        "column": column,

        "score": score,

        "valid_ratio": valid_ratio,

        "unique_dates": unique_dates

    }


# ============================================================
# SCORE NUMERIC BUSINESS METRIC
# ============================================================

def score_metric_column(df, column):

    score = 0

    column_name = str(column).lower()

    # --------------------------------------------------------
    # Numeric validation
    # --------------------------------------------------------

    if not pd.api.types.is_numeric_dtype(
        df[column]
    ):

        return None

    # --------------------------------------------------------
    # Numeric coverage
    # --------------------------------------------------------

    numeric_ratio = (
        pd.to_numeric(
            df[column],
            errors="coerce"
        )
        .notna()
        .mean()
    )

    if numeric_ratio >= 0.95:

        score += 20

    # --------------------------------------------------------
    # Business metric keywords
    # --------------------------------------------------------

    metric_keywords = [

        "revenue",
        "sales",
        "income",
        "profit",
        "loss",
        "orders",
        "order",
        "traffic",
        "visits",
        "sessions",
        "customers",
        "customer_count",
        "users",
        "transactions",
        "transaction",
        "conversion",
        "rate",
        "refund",
        "returns",
        "cost",
        "expense",
        "spend",
        "ad_spend",
        "price",
        "amount",
        "gmv",
        "aov",
        "average_order_value",
        "quantity",
        "units",
        "inventory",
        "balance",
        "growth",
        "margin",
        "roi"
    ]

    if any(
        keyword in column_name
        for keyword in metric_keywords
    ):

        score += 40

    # --------------------------------------------------------
    # Possible identifier detection
    # --------------------------------------------------------

    id_keywords = [

        "id",
        "code",
        "zip",
        "postal",
        "phone",
        "account_number",
        "customer_number",
        "reference"

    ]

    looks_like_id = any(

        keyword in column_name

        for keyword in id_keywords

    )

    if looks_like_id:

        score -= 60

    # --------------------------------------------------------
    # Unique-value analysis
    # --------------------------------------------------------

    unique_count = (
        df[column]
        .nunique()
    )

    total_rows = len(df)

    if total_rows > 0:

        unique_ratio = (
            unique_count
            / total_rows
        )

    else:

        unique_ratio = 0

    # A metric usually has repeated values
    if unique_ratio < 0.95:

        score += 20

    # A constant column isn't useful
    if unique_count > 1:

        score += 20

    # --------------------------------------------------------
    # Classification
    # --------------------------------------------------------

    if score >= 70:

        classification = "RECOMMENDED"

    elif score >= 40:

        classification = "POSSIBLE_METRIC"

    else:

        classification = "NOT_RECOMMENDED"

    return {

        "column": column,

        "score": score,

        "classification": classification,

        "unique_count": unique_count,

        "unique_ratio": unique_ratio

    }


# ============================================================
# DATA QUALITY CHECK
# ============================================================

def check_data_quality(
    df,
    selected_date_column=None
):

    warnings = []

    # --------------------------------------------------------
    # 1. Missing values
    # --------------------------------------------------------

    missing_by_column = (
        df.isnull().sum()
    )

    total_missing = int(
        missing_by_column.sum()
    )

    if total_missing > 0:

        warnings.append(
            f"{total_missing} missing value(s) detected."
        )

    # --------------------------------------------------------
    # 2. Duplicate rows
    # --------------------------------------------------------

    duplicate_rows = int(
        df.duplicated().sum()
    )

    if duplicate_rows > 0:

        warnings.append(
            f"{duplicate_rows} duplicate row(s) detected."
        )

    # --------------------------------------------------------
    # 3. Missing dates
    # --------------------------------------------------------

    missing_dates = 0

    if selected_date_column is not None:

        converted_dates = pd.to_datetime(
            df[selected_date_column],
            errors="coerce"
        )

        valid_dates = (
            converted_dates
            .dropna()
            .sort_values()
            .drop_duplicates()
        )

        if len(valid_dates) >= 3:

            differences = (
                valid_dates
                .diff()
                .dropna()
            )

            median_gap = (
                differences.median()
            )

            expected_days = (
                median_gap.total_seconds()
                / 86400
            )

            # Only check missing dates for data that
            # appears to have a regular frequency.

            if expected_days <= 1.5:

                expected_range = pd.date_range(
                    start=valid_dates.min(),
                    end=valid_dates.max(),
                    freq="D"
                )

                missing_dates = len(
                    expected_range
                    .difference(valid_dates)
                )

            elif expected_days <= 10:

                expected_range = pd.date_range(
                    start=valid_dates.min(),
                    end=valid_dates.max(),
                    freq="7D"
                )

                missing_dates = len(
                    expected_range
                    .difference(valid_dates)
                )

    if missing_dates > 0:

        warnings.append(
            f"{missing_dates} date(s) appear to be missing."
        )

    # --------------------------------------------------------
    # 4. Too little historical data
    # --------------------------------------------------------

    if selected_date_column is not None:

        unique_dates = (
            pd.to_datetime(
                df[selected_date_column],
                errors="coerce"
            )
            .dropna()
            .nunique()
        )

        if unique_dates < 7:

            warnings.append(
                "Less than 7 unique dates are available. "
                "Historical anomaly detection may be unreliable."
            )

    # --------------------------------------------------------
    # Return results
    # --------------------------------------------------------

    return {

        "warnings": warnings,

        "total_missing": total_missing,

        "duplicate_rows": duplicate_rows,

        "missing_dates": missing_dates

    }


# ============================================================
# DATA PROFILER
# ============================================================

def profile_dataset(file_path):

    print("\n" + "=" * 65)
    print("INSIGHTGUARD DATA PROFILER")
    print("=" * 65)

    # ========================================================
    # 1. LOAD FILE
    # ========================================================

    print("\nLoading dataset...")

    if file_path.lower().endswith(".csv"):

        df = pd.read_csv(file_path)

    elif file_path.lower().endswith(
        (".xlsx", ".xls")
    ):

        df = pd.read_excel(file_path)

    else:

        raise ValueError(
            "Unsupported file format. "
            "Please use CSV or Excel."
        )

    print("✅ Dataset loaded.")

    # ========================================================
    # 2. BASIC INFORMATION
    # ========================================================

    rows = len(df)

    columns = len(df.columns)

    print("\nDATASET INFORMATION")
    print("-" * 65)

    print(f"Rows: {rows}")
    print(f"Columns: {columns}")

    # ========================================================
    # 3. COLUMN INFORMATION
    # ========================================================

    print("\nCOLUMNS")
    print("-" * 65)

    for column in df.columns:

        print(
            f"{column} → "
            f"{df[column].dtype}"
        )

    # ========================================================
    # 4. DATE COLUMN DETECTION
    # ========================================================

    date_candidates = []

    for column in df.columns:

        candidate = score_date_column(
            df,
            column
        )

        if candidate is not None:

            date_candidates.append(
                candidate
            )

    date_candidates.sort(
        key=lambda x: x["score"],
        reverse=True
    )

    date_columns = [

        candidate["column"]

        for candidate
        in date_candidates

    ]

    print("\nPOSSIBLE DATE COLUMNS")
    print("-" * 65)

    if date_candidates:

        for candidate in date_candidates:

            print(
                f"📅 {candidate['column']} "
                f"(confidence: "
                f"{candidate['score']}%)"
            )

    else:

        print(
            "❌ No date column detected."
        )

    # ========================================================
    # 5. NUMERIC COLUMNS
    # ========================================================

    numeric_columns = (

        df
        .select_dtypes(
            include="number"
        )
        .columns
        .tolist()

    )

    print("\nNUMERIC COLUMNS")
    print("-" * 65)

    if numeric_columns:

        for column in numeric_columns:

            print(
                f"📊 {column}"
            )

    else:

        print(
            "❌ No numeric columns detected."
        )

    # ========================================================
    # 6. BUSINESS METRIC ANALYSIS
    # ========================================================

    metric_candidates = []

    for column in numeric_columns:

        candidate = score_metric_column(
            df,
            column
        )

        if candidate is not None:

            metric_candidates.append(
                candidate
            )

    metric_candidates.sort(
        key=lambda x: x["score"],
        reverse=True
    )

    print("\nBUSINESS METRIC ANALYSIS")
    print("-" * 65)

    if metric_candidates:

        for candidate in metric_candidates:

            print(
                f"📊 {candidate['column']} "
                f"→ "
                f"{candidate['classification']} "
                f"({candidate['score']})"
            )

    else:

        print(
            "❌ No numeric metrics found."
        )

    # ========================================================
    # 7. SELECT DATE COLUMN
    # ========================================================

    selected_date_column = None

    date_range = None

    frequency = None

    if date_columns:

        selected_date_column = (
            date_columns[0]
        )

        converted_dates = (
            get_date_conversion(
                df[selected_date_column]
            )
        )

        if converted_dates is not None:

            valid_dates = (
                converted_dates
                .dropna()
            )

            if not valid_dates.empty:

                minimum_date = (
                    valid_dates.min()
                )

                maximum_date = (
                    valid_dates.max()
                )

                date_range = (
                    minimum_date,
                    maximum_date
                )

                print(
                    "\nSELECTED DATE COLUMN"
                )

                print("-" * 65)

                print(
                    f"📅 "
                    f"{selected_date_column}"
                )

                print("\nDATE RANGE")

                print("-" * 65)

                print(
                    f"Start: "
                    f"{minimum_date.strftime('%Y-%m-%d')}"
                )

                print(
                    f"End: "
                    f"{maximum_date.strftime('%Y-%m-%d')}"
                )

                frequency = (
                    detect_frequency(
                        valid_dates
                    )
                )

                print(
                    "\nDATA FREQUENCY"
                )

                print("-" * 65)

                print(
                    f"Detected frequency: "
                    f"{frequency}"
                )

    else:

        print("\nDATE RANGE")

        print("-" * 65)

        print(
            "❌ Cannot determine date range "
            "without a date column."
        )

    # ========================================================
    # 8. DATA QUALITY
    # ========================================================

    quality = check_data_quality(
        df,
        selected_date_column
    )

    print("\nDATA QUALITY")
    print("-" * 65)

    print(
        f"Total missing values: "
        f"{quality['total_missing']}"
    )

    print(
        f"Duplicate rows: "
        f"{quality['duplicate_rows']}"
    )

    print(
        f"Missing dates: "
        f"{quality['missing_dates']}"
    )

    # ========================================================
    # 9. WARNINGS
    # ========================================================

    print("\nDATA QUALITY WARNINGS")
    print("-" * 65)

    if quality["warnings"]:

        for warning in quality["warnings"]:

            print(
                f"⚠️ {warning}"
            )

    else:

        print(
            "✅ No major data quality issues detected."
        )

    # ========================================================
    # 10. RETURN PROFILE
    # ========================================================

    return {

        "dataframe": df,

        "rows": rows,

        "columns": columns,

        "date_columns": date_columns,

        "selected_date_column":
            selected_date_column,

        "numeric_columns":
            numeric_columns,

        "metric_candidates":
            metric_candidates,

        "missing_values":
            quality["total_missing"],

        "duplicate_rows":
            quality["duplicate_rows"],

        "missing_dates":
            quality["missing_dates"],

        "data_quality_warnings":
            quality["warnings"],

        "date_range":
            date_range,

        "frequency":
            frequency

    }


# ============================================================
# TEST
# ============================================================

if __name__ == "__main__":

    
    profile = profile_dataset(
    "data/insightguard_manufacturing_test.xlsx"
)

    print("\n" + "=" * 65)
    print("PROFILE COMPLETE")
    print("=" * 65)