from __future__ import annotations

import json
import os
import tempfile
import smtplib
from email.message import EmailMessage
from pathlib import Path
from typing import Any

import pandas as pd

from dotenv import load_dotenv

from fastapi import (
    FastAPI,
    File,
    HTTPException,
    UploadFile,
)

from fastapi.middleware.cors import CORSMiddleware

from pydantic import (
    BaseModel,
    EmailStr,
)

from data_profiler import profile_dataset

from historical_analyzer import (
    analyze_historical_data,
    get_critical_incidents,
)


# ============================================================
# CONFIGURATION
# ============================================================

BASE_DIR = Path(
    __file__
).resolve().parent


load_dotenv(
    BASE_DIR / ".env"
)


app = FastAPI(
    title="InsightGuard API",
    version="1.0.0",
)


FRONTEND_ORIGIN = os.getenv(
    "FRONTEND_ORIGIN",
    "http://localhost:3000",
)


# ============================================================
# CORS
# ============================================================

app.add_middleware(
    CORSMiddleware,

    allow_origins=[
        FRONTEND_ORIGIN,

        "http://localhost:3000",
        "http://127.0.0.1:3000",

        "http://localhost:3001",
        "http://127.0.0.1:3001",
    ],

    allow_credentials=True,

    allow_methods=["*"],

    allow_headers=["*"],
)


# ============================================================
# JSON SAFE
# ============================================================

def json_safe(
    value: Any
):

    if isinstance(
        value,
        pd.Timestamp
    ):
        return value.strftime(
            "%Y-%m-%d"
        )


    if hasattr(
        value,
        "item"
    ):

        try:
            return value.item()

        except Exception:
            pass


    if isinstance(
        value,
        dict
    ):

        return {
            str(key): json_safe(val)
            for key, val in value.items()
        }


    if isinstance(
        value,
        list
    ):

        return [
            json_safe(item)
            for item in value
        ]


    if isinstance(
        value,
        tuple
    ):

        return [
            json_safe(item)
            for item in value
        ]


    return value


# ============================================================
# METRIC SELECTION
# ============================================================

def choose_metrics(
    profile: dict
) -> list[str]:

    candidates = profile.get(
        "metric_candidates",
        [],
    )

    selected = []


    for candidate in candidates:

        classification = candidate.get(
            "classification",
            "",
        )

        score = float(
            candidate.get(
                "score",
                0,
            )
        )

        column = candidate.get(
            "column"
        )


        if (
            column
            and classification in {
                "RECOMMENDED",
                "POSSIBLE_METRIC",
            }
            and score >= 40
        ):

            selected.append(
                column
            )


    # --------------------------------------------------------
    # FALLBACK
    # --------------------------------------------------------

    if not selected:

        selected = list(
            profile.get(
                "numeric_columns",
                [],
            )
        )


    return list(
        dict.fromkeys(
            selected
        )
    )


# ============================================================
# INCIDENT FORMAT
# ============================================================

def summarize_incident_for_dashboard(
    incident: dict,
) -> dict:

    metrics = []

    for metric in incident.get(
        "metrics",
        [],
    ):

        metrics.append(
            {
                # Frontend expects "name"
                "name": metric.get(
                    "metric"
                ),

                "actual": metric.get(
                    "actual"
                ),

                "baseline": metric.get(
                    "baseline"
                ),

                "std": metric.get(
                    "std"
                ),

                "z_score": metric.get(
                    "z_score"
                ),

                "change": metric.get(
                    "change"
                ),

                "status": metric.get(
                    "status"
                ),
            }
        )


    # ========================================================
    # COMPLETE DATE SNAPSHOT
    # ========================================================
    #
    # This is extremely important.
    #
    # incident["metrics"] contains ONLY anomalies.
    #
    # incident["all_results"] contains EVERY metric for this
    # exact historical date.
    #
    # Gemini needs both.
    # ========================================================

    all_results = []

    for result in incident.get(
        "all_results",
        [],
    ):

        all_results.append(
            {
                "metric": result.get(
                    "metric"
                ),

                "actual": result.get(
                    "actual"
                ),

                "baseline": result.get(
                    "baseline"
                ),

                "std": result.get(
                    "std"
                ),

                "z_score": result.get(
                    "z_score"
                ),

                "change": result.get(
                    "change"
                ),

                "status": result.get(
                    "status"
                ),
            }
        )


    return {

        "date": incident.get(
            "date"
        ),

        "severity": incident.get(
            "severity"
        ),

        "metrics": metrics,

        "all_results": all_results,

    }

# ============================================================
# REQUEST MODELS
# ============================================================

class AIRequest(
    BaseModel
):

    incident: dict


class SendReportRequest(
    BaseModel
):

    email: EmailStr

    incidents: list[dict]


# ============================================================
# HEALTH CHECK
# ============================================================

@app.get(
    "/api/health"
)
def health():

    return {
        "status": "ok",
        "service": "InsightGuard API",
    }


# ============================================================
# ANALYZE DATASET
# ============================================================

@app.post(
    "/api/analyze"
)
async def analyze(
    file: UploadFile = File(...)
):

    filename = (
        file.filename
        or "dataset"
    )


    suffix = Path(
        filename
    ).suffix.lower()


    # --------------------------------------------------------
    # VALIDATE FILE
    # --------------------------------------------------------

    if suffix not in {
        ".xlsx",
        ".xls",
        ".csv",
    }:

        raise HTTPException(
            status_code=400,
            detail=(
                "Only .xlsx, .xls and "
                ".csv files are supported."
            ),
        )


    # --------------------------------------------------------
    # READ FILE
    # --------------------------------------------------------

    data = await file.read()


    if not data:

        raise HTTPException(
            status_code=400,
            detail="The uploaded file is empty.",
        )


    tmp_path = None


    try:

        # ----------------------------------------------------
        # SAVE TEMPORARY FILE
        # ----------------------------------------------------

        with tempfile.NamedTemporaryFile(
            delete=False,
            suffix=suffix,
        ) as tmp:

            tmp.write(data)

            tmp_path = Path(
                tmp.name
            )


        # ----------------------------------------------------
        # DATA PROFILER
        # ----------------------------------------------------

        profile = profile_dataset(
            str(tmp_path)
        )


        date_column = profile.get(
            "selected_date_column"
        )


        if not date_column:

            raise HTTPException(
                status_code=422,
                detail=(
                    "InsightGuard could not "
                    "identify a date/time column "
                    "in this dataset."
                ),
            )


        # ----------------------------------------------------
        # BUSINESS METRICS
        # ----------------------------------------------------

        metrics = choose_metrics(
            profile
        )


        if not metrics:

            raise HTTPException(
                status_code=422,
                detail=(
                    "InsightGuard could not "
                    "identify usable numeric "
                    "business metrics."
                ),
            )


        # ----------------------------------------------------
        # PREPARE DATAFRAME
        # ----------------------------------------------------

        df = profile[
            "dataframe"
        ].copy()


        df[date_column] = (
            pd.to_datetime(
                df[date_column],
                errors="coerce",
            )
            .dt.normalize()
        )


        df = (
            df
            .dropna(
                subset=[
                    date_column
                ]
            )
            .sort_values(
                date_column
            )
            .reset_index(
                drop=True
            )
        )


        if df.empty:

            raise HTTPException(
                status_code=422,
                detail=(
                    "No valid rows remain "
                    "after processing the "
                    "date column."
                ),
            )


        # ----------------------------------------------------
        # HISTORICAL ANALYSIS
        # ----------------------------------------------------

        historical = (
            analyze_historical_data(
                df=df,
                date_column=date_column,
                metrics=metrics,
                baseline_periods=30,
            )
        )


        # ----------------------------------------------------
        # CRITICAL INCIDENTS
        # ----------------------------------------------------

        critical = (
            get_critical_incidents(
                historical
            )
        )


        # ----------------------------------------------------
        # RESPONSE
        # ----------------------------------------------------

        response = {

            "dataset": {

                "name":
                    filename,

                "rows":
                    int(
                        profile["rows"]
                    ),

                "columns":
                    int(
                        profile["columns"]
                    ),

                "metrics":
                    metrics,

                "date_column":
                    date_column,

                "dates_analyzed":
                    int(
                        df[
                            date_column
                        ].nunique()
                    ),

                "date_range": [

                    df[
                        date_column
                    ]
                    .min()
                    .strftime(
                        "%Y-%m-%d"
                    ),

                    df[
                        date_column
                    ]
                    .max()
                    .strftime(
                        "%Y-%m-%d"
                    ),
                ],

                "frequency":
                    profile.get(
                        "frequency"
                    ),

                "missing_values":
                    int(
                        profile.get(
                            "missing_values",
                            0,
                        )
                    ),

                "duplicate_rows":
                    int(
                        profile.get(
                            "duplicate_rows",
                            0,
                        )
                    ),

                "missing_dates":
                    int(
                        profile.get(
                            "missing_dates",
                            0,
                        )
                    ),

                "warnings":
                    profile.get(
                        "data_quality_warnings",
                        [],
                    ),
            },


            "critical_incidents": [

                summarize_incident_for_dashboard(
                    incident
                )

                for incident in critical
            ],


            "all_incidents": [

                summarize_incident_for_dashboard(
                    incident
                )

                for incident in historical

                if incident.get(
                    "severity"
                ) != "NORMAL"
            ],
        }


        return json_safe(
            response
        )


    except HTTPException:

        raise


    except Exception as exc:

        raise HTTPException(
            status_code=500,
            detail=(
                f"Analysis failed: {exc}"
            ),
        ) from exc


    finally:

        if (
            tmp_path
            and tmp_path.exists()
        ):

            tmp_path.unlink(
                missing_ok=True
            )


# ============================================================
# GEMINI AI ANALYSIS
# ============================================================

@app.post(
    "/api/ai"
)
def incident_ai(
    request: AIRequest
):

    try:

        from ai_explainer import (
            generate_explanation
        )


        explanation = (
            generate_explanation(
                request.incident
            )
        )


        return {
            "explanation":
                explanation
        }


    except Exception as exc:

        raise HTTPException(
            status_code=500,
            detail=(
                f"AI analysis failed: {exc}"
            ),
        ) from exc


# ============================================================
# SEND CONSOLIDATED EMAIL
# ============================================================

@app.post(
    "/api/send-report"
)
def send_report(
    request: SendReportRequest
):

    # ========================================================
    # VALIDATE
    # ========================================================

    if not request.incidents:

        raise HTTPException(
            status_code=400,
            detail=(
                "There are no critical "
                "incidents to send."
            ),
        )


    # ========================================================
    # GMAIL SMTP CONFIGURATION
    # ========================================================
    #
    # Required .env values:
    #
    # SMTP_EMAIL=your_gmail@gmail.com
    # SMTP_PASSWORD=your_google_app_password
    # SMTP_HOST=smtp.gmail.com
    # SMTP_PORT=465
    #
    # SMTP_PASSWORD must be a Google App Password.
    # ========================================================

    smtp_email = os.getenv("SMTP_EMAIL")
    smtp_password = os.getenv("SMTP_PASSWORD")
    smtp_host = os.getenv("SMTP_HOST", "smtp.gmail.com")
    smtp_port = int(os.getenv("SMTP_PORT", "465"))

    if not smtp_email:
        raise HTTPException(
            status_code=500,
            detail="SMTP_EMAIL is not configured on the backend.",
        )

    if not smtp_password:
        raise HTTPException(
            status_code=500,
            detail=(
                "SMTP_PASSWORD is not configured on the backend. "
                "Use a Google App Password."
            ),
        )

    from_address = os.getenv(
        "SMTP_FROM_EMAIL",
        f"InsightGuard <{smtp_email}>",
    )

    # ========================================================
    # EMAIL HTML
    # ========================================================
    #
    # IMPORTANT:
    # The frontend sends ai_explanation for every incident.
    # This endpoint does NOT call Gemini again and does NOT
    # generate a generic fallback.
    #
    # Therefore the email contains the exact raw Gemini response
    # that the dashboard generated for each date.
    # ========================================================

    for incident in request.incidents:

        if not str(
            incident.get(
                "ai_explanation",
                ""
            )
        ).strip():

            date = incident.get(
                "date",
                "Unknown date"
            )

            raise HTTPException(
                status_code=422,
                detail=(
                    "AI analysis is missing for "
                    f"{date}. Please generate the "
                    "dashboard AI analysis before "
                    "sending the report."
                ),
            )


    try:

        from email_alert import (
            build_consolidated_email_html
        )

        email_html = (
            build_consolidated_email_html(
                request.incidents
            )
        )

    except HTTPException:
        raise

    except Exception as exc:

        raise HTTPException(
            status_code=500,
            detail=(
                "Email HTML generation failed: "
                f"{exc}"
            ),
        ) from exc


    # ========================================================
    # SEND THROUGH GMAIL SMTP
    # ========================================================

    count = len(request.incidents)

    incident_word = (
        "incident"
        if count == 1
        else "incidents"
    )

    subject = (
        "🔴 InsightGuard — "
        f"{count} Critical "
        f"{incident_word.title()}"
    )

    try:
        message = EmailMessage()

        message["From"] = from_address
        message["To"] = str(request.email)
        message["Subject"] = subject

        message.set_content(
            "InsightGuard consolidated critical incident report. "
            "Please open this email in an HTML-capable email client "
            "to view the full formatted report."
        )

        # Uses the existing email_alert.py HTML unchanged.
        message.add_alternative(
            email_html,
            subtype="html",
        )

        if smtp_port == 465:
            with smtplib.SMTP_SSL(
                smtp_host,
                smtp_port,
                timeout=30,
            ) as smtp:
                smtp.login(smtp_email, smtp_password)
                smtp.send_message(message)
        else:
            with smtplib.SMTP(
                smtp_host,
                smtp_port,
                timeout=30,
            ) as smtp:
                smtp.ehlo()
                smtp.starttls()
                smtp.ehlo()
                smtp.login(smtp_email, smtp_password)
                smtp.send_message(message)

        return {
            "sent": True,
            "recipient": str(request.email),
            "incidents": count,
            "message": (
                "Consolidated report "
                "sent successfully."
            ),
        }

    except smtplib.SMTPAuthenticationError:
        raise HTTPException(
            status_code=500,
            detail=(
                "Gmail authentication failed. "
                "Make sure SMTP_EMAIL is correct and "
                "SMTP_PASSWORD is a Google App Password, "
                "not your normal Gmail password."
            ),
        )

    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail=f"Email sending failed: {exc}",
        ) from exc



# ============================================================
# EMAIL ALIAS
# ============================================================

@app.post(
    "/api/send-email"
)
def send_email_alias(
    request: SendReportRequest
):

    return send_report(
        request
    )


# ============================================================
# RUN DIRECTLY
# ============================================================

if __name__ == "__main__":

    import uvicorn


    uvicorn.run(
        "app:app",

        host="127.0.0.1",

        port=8000,

        reload=True,
    )