# InsightGuard — AI-Powered Anomaly Detection Agent

> An end-to-end analytics and AI system that detects abnormal business patterns, explains **why they happened**, and recommends **what to investigate next**.

<p align="center">
  <img src="https://img.shields.io/badge/Python-3.x-blue?logo=python" alt="Python">
  <img src="https://img.shields.io/badge/Next.js-Frontend-black?logo=next.js" alt="Next.js">
  <img src="https://img.shields.io/badge/AI-Powered-Anomaly%20Analysis-purple" alt="AI Powered">
  <img src="https://img.shields.io/badge/Status-Active-success" alt="Status">
</p>

## Overview

**InsightGuard** is an AI-powered anomaly detection agent designed to go beyond simply identifying unusual data points.

Traditional anomaly detection systems can tell you:

> "Something unusual happened."

InsightGuard aims to answer:

> **"What happened, why did it happen, and what should I investigate next?"**

The system analyzes business data, identifies abnormal patterns, generates an AI-powered explanation, and provides investigation recommendations through an interactive web interface.

It can also communicate anomaly analysis through email notifications, making the system useful for automated monitoring workflows.

---

## Key Features

### 🔍 Anomaly Detection

Detects unusual patterns and deviations in business/data metrics.

* Identifies abnormal values and trends
* Compares observed behavior against expected patterns
* Highlights significant deviations
* Presents detected anomalies in an accessible interface

### 🤖 AI-Powered Analysis

Instead of stopping at anomaly detection, InsightGuard generates contextual analysis explaining the detected event.

The AI analysis focuses on:

* What changed
* How significant the change is
* Possible contributing factors
* Business impact
* Areas that require further investigation

### 🧭 Investigation Recommendations

InsightGuard provides actionable next steps instead of simply reporting an anomaly.

Example recommendations include:

* Investigate the affected metric
* Compare against historical periods
* Check related business dimensions
* Examine potential contributing factors
* Validate whether the anomaly represents a real business event

### 📊 Interactive Dashboard

The frontend provides a centralized interface for viewing:

* Detected anomalies
* Metric changes
* AI-generated explanations
* Investigation recommendations
* Relevant analytical information

### 📧 Automated Email Notifications

InsightGuard can send anomaly analysis through email so that important events can be communicated without requiring users to continuously monitor the dashboard.

---

## System Architecture

```text
                    ┌─────────────────────┐
                    │     Business Data   │
                    └──────────┬──────────┘
                               │
                               ▼
                    ┌─────────────────────┐
                    │  Anomaly Detection  │
                    │       Engine        │
                    └──────────┬──────────┘
                               │
                         Anomaly Found
                               │
                               ▼
                    ┌─────────────────────┐
                    │    AI Analysis      │
                    │      Engine         │
                    └──────────┬──────────┘
                               │
                ┌──────────────┴──────────────┐
                │                             │
                ▼                             ▼
       ┌─────────────────┐          ┌─────────────────┐
       │ Web Dashboard   │          │ Email Alerting  │
       └─────────────────┘          └─────────────────┘
                │
                ▼
       Investigation & Insights
```

---

## Project Structure

```text
InsightGuard/
│
├── backend/
│   ├── ...
│   └── Python anomaly/AI engine
│
├── frontend/
│   ├── ...
│   └── Next.js application
│
├── data/
│   └── Project datasets
│
├── README.md
└── .gitignore
```

> The exact files and modules may vary as the project evolves.

---

## Tech Stack

### Frontend

* Next.js
* React
* TypeScript
* Modern responsive UI

### Backend / AI Engine

* Python
* Data processing and anomaly analysis
* AI-powered reasoning and explanation
* REST/API integration

### Communication

* Email notification pipeline
* Backend-to-frontend integration

### Development Tools

* Git
* GitHub
* VS Code
* Vercel

---

## How It Works

### 1. Data Input

InsightGuard receives business or analytical data containing measurable metrics.

### 2. Anomaly Detection

The system analyzes the data and identifies significant deviations from expected behavior.

### 3. Context Generation

The detected anomaly is converted into meaningful analytical context, including the affected metric and relevant changes.

### 4. AI Investigation

The AI engine analyzes the anomaly and generates:

* An explanation
* Potential causes
* Business implications
* Recommended investigation steps

### 5. Visualization

The results are presented through the InsightGuard web dashboard.

### 6. Notification

The analysis can also be delivered through email, allowing users to receive anomaly insights without manually checking the dashboard.

---

## Example Workflow

```text
Metric changes significantly
          ↓
Anomaly detected
          ↓
Anomaly context generated
          ↓
AI analyzes the event
          ↓
Explanation generated
          ↓
Investigation steps recommended
          ↓
Dashboard updated
          ↓
Email notification sent
```

---

## Why InsightGuard?

Most anomaly detection systems focus primarily on **detection**.

InsightGuard focuses on the complete analytical workflow:

| Traditional Detection         | InsightGuard                                |
| ----------------------------- | ------------------------------------------- |
| Detects unusual values        | Detects unusual values                      |
| Reports anomalies             | Explains anomalies                          |
| Requires manual investigation | Suggests investigation paths                |
| Produces alerts               | Produces contextual analysis                |
| Focuses on detection          | Focuses on detection → explanation → action |

The goal is to reduce the time between **"something changed"** and **"we understand what to investigate."**

---

## Getting Started

### Prerequisites

Make sure the following are installed:

* Python 3.x
* Node.js
* npm
* Git

### Clone the repository

```bash
git clone https://github.com/kush-019/InsightGuard-AI-AGENT.git

cd InsightGuard-AI-AGENT
```

### Backend Setup

Navigate to the backend:

```bash
cd backend
```

Create a virtual environment:

```bash
python -m venv venv
```

Activate it on Windows:

```bash
venv\Scripts\activate
```

Install dependencies:

```bash
pip install -r requirements.txt
```

### Environment Variables

Create a `.env` file based on `.env.example`.

```env
AI_API_KEY=your_api_key_here
EMAIL_USERNAME=your_email_here
EMAIL_PASSWORD=your_email_app_password_here
```

> Never commit your `.env` file or API credentials to GitHub.

### Start the Backend

Use the backend startup command appropriate to the project configuration.

Example:

```bash
python app.py
```

### Frontend Setup

Open another terminal:

```bash
cd frontend
```

Install dependencies:

```bash
npm install
```

Start the development server:

```bash
npm run dev
```

Then open:

```text
http://localhost:3000
```

---

## Environment Variables

Sensitive configuration should be stored locally in `.env`.

A safe `.env.example` should contain placeholders only:

```env
AI_API_KEY=
EMAIL_USERNAME=
EMAIL_PASSWORD=
```

Never upload actual credentials.

---

## Screenshots

Add screenshots of the finished application here.

Recommended screenshots:

1. **Main InsightGuard dashboard**
2. **Detected anomaly**
3. **AI-generated analysis**
4. **Investigation recommendations**
5. **Email notification**

Example:

```markdown
## Dashboard

![InsightGuard Dashboard](docs/screenshots/dashboard.png)

## AI Analysis

![AI Analysis](docs/screenshots/ai-analysis.png)

## Email Alert

![Email Notification](docs/screenshots/email-alert.png)
```

---

## Deployment

The frontend is deployed using **Vercel**.

Live application:

**InsightGuard:**
https://insightguard-ai-agent.vercel.app/

> Backend availability depends on the configured deployment and environment.

---

## Future Improvements

Potential improvements include:

* [ ] Support for additional anomaly detection techniques
* [ ] More business metrics and datasets
* [ ] Historical anomaly tracking
* [ ] Anomaly severity scoring
* [ ] User authentication
* [ ] Configurable alert thresholds
* [ ] Additional notification channels
* [ ] Automated anomaly reports
* [ ] Improved AI investigation workflows
* [ ] Production monitoring and observability

---

## Project Goals

InsightGuard was built to explore the intersection of:

* Data Analytics
* Anomaly Detection
* Artificial Intelligence
* Business Intelligence
* Automated Monitoring
* Explainable Analytical Workflows

The project demonstrates how an analytical system can evolve from simply identifying abnormal data to providing **contextual explanations and actionable investigation guidance**.

---

## Author

**Kushagra Srivastava**

GitHub:
https://github.com/kush-019

---

## License

This project is licensed under the MIT License.

See `LICENSE` for more information.
