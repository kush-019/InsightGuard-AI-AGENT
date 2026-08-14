"use client";

import { useMemo, useRef, useState } from "react";
import {
  Activity,
  AlertTriangle,
  BarChart3,
  Bell,
  CalendarDays,
  Check,
  ChevronDown,
  Database,
  FileSpreadsheet,
  LayoutDashboard,
  Mail,
  Menu,
  RefreshCw,
  Send,
  Shield,
  Sparkles,
  TrendingUp,
  UploadCloud,
  X,
} from "lucide-react";

type Metric = {
  std: any;
  name: string;
  actual: number | null;
  baseline: number | null;
  z_score: number | null;
  change: number | null;
  status: string;
};

type Incident = {
  date: string;
  severity: string;
  metrics: Metric[];

  all_results?: {
    metric?: string;
    name?: string;
    actual: number | null;
    baseline: number | null;
    std?: number | null;
    z_score?: number | null;
    change: number | null;
    status: string;
  }[];
};

type Analysis = {
  dataset: {
    name: string;
    rows: number;
    columns: number;
    metrics: string[];
    dates_analyzed: number;
    date_range: [string, string];
    frequency: string | null;
    missing_values: number;
    duplicate_rows: number;
    missing_dates: number;
    warnings: string[];
  };

  critical_incidents: Incident[];
  all_incidents: Incident[];
};

type AI = {
  whatHappened: string;
  keyMetrics: string;
  likelyReason: string;
  investigate: string;
};

const API = (
  process.env.NEXT_PUBLIC_API_URL ||
  "http://127.0.0.1:8000"
).replace(/\/$/, "");


/* ============================================================
   DATE FUNCTIONS
============================================================ */

function prettyDate(s: string) {
  const d = new Date(`${s}T00:00:00`);

  const day = d.getDate();

  const m = d.toLocaleString("en-IN", {
    month: "long",
  });

  const y = d.getFullYear();

  let x = "th";

  if (day % 100 < 11 || day % 100 > 13) {
    if (day % 10 === 1) x = "st";
    else if (day % 10 === 2) x = "nd";
    else if (day % 10 === 3) x = "rd";
  }

  return `${day}${x} ${m} ${y}`;
}

function shortDate(s: string) {
  const d = new Date(`${s}T00:00:00`);

  return `${String(
    d.getDate()
  ).padStart(2, "0")}/${String(
    d.getMonth() + 1
  ).padStart(2, "0")}/${d.getFullYear()}`;
}


/* ============================================================
   AI PARSER
============================================================ */

function parseAI(text: string): AI {
  const r: AI = {
    whatHappened: "",
    keyMetrics: "",
    likelyReason: "",
    investigate: "",
  };

  const map: [string, keyof AI][] = [
    ["What Happened", "whatHappened"],
    ["Key Metrics", "keyMetrics"],
    ["Likely Reason", "likelyReason"],
    ["What to Investigate", "investigate"],
  ];

  let cur: keyof AI | null = null;

  for (const raw of text.split("\n")) {
    const line = raw
      .trim()
      .replace(/^#{1,6}\s*/, "")
      .replace(/:$/, "")
      .trim();

    if (!line) continue;

    const h = map.find(
      ([x]) =>
        x.toLowerCase() ===
        line.toLowerCase()
    );

    if (h) {
      cur = h[1];
      continue;
    }

    if (cur) {
      r[cur] = r[cur]
        ? `${r[cur]} ${line}`
        : line;
    }
  }

  return r;
}


/* ============================================================
   MAIN PAGE
============================================================ */

export default function Home() {

  const input =
    useRef<HTMLInputElement>(null);

  const [file, setFile] =
    useState<File | null>(null);

  const [analysis, setAnalysis] =
    useState<Analysis | null>(null);

  const [selectedDate, setSelectedDate] =
    useState("");

  const [email, setEmail] =
    useState("");

  const [busy, setBusy] =
    useState(false);

  const [aiBusy, setAiBusy] =
    useState(false);

  const [sending, setSending] =
    useState(false);

  const [sent, setSent] =
    useState(false);

  const [ai, setAi] =
    useState<AI | null>(null);

  /*
   * Exact raw Gemini response cached per incident date.
   *
   * The same cached response is used by the dashboard
   * and by the email.
   */
  const [aiExplanations, setAiExplanations] =
    useState<Record<string, string>>({});

  const [error, setError] =
    useState("");

  const [mobile, setMobile] =
    useState(false);


  /* ==========================================================
     CURRENT INCIDENTS
  ========================================================== */

  const critical =
    analysis?.critical_incidents || [];

  const selected = useMemo(
    () =>
      critical.find(
        (x) =>
          x.date === selectedDate
      ) ||
      critical[0] ||
      null,
    [
      critical,
      selectedDate,
    ]
  );


  /* ==========================================================
     FILE PICKER
  ========================================================== */

  const pick = () =>
    input.current?.click();


  /* ==========================================================
     CHOOSE FILE
  ========================================================== */

  const choose = (f?: File) => {

    if (!f) return;

    if (
      !/\.(xlsx|xls|csv)$/i.test(
        f.name
      )
    ) {

      setError(
        "Please upload an Excel (.xlsx/.xls) or CSV file."
      );

      return;
    }

    setFile(f);

    setAnalysis(null);

    setSelectedDate("");

    setAi(null);

    setAiExplanations({});

    setSent(false);

    setError("");
  };


  /* ==========================================================
     ANALYZE DATASET
  ========================================================== */

  async function analyze() {

    if (!file) {
      pick();
      return;
    }

    setBusy(true);

    setError("");

    setAi(null);

    setAiExplanations({});

    try {

      const fd = new FormData();

      fd.append(
        "file",
        file
      );

      const res =
        await fetch(
          `${API}/api/analyze`,
          {
            method: "POST",
            body: fd,
          }
        );

      const data =
        await res.json();

      if (!res.ok) {

        throw new Error(
          data.detail ||
          "Analysis failed."
        );
      }

      setAnalysis(data);

      const first =
        data.critical_incidents?.[0];

      setSelectedDate(
        first?.date || ""
      );

      /*
       * Generate AI only for the first critical date.
       * Other dates are generated when selected.
       */
      if (first) {
        await getAI(first);
      }

    } catch (e) {

      setError(
        e instanceof Error
          ? e.message
          : "Analysis failed."
      );

    } finally {

      setBusy(false);

    }
  }


  /* ==========================================================
     GEMINI AI
  ========================================================== */

  async function getAI(
    incident: Incident
  ) {

    /*
     * If this date already has a Gemini response,
     * use the cached response instead of calling Gemini again.
     */

    const cached =
      aiExplanations[
        incident.date
      ];

    if (cached) {

      setAi(
        parseAI(
          cached
        )
      );

      return;
    }

    setAiBusy(true);

    setAi(null);

    setError("");

    try {

      const allResults = (
        incident.all_results || []
      ).map(
        (m) => ({
          metric:
            m.metric ??
            m.name ??
            "Unknown Metric",

          actual:
            m.actual,

          baseline:
            m.baseline,

          std:
            m.std ??
            null,

          z_score:
            m.z_score ??
            null,

          change:
            m.change,

          status:
            m.status,
        })
      );

      const anomalyResults =
        incident.metrics.map(
          (m) => ({
            metric:
              m.name,

            actual:
              m.actual,

            baseline:
              m.baseline,

            std:
              m.std ??
              null,

            z_score:
              m.z_score ??
              null,

            change:
              m.change,

            status:
              m.status,
          })
        );

      const payload = {
        incident: {
          date:
            incident.date,

          severity:
            incident.severity,

          metrics:
            anomalyResults,

          all_results:
            allResults,
        },
      };

      console.log(
        "[InsightGuard] AI incident date:",
        incident.date
      );

      console.log(
        "[InsightGuard] AI anomalies:",
        anomalyResults
      );

      console.log(
        "[InsightGuard] AI complete date snapshot:",
        allResults
      );

      console.log(
        "[InsightGuard] AI final payload:",
        payload
      );

      const res =
        await fetch(
          `${API}/api/ai`,
          {
            method:
              "POST",

            headers: {
              "Content-Type":
                "application/json",
            },

            body:
              JSON.stringify(
                payload
              ),
          }
        );

      const data =
        await res.json();

      if (!res.ok) {

        throw new Error(
          data.detail ||
          "AI analysis failed."
        );
      }

      if (!data.explanation) {

        throw new Error(
          "Gemini returned an empty analysis."
        );
      }

      const explanation =
        data.explanation;

      console.log(
        "[InsightGuard] Gemini explanation:",
        explanation
      );

      /*
       * Cache the exact raw Gemini response.
       */
      setAiExplanations(
        (prev) => ({
          ...prev,
          [incident.date]:
            explanation,
        })
      );

      /*
       * Display the exact same response
       * on the dashboard.
       */
      setAi(
        parseAI(
          explanation
        )
      );

    } catch (e) {

      setError(
        e instanceof Error
          ? e.message
          : "AI analysis failed."
      );

    } finally {

      setAiBusy(false);

    }
  }


  /* ==========================================================
     SELECT DATE
  ========================================================== */

  async function selectDate(
    d: string
  ) {

    setSelectedDate(d);

    setSent(false);

    setAi(null);

    setError("");

    const incident =
      critical.find(
        (x) =>
          x.date === d
      );

    if (!incident) {
      return;
    }

    /*
     * Use cached Gemini response if available.
     */
    const cached =
      aiExplanations[
        incident.date
      ];

    if (cached) {

      setAi(
        parseAI(
          cached
        )
      );

      return;
    }

    /*
     * Only the first selection of a date
     * calls Gemini.
     */
    await getAI(
      incident
    );
  }


  /* ==========================================================
     SEND REPORT
  ========================================================== */

  async function sendReport() {

    if (
      !email ||
      !email.includes("@")
    ) {

      setError(
        "Enter a valid email address."
      );

      return;
    }

    if (!critical.length) {

      setError(
        "There are no critical incidents to send."
      );

      return;
    }

    /*
     * IMPORTANT:
     *
     * There is NO Gemini call here.
     *
     * The email uses only the AI explanations
     * already generated by the dashboard.
     */

    const missingDates =
      critical
        .filter(
          (incident) =>
            !aiExplanations[
              incident.date
            ]
        )
        .map(
          (incident) =>
            incident.date
        );

    /*
     * Do not generate missing AI reports here.
     * This keeps email sending fast.
     */
    if (
      missingDates.length > 0
    ) {

      setError(
        `AI analysis is missing for ${missingDates
          .map(shortDate)
          .join(", ")}. Select each critical date once to generate its analysis, then send the report.`
      );

      return;
    }

    setSending(true);

    setError("");

    try {

      /*
       * Attach the EXACT Gemini response already
       * displayed on the dashboard to each incident.
       */

      const incidentsWithAI =
        critical.map(
          (incident) => ({
            ...incident,

            ai_explanation:
              aiExplanations[
                incident.date
              ],
          })
        );

      /*
       * Only one request is made here:
       *
       * Frontend → /api/send-report → Resend
       *
       * No Gemini request.
       */

      const res =
        await fetch(
          `${API}/api/send-report`,
          {
            method:
              "POST",

            headers: {
              "Content-Type":
                "application/json",
            },

            body:
              JSON.stringify({
                email,

                incidents:
                  incidentsWithAI,
              }),
          }
        );

      const data =
        await res.json();

      if (!res.ok) {

        throw new Error(
          data.detail ||
          "Email sending failed."
        );
      }

      setSent(true);

    } catch (e) {

      setError(
        e instanceof Error
          ? e.message
          : "Email sending failed."
      );

    } finally {

      setSending(false);

    }
  }


  /* ==========================================================
     NAVIGATION
  ========================================================== */

  const go = (id: string) => {

    setMobile(false);

    document
      .getElementById(id)
      ?.scrollIntoView({
        behavior:
          "smooth",
      });
  };


  /* ==========================================================
     UI
  ========================================================== */

  return (

    <div className="min-h-screen bg-[#030303] text-white">

      <input
        ref={input}
        type="file"
        accept=".xlsx,.xls,.csv"
        className="hidden"
        onChange={(e) =>
          choose(
            e.target.files?.[0]
          )
        }
      />

      {error && (

        <div className="fixed right-5 top-5 z-[100] max-w-md rounded-xl border border-red-900 bg-[#160606] p-4 text-sm text-red-300 shadow-2xl">

          <div className="flex gap-3">

            <AlertTriangle
              size={18}
            />

            <span className="flex-1">
              {error}
            </span>

            <button
              onClick={() =>
                setError("")
              }
            >
              <X size={16} />
            </button>

          </div>

        </div>

      )}

      <div className="flex min-h-screen">

        <Sidebar
          mobile={mobile}
          close={() =>
            setMobile(false)
          }
          go={go}
          upload={pick}
        />

        <main className="min-w-0 flex-1 lg:ml-[260px]">

          <header className="sticky top-0 z-30 flex h-[86px] items-center border-b border-[#1c1c1c] bg-[#030303]/95 px-4 backdrop-blur sm:px-6">

            <button
              onClick={() =>
                setMobile(true)
              }
              className="lg:hidden"
            >
              <Menu />
            </button>

            <div className="ml-5 text-sm text-neutral-300">

              AI-Powered Anomaly Detection. Actionable Insights.

            </div>

            <div className="ml-auto flex items-center gap-4">

              <Bell size={21} />

              <div className="hidden h-7 w-px bg-[#252525] sm:block" />

              <div className="grid h-10 w-10 place-items-center rounded-full bg-red-700 text-sm font-bold">

                IG

              </div>

              <div className="hidden sm:block">

                <div className="text-xs font-semibold">

                  InsightGuard

                </div>

                <div className="text-[11px] text-neutral-500">

                  Admin

                </div>

              </div>

            </div>

          </header>

          <div className="mx-auto max-w-[1500px] space-y-5 p-4 sm:p-6">

            <section
              id="dashboard"
              className="scroll-mt-24"
            >

              <div className="grid gap-4 xl:grid-cols-4">

                <Stat
                  title="Total Rows"
                  value={
                    analysis
                      ? String(
                          analysis.dataset.rows
                        )
                      : "—"
                  }
                  sub="Total data points"
                  icon={<Database />}
                />

                <Stat
                  title="Metrics Detected"
                  value={
                    analysis
                      ? String(
                          analysis.dataset.metrics.length
                        )
                      : "—"
                  }
                  sub="Numeric business metrics"
                  icon={<TrendingUp />}
                />

                <Stat
                  title="Dates Analyzed"
                  value={
                    analysis
                      ? String(
                          analysis.dataset.dates_analyzed
                        )
                      : "—"
                  }
                  sub={
                    analysis
                      ? `${shortDate(
                          analysis.dataset.date_range[0]
                        )} to ${shortDate(
                          analysis.dataset.date_range[1]
                        )}`
                      : "Upload a dataset to begin"
                  }
                  icon={<CalendarDays />}
                />

                <Stat
                  title="Critical Dates"
                  value={
                    analysis
                      ? String(
                          critical.length
                        )
                      : "—"
                  }
                  sub="Require immediate attention"
                  icon={<AlertTriangle />}
                  danger
                />

              </div>

            </section>

            <div className="grid gap-4 lg:grid-cols-2">

              <Quick
                onUpload={pick}
                onAnalyze={analyze}
                loading={busy}
              />

              <Last
                file={
                  analysis?.dataset.name ||
                  file?.name ||
                  "No dataset analyzed yet"
                }
                upload={pick}
              />

            </div>

            {!analysis ? (

              <Empty
                upload={pick}
              />

            ) : (

              <>

                <section
                  id="timeline"
                  className="grid scroll-mt-24 gap-5 xl:grid-cols-[1.45fr_1fr]"
                >

                  <Timeline
                    incidents={critical}
                    selected={selectedDate}
                    choose={selectDate}
                  />

                  <Selected
                    incident={selected}
                    email={email}
                    setEmail={setEmail}
                  />

                </section>

                <section
                  id="metrics"
                  className="grid scroll-mt-24 gap-5 xl:grid-cols-[1fr_1fr_1.05fr]"
                >

                  <Metrics
                    incident={selected}
                  />

                  <AIBox
                    incident={selected}
                    ai={ai}
                    busy={aiBusy}
                  />

                  <Insights
                    ai={ai}
                    busy={aiBusy}
                  />

                </section>

                <section
                  id="report"
                  className="scroll-mt-24"
                >

                  <Report
                    email={email}
                    sent={sent}
                    sending={sending}
                    ready={
                      critical.length >
                      0
                    }
                    send={sendReport}
                  />

                </section>

              </>

            )}

            {/* ==================================================
                FOOTER
            ================================================== */}

            <footer className="border-t border-[#1c1c1c] pt-5">

              <div className="flex items-end justify-between gap-4">

                <span className="flex items-center gap-2 text-xs text-neutral-600">

                  <Shield
                    size={16}
                    className="text-red-600"
                  />

                  InsightGuard is monitoring
                  your data 24/7 to keep your
                  business safe.

                </span>

                <span className="shrink-0 text-xs font-semibold text-neutral-500">

                  By Kushagra Srivastava

                </span>

              </div>

            </footer>

          </div>

        </main>

      </div>

    </div>

  );
}


/* ============================================================
   SIDEBAR
============================================================ */

function Sidebar({
  mobile,
  close,
  go,
  upload,
}: {
  mobile: boolean;
  close: () => void;
  go: (id: string) => void;
  upload: () => void;
}) {

  return (

    <>

      <div
        className={`${
          mobile
            ? "fixed"
            : "hidden"
        } inset-0 z-40 bg-black/70 lg:hidden`}
        onClick={close}
      />

      <aside
        className={`fixed inset-y-0 left-0 z-50 w-[260px] border-r border-[#1d1d1d] bg-[#050505] p-4 transition-transform lg:translate-x-0 ${
          mobile
            ? "translate-x-0"
            : "-translate-x-full"
        }`}
      >

        <div className="flex items-center gap-3">

          <div className="grid h-12 w-12 place-items-center rounded-xl bg-gradient-to-br from-red-700 to-red-950">

            <Shield
              size={28}
            />

          </div>

          <div>

            <div className="text-xl font-bold">

              Insight

              <span className="text-red-600">

                Guard

              </span>

            </div>

            <div className="text-[11px] text-neutral-500">

              AI Anomaly Agent

            </div>

          </div>

          <button
            className="ml-auto lg:hidden"
            onClick={close}
          >
            <X size={18} />
          </button>

        </div>

        <nav className="mt-8 space-y-1">

          <Nav
            icon={<LayoutDashboard />}
            text="Dashboard"
            active
            click={() =>
              go("dashboard")
            }
          />

          <Nav
            icon={<UploadCloud />}
            text="Upload Dataset"
            click={upload}
          />

          <Nav
            icon={<FileSpreadsheet />}
            text="Anomaly Reports"
            click={() =>
              go("timeline")
            }
          />

          <Nav
            icon={<Bell />}
            text="Alert History"
            click={() =>
              go("timeline")
            }
          />

          <Nav
            icon={<BarChart3 />}
            text="Metrics Overview"
            click={() =>
              go("metrics")
            }
          />

        </nav>

        <div className="absolute bottom-5 left-4 right-4">

          <div className="rounded-xl border border-[#292929] bg-[#0a0a0a] p-4">

            <b>
              System Status
            </b>

            <div className="mt-3 flex items-center gap-2 text-xs text-neutral-400">

              <span className="h-2.5 w-2.5 rounded-full bg-emerald-500" />

              All systems operational

            </div>

          </div>

        </div>

      </aside>

    </>

  );
}


/* ============================================================
   NAVIGATION ITEM
============================================================ */

function Nav({
  icon,
  text,
  active,
  click,
}: {
  icon: React.ReactNode;
  text: string;
  active?: boolean;
  click: () => void;
}) {

  return (

    <button
      onClick={click}
      className={`flex w-full items-center gap-4 rounded-lg px-3 py-3 text-sm ${
        active
          ? "bg-red-700 text-white"
          : "text-neutral-400 hover:bg-white/[.03] hover:text-white"
      }`}
    >

      {icon}

      {text}

    </button>

  );
}


/* ============================================================
   STAT CARD
============================================================ */

function Stat({
  title,
  value,
  sub,
  icon,
  danger,
}: {
  title: string;
  value: string;
  sub: string;
  icon: React.ReactNode;
  danger?: boolean;
}) {

  return (

    <div className="rounded-xl border border-[#202020] bg-[#090909] p-4">

      <div className="flex gap-3">

        <div className="grid h-11 w-11 place-items-center rounded-lg bg-red-900/15 text-red-500">

          {icon}

        </div>

        <div>

          <div className="text-xs text-neutral-400">

            {title}

          </div>

          <div className="mt-1 text-2xl font-bold">

            {value}

          </div>

        </div>

      </div>

      <div
        className={`mt-4 text-[11px] ${
          danger
            ? "text-red-400"
            : "text-neutral-500"
        }`}
      >

        {sub}

      </div>

    </div>

  );
}


/* ============================================================
   QUICK START
============================================================ */

function Quick({
  onUpload,
  onAnalyze,
  loading,
}: {
  onUpload: () => void;
  onAnalyze: () => void;
  loading: boolean;
}) {

  return (

    <div className="rounded-xl border border-[#202020] bg-[#090909] p-5">

      <div className="text-sm font-semibold text-red-500">

        Quick Start

      </div>

      <ol className="mt-3 space-y-2 text-xs text-neutral-400">

        <li>
          1. Upload your dataset
        </li>

        <li>
          2. We'll analyze the data
        </li>

        <li>
          3. Get AI-powered insights
        </li>

      </ol>

      <button
        onClick={onAnalyze}
        className="mt-4 flex items-center gap-2 rounded-lg bg-red-600 px-5 py-2.5 text-xs font-bold"
      >

        {loading ? (

          <Activity
            size={15}
            className="animate-spin"
          />

        ) : (

          <Check size={15} />

        )}

        {loading
          ? "Analyzing..."
          : "Ready to analyze"}

      </button>

      <button
        onClick={onUpload}
        className="ml-2 mt-4 rounded-lg border border-[#333] px-4 py-2.5 text-xs text-neutral-400"
      >

        Choose file

      </button>

    </div>

  );
}


/* ============================================================
   LAST DATASET
============================================================ */

function Last({
  file,
  upload,
}: {
  file: string;
  upload: () => void;
}) {

  return (

    <div className="rounded-xl border border-[#202020] bg-[#090909] p-5">

      <div className="text-sm font-semibold text-red-500">

        Last Analyzed Dataset

      </div>

      <div className="mt-4 flex items-center gap-3">

        <div className="grid h-11 w-11 place-items-center rounded-lg bg-red-900/20 text-red-500">

          <FileSpreadsheet />

        </div>

        <div className="min-w-0">

          <div className="truncate text-xs font-semibold">

            {file}

          </div>

          <div className="mt-1 text-[10px] text-neutral-500">

            Upload a new file to refresh the analysis

          </div>

        </div>

      </div>

      <button
        onClick={upload}
        className="mt-4 flex w-full items-center justify-center gap-2 rounded-lg border border-red-800 py-2 text-xs font-semibold text-red-500"
      >

        <RefreshCw
          size={15}
        />

        Analyze New File

      </button>

    </div>

  );
}


/* ============================================================
   EMPTY STATE
============================================================ */

function Empty({
  upload,
}: {
  upload: () => void;
}) {

  return (

    <div className="rounded-xl border border-dashed border-[#333] bg-[#080808] p-12 text-center">

      <div className="mx-auto grid h-16 w-16 place-items-center rounded-2xl bg-red-900/15 text-red-500">

        <UploadCloud
          size={30}
        />

      </div>

      <h2 className="mt-5 text-xl font-semibold">

        Upload a dataset to start

      </h2>

      <p className="mx-auto mt-2 max-w-lg text-sm leading-6 text-neutral-500">

        InsightGuard automatically
        detects the date column and
        business metrics, scans the
        complete history, identifies
        critical dates, generates
        Gemini insights, and prepares
        one consolidated email.

      </p>

      <button
        onClick={upload}
        className="mt-6 rounded-lg bg-red-600 px-6 py-3 text-sm font-bold"
      >

        Upload Excel / CSV

      </button>

    </div>

  );
}


/* ============================================================
   TIMELINE
============================================================ */

function Timeline({
  incidents,
  selected,
  choose,
}: {
  incidents: Incident[];
  selected: string;
  choose: (d: string) => void;
}) {

  if (!incidents.length) {

    return (

      <div className="rounded-xl border border-[#202020] bg-[#090909] p-8">

        <h2 className="font-semibold">

          Anomaly Timeline

        </h2>

        <div className="mt-8 text-center text-sm text-emerald-400">

          ✓ No critical anomalies detected.

        </div>

      </div>

    );
  }

  const max = Math.max(
    ...incidents.map(
      (x) =>
        x.metrics.length
    ),
    1
  );

  const pts =
    incidents.map(
      (x, i) => ({
        x:
          incidents.length === 1
            ? 280
            : 40 +
              (i *
                500) /
                (incidents.length -
                  1),

        y:
          175 -
          (x.metrics.length /
            max) *
            120,
      })
    );

  const path =
    pts
      .map(
        (p, i) =>
          `${
            i ? "L" : "M"
          } ${p.x} ${p.y}`
      )
      .join(" ");

  return (

    <div className="rounded-xl border border-[#202020] bg-[#090909] p-5">

      <div className="flex items-center justify-between gap-3">

        <h2 className="font-semibold">

          Anomaly Timeline (All Critical Dates)

        </h2>

        <div className="relative">

          <select
            value={selected}
            onChange={(e) =>
              choose(
                e.target.value
              )
            }
            className="appearance-none rounded-lg border border-[#303030] bg-[#060606] px-3 py-2 pr-9 text-xs"
          >

            {incidents.map(
              (x) => (

                <option
                  key={x.date}
                  value={x.date}
                >

                  {shortDate(
                    x.date
                  )}

                </option>

              )
            )}

          </select>

          <ChevronDown
            size={14}
            className="pointer-events-none absolute right-3 top-2.5 text-neutral-500"
          />

        </div>

      </div>

      <div className="mt-5 grid gap-5 lg:grid-cols-[1fr_220px]">

        <div>

          <div className="mb-2 text-[11px] text-neutral-500">

            Number of Anomalies

          </div>

          <svg
            viewBox="0 0 560 225"
            className="h-[245px] w-full"
            preserveAspectRatio="none"
          >

            {[35, 75, 115, 155, 195].map(
              (y) => (

                <line
                  key={y}
                  x1="30"
                  x2="540"
                  y1={y}
                  y2={y}
                  stroke="#171717"
                />

              )
            )}

            <path
              d={path}
              fill="none"
              stroke="#ef1b24"
              strokeWidth="2.5"
            />

            {pts.map(
              (p, i) => (

                <g
                  key={
                    incidents[i]
                      .date
                  }
                >

                  <circle
                    cx={p.x}
                    cy={p.y}
                    r="6"
                    fill="#ef1b24"
                  />

                  <text
                    x={p.x}
                    y={
                      p.y - 14
                    }
                    textAnchor="middle"
                    fill="white"
                    fontSize="12"
                    fontWeight="700"
                  >

                    {
                      incidents[i]
                        .metrics
                        .length
                    }

                  </text>

                  <text
                    x={p.x}
                    y="214"
                    textAnchor="middle"
                    fill="#777"
                    fontSize="10"
                  >

                    {new Date(
                      `${incidents[i].date}T00:00:00`
                    ).toLocaleString(
                      "en",
                      {
                        day: "2-digit",
                        month: "short",
                      }
                    )}

                  </text>

                </g>
              )
            )}

          </svg>

          <div className="mt-1 flex justify-center gap-2 text-[11px] text-neutral-500">

            <span className="h-3 w-3 bg-red-600" />

            Critical Anomalies

          </div>

        </div>

        <div className="border-l border-[#202020] pl-4">

          <div className="mb-3 text-xs font-semibold">

            🔴 Critical Dates

          </div>

          {incidents.map(
            (x) => (

              <button
                key={x.date}
                onClick={() =>
                  choose(x.date)
                }
                className={`mb-3 flex w-full items-start gap-3 text-left ${
                  selected === x.date
                    ? "text-white"
                    : "text-neutral-400"
                }`}
              >

                <span className="mt-1.5 h-2 w-2 rounded-full bg-red-700" />

                <span className="flex-1">

                  <span className="block text-xs">

                    {shortDate(
                      x.date
                    )}

                  </span>

                  <span className="text-[10px] text-neutral-600">

                    {
                      x.metrics
                        .length
                    }{" "}

                    metrics affected

                  </span>

                </span>

                <span className="rounded bg-red-950 px-2 py-1 text-[8px] font-bold text-red-400">

                  CRITICAL

                </span>

              </button>
            )
          )}

          <button
            onClick={() =>
              document
                .getElementById(
                  "report"
                )
                ?.scrollIntoView({
                  behavior:
                    "smooth",
                })
            }
            className="text-xs font-semibold text-red-500"
          >

            View Full Report →

          </button>

        </div>

      </div>

    </div>

  );
}


/* ============================================================
   SELECTED INCIDENT
============================================================ */

function Selected({
  incident,
  email,
  setEmail,
}: {
  incident: Incident | null;
  email: string;
  setEmail: (s: string) => void;
}) {

  if (!incident) {

    return (

      <div className="rounded-xl border border-[#202020] bg-[#090909] p-8 text-sm text-emerald-400">

        No critical incident selected.

      </div>

    );
  }

  return (

    <div className="rounded-xl border border-[#202020] bg-[#090909] p-5">

      <div className="flex items-center gap-2 text-xs text-neutral-400">

        <span className="h-2 w-2 rounded-full bg-red-600" />

        Selected Critical Date

      </div>

      <div className="mt-2 flex items-center justify-between gap-3">

        <h2 className="text-2xl font-bold text-red-500">

          {prettyDate(
            incident.date
          )}

        </h2>

        <span className="rounded-md bg-red-900/50 px-3 py-2 text-[10px] font-bold">

          CRITICAL

        </span>

      </div>

      <div className="mt-4 grid gap-2 sm:grid-cols-3">

        {incident.metrics.map(
          (m) => (

            <MetricCard
              key={m.name}
              m={m}
            />

          )
        )}

      </div>

      <div className="mt-4 border-t border-[#202020] pt-4 text-xs leading-5 text-neutral-300">

        <span className="font-bold text-red-500">

          ⚠ Summary:

        </span>{" "}

        {
          incident.metrics
            .length
        }{" "}

        metric-level anomaly

        {incident.metrics.length ===
        1
          ? ""
          : "ies"}{" "}

        detected outside the
        historical baseline.

      </div>

      <label className="mt-5 block text-[10px] uppercase tracking-wider text-neutral-600">

        Report email

        <input
          value={email}
          onChange={(e) =>
            setEmail(
              e.target.value
            )
          }
          placeholder="you@gmail.com"
          className="mt-2 w-full rounded-lg border border-[#292929] bg-[#060606] px-3 py-2.5 text-xs outline-none focus:border-red-600"
        />

      </label>

    </div>
  );
}


/* ============================================================
   METRIC CARD
============================================================ */

function MetricCard({
  m,
}: {
  m: Metric;
}) {

  const pos =
    (m.change || 0) >= 0;

  return (

    <div className="rounded-lg border border-[#252525] bg-[#060606] p-3">

      <div className="truncate text-[10px] text-neutral-400">

        {m.name}

      </div>

      <div
        className={`mt-2 text-lg font-bold ${
          pos
            ? "text-red-500"
            : "text-white"
        }`}
      >

        {pos ? "+" : ""}

        {m.change == null
          ? "—"
          : m.change.toFixed(2)}

        %

      </div>

      <div className="mt-1 text-[9px] text-neutral-600">

        vs historical baseline

      </div>

      <div className="mt-3 h-7">

        <svg
          viewBox="0 0 120 30"
          className="h-full w-full"
        >

          <path
            d={
              pos
                ? "M0 24 L15 22 L30 18 L45 20 L60 13 L75 15 L90 7 L105 10 L120 3"
                : "M0 5 L15 8 L30 6 L45 14 L60 11 L75 18 L90 14 L105 22 L120 25"
            }
            fill="none"
            stroke="#ef1b24"
            strokeWidth="1.5"
          />

        </svg>

      </div>

    </div>

  );
}


/* ============================================================
   METRICS TABLE
============================================================ */

function Metrics({
  incident,
}: {
  incident: Incident | null;
}) {

  return (

    <div className="rounded-xl border border-[#202020] bg-[#090909] p-5">

      <h2 className="font-semibold">

        Metrics Affected

        {incident
          ? ` on ${shortDate(
              incident.date
            )}`
          : ""}

      </h2>

      {incident?.metrics.map(
        (m) => (

          <div
            key={m.name}
            className="grid grid-cols-[1.5fr_.8fr_.8fr_.6fr] items-center gap-2 border-b border-[#181818] py-3 text-[11px]"
          >

            <span>

              {m.name}

            </span>

            <span
              className={
                m.change != null &&
                m.change >= 0
                  ? "text-emerald-400"
                  : "text-red-500"
              }
            >

              {m.change != null &&
              m.change >= 0
                ? "+"
                : ""}

              {m.change == null
                ? "—"
                : m.change.toFixed(
                    2
                  )}

              %

            </span>

            <span className="text-neutral-500">

              {m.change != null &&
              m.change >= 0
                ? "▲ Increase"
                : "▼ Decrease"}

            </span>

            <span className="rounded bg-red-900/60 px-2 py-1 text-center text-[9px] text-red-300">

              Critical

            </span>

          </div>
        )
      ) || (

        <div className="mt-8 text-sm text-neutral-600">

          No critical metrics.

        </div>

      )}

    </div>

  );
}


/* ============================================================
   AI BOX
============================================================ */

function AIBox({
  incident,
  ai,
  busy,
}: {
  incident: Incident | null;
  ai: AI | null;
  busy: boolean;
}) {

  return (

    <div className="rounded-xl border border-[#202020] bg-[#090909] p-5">

      <div className="flex items-center gap-2">

        <Sparkles
          size={18}
          className="text-red-500"
        />

        <h2 className="font-semibold">

          AI Analysis (Gemini)

        </h2>

      </div>

      {busy ? (

        <div className="mt-8 flex items-center gap-2 text-xs text-neutral-500">

          <Activity
            size={15}
            className="animate-spin text-red-500"
          />

          Generating AI explanation...

        </div>

      ) : (

        <>

          <p className="mt-5 text-xs leading-6 text-neutral-400">

            {ai?.whatHappened ||
              "Select a critical date to generate AI analysis."}

          </p>

          <p className="mt-3 text-xs leading-6 text-neutral-400">

            {ai?.likelyReason ||
              "Gemini will explain the business significance of the detected anomaly."}

          </p>

          <button
            onClick={() =>
              document
                .getElementById(
                  "insights"
                )
                ?.scrollIntoView({
                  behavior:
                    "smooth",
                })
            }
            className="mt-6 rounded-lg border border-red-800 px-4 py-2.5 text-xs font-semibold text-red-500"
          >

            View Full AI Analysis →

          </button>

        </>

      )}

    </div>

  );
}


/* ============================================================
   AI INSIGHTS
============================================================ */

function Insights({
  ai,
  busy,
}: {
  ai: AI | null;
  busy: boolean;
}) {

  return (

    <div
      id="insights"
      className="rounded-xl border border-[#202020] bg-[#090909] p-5"
    >

      <div className="flex items-center gap-2">

        <Sparkles
          size={17}
          className="text-red-500"
        />

        <h2 className="font-semibold">

          AI Insights (Gemini)

        </h2>

      </div>

      {busy ? (

        <div className="mt-6 text-xs text-neutral-500">

          Generating insights...

        </div>

      ) : (

        <>

          <IR
            title="What Happened"
            text={
              ai?.whatHappened ||
              "Select a critical date to generate insights."
            }
          />

          <IR
            title="Why It Matters"
            text={
              ai?.likelyReason ||
              "AI-generated business context will appear here."
            }
          />

          <IR
            title="What To Investigate"
            text={
              ai?.investigate ||
              "Investigation guidance will appear here."
            }
          />

        </>

      )}

    </div>

  );
}


/* ============================================================
   INSIGHT ROW
============================================================ */

function IR({
  title,
  text,
}: {
  title: string;
  text: string;
}) {

  return (

    <div className="mt-5">

      <div className="text-xs font-semibold text-red-500">

        {title}

      </div>

      <p className="mt-1 text-[11px] leading-5 text-neutral-400">

        {text}

      </p>

    </div>

  );
}


/* ============================================================
   REPORT
============================================================ */

function Report({
  email,
  sent,
  sending,
  ready,
  send,
}: {
  email: string;
  sent: boolean;
  sending: boolean;
  ready: boolean;
  send: () => void;
}) {

  return (

    <div className="rounded-xl border border-[#202020] bg-[#090909] p-5">

      <div className="flex flex-col gap-5 md:flex-row md:items-center md:justify-between">

        <div className="flex gap-3">

          <div className="grid h-10 w-10 place-items-center rounded-lg bg-red-950/50 text-red-500">

            <Mail />

          </div>

          <div>

            <h2 className="font-semibold">

              Consolidated Report

            </h2>

            <p className="mt-1 text-xs text-neutral-500">

              One complete report with all
              critical insights will be sent to:

            </p>

            <p className="mt-2 text-xs font-semibold text-red-500">

              {email ||
                "Enter recipient email above"}

            </p>

          </div>

        </div>

        <button
          disabled={
            !ready ||
            sending
          }
          onClick={send}
          className="flex items-center gap-2 rounded-lg bg-red-600 px-6 py-3 text-xs font-bold disabled:opacity-40"
        >

          {sending ? (

            <Activity
              size={15}
              className="animate-spin"
            />

          ) : (

            <Send size={15} />

          )}

          {sent
            ? "Report Sent"
            : sending
            ? "Sending..."
            : "Send Report"}

        </button>

      </div>

    </div>

  );
}