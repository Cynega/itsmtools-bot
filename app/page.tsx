"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { ThemeToggle } from "@/components/theme-toggle";

type JobStatus = "idle" | "running" | "done" | "error";

type JobResult = {
  keyword: string;
  research?: { volume?: number | string; cpc?: number | string; competitors?: number };
  article?: { word_count?: number };
  publish?: { success?: boolean; url?: string; id?: number; error?: string };
  error?: string;
};

type Job = {
  keyword: string;
  status: JobStatus;
  result?: JobResult;
};

export default function Home() {
  const [keywordsText, setKeywordsText] = useState("");
  const [country, setCountry] = useState("US");
  const [publishStatus, setPublishStatus] = useState<"draft" | "publish">("draft");
  const [jobs, setJobs] = useState<Job[]>([]);
  const [running, setRunning] = useState(false);
  const router = useRouter();

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    const keywords = keywordsText
      .split("\n")
      .map((k) => k.trim())
      .filter(Boolean);
    if (keywords.length === 0) return;

    setRunning(true);
    const initial: Job[] = keywords.map((k) => ({ keyword: k, status: "idle" }));
    setJobs(initial);

    for (let i = 0; i < keywords.length; i++) {
      const keyword = keywords[i];
      setJobs((prev) =>
        prev.map((j, idx) => (idx === i ? { ...j, status: "running" } : j)),
      );

      try {
        const res = await fetch("/api/generate", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ keyword, country, status: publishStatus }),
        });
        if (res.status === 401) {
          router.replace("/login");
          return;
        }
        const data: JobResult = await res.json();
        const ok = res.ok && data.publish?.success !== false;
        setJobs((prev) =>
          prev.map((j, idx) =>
            idx === i ? { ...j, status: ok ? "done" : "error", result: data } : j,
          ),
        );
      } catch (err) {
        setJobs((prev) =>
          prev.map((j, idx) =>
            idx === i
              ? {
                  ...j,
                  status: "error",
                  result: { keyword, error: (err as Error).message },
                }
              : j,
          ),
        );
      }
    }

    setRunning(false);
  }

  async function handleLogout() {
    await fetch("/api/auth/logout", { method: "POST" });
    router.replace("/login");
    router.refresh();
  }

  return (
    <main className="mx-auto max-w-3xl px-6 py-12">
      <header className="mb-8 flex items-start justify-between gap-4">
        <div>
          <h1 className="text-4xl font-bold tracking-tight">✍️ ITSM Content Bot</h1>
          <p className="mt-2 text-neutral-500 dark:text-stone-400">
            Generador automático de artículos SEO para itsmtools.com
          </p>
        </div>
        <div className="flex items-center gap-2">
          <ThemeToggle />
          <button
            type="button"
            onClick={handleLogout}
            className="rounded-md border border-neutral-200 bg-white px-3 py-2 text-sm text-neutral-600 transition hover:bg-neutral-100 dark:border-stone-700 dark:bg-stone-800 dark:text-stone-300 dark:hover:bg-stone-700"
          >
            Salir
          </button>
        </div>
      </header>

      <hr className="border-neutral-200 dark:border-stone-700" />

      <form onSubmit={handleSubmit} className="my-8 space-y-6">
        <h2 className="text-2xl font-semibold">Configuración</h2>

        <label className="block">
          <span className="mb-2 block text-sm font-medium">
            Keywords (una por línea)
          </span>
          <textarea
            value={keywordsText}
            onChange={(e) => setKeywordsText(e.target.value)}
            rows={5}
            placeholder={"best ITSM tools\nbest help desk software\nITSM vs ITSM comparison"}
            className="w-full rounded-md border border-neutral-200 bg-neutral-50 px-3 py-2 text-sm focus:border-brand focus:outline-none focus:ring-1 focus:ring-brand dark:border-stone-700 dark:bg-stone-800 dark:text-stone-100 dark:placeholder:text-stone-500"
            disabled={running}
            required
          />
        </label>

        <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
          <label className="block">
            <span className="mb-2 block text-sm font-medium">Estado en WordPress</span>
            <select
              value={publishStatus}
              onChange={(e) => setPublishStatus(e.target.value as "draft" | "publish")}
              className="w-full rounded-md border border-neutral-200 bg-neutral-50 px-3 py-2 text-sm focus:border-brand focus:outline-none focus:ring-1 focus:ring-brand dark:border-stone-700 dark:bg-stone-800 dark:text-stone-100"
              disabled={running}
            >
              <option value="draft">draft</option>
              <option value="publish">publish</option>
            </select>
          </label>

          <label className="block">
            <span className="mb-2 block text-sm font-medium">País del SERP</span>
            <select
              value={country}
              onChange={(e) => setCountry(e.target.value)}
              className="w-full rounded-md border border-neutral-200 bg-neutral-50 px-3 py-2 text-sm focus:border-brand focus:outline-none focus:ring-1 focus:ring-brand dark:border-stone-700 dark:bg-stone-800 dark:text-stone-100"
              disabled={running}
            >
              <option value="US">US</option>
              <option value="GB">GB</option>
              <option value="AU">AU</option>
              <option value="CA">CA</option>
            </select>
          </label>
        </div>

        <button
          type="submit"
          disabled={running}
          className="w-full rounded-md bg-brand px-4 py-3 font-semibold text-white transition hover:bg-brand-dark disabled:cursor-not-allowed disabled:opacity-60"
        >
          {running ? "Generando…" : "🚀 Generar artículos"}
        </button>
      </form>

      {jobs.length > 0 && (
        <section className="space-y-4">
          <h2 className="text-xl font-semibold">Resultados</h2>
          {jobs.map((job, idx) => (
            <JobCard key={idx} job={job} />
          ))}
        </section>
      )}

      <footer className="mt-16 border-t border-neutral-200 pt-6 text-sm text-neutral-500 dark:border-stone-700 dark:text-stone-400">
        itsmtools.com · ITSM Content Bot · Powered by Claude AI + DataForSEO
      </footer>
    </main>
  );
}

function JobCard({ job }: { job: Job }) {
  const { keyword, status, result } = job;
  return (
    <article className="rounded-md border border-neutral-200 bg-white p-4 dark:border-stone-700 dark:bg-stone-800">
      <header className="mb-2 flex items-center justify-between">
        <h3 className="font-medium">📄 {keyword}</h3>
        <StatusBadge status={status} />
      </header>
      {status === "running" && (
        <p className="text-sm text-neutral-500 dark:text-stone-400">
          Research → Generación → Publicación. Puede tardar 1–3 min.
        </p>
      )}
      {status === "done" && result && (
        <div className="space-y-1 text-sm">
          {result.research && (
            <p>
              Research: vol <strong>{result.research.volume ?? "N/A"}</strong> · CPC{" "}
              <strong>${result.research.cpc ?? "N/A"}</strong> · competidores{" "}
              <strong>{result.research.competitors ?? 0}</strong>
            </p>
          )}
          {result.article && (
            <p>
              Artículo: ~<strong>{result.article.word_count}</strong> palabras
            </p>
          )}
          {result.publish?.url && (
            <p>
              <a
                href={result.publish.url}
                target="_blank"
                rel="noreferrer"
                className="text-brand underline"
              >
                🔗 Ver en WordPress
              </a>
            </p>
          )}
        </div>
      )}
      {status === "error" && result && (
        <p className="text-sm text-red-600 dark:text-red-400">
          Error: {result.error || result.publish?.error || "fallo desconocido"}
        </p>
      )}
    </article>
  );
}

function StatusBadge({ status }: { status: JobStatus }) {
  const styles: Record<JobStatus, string> = {
    idle: "bg-neutral-100 text-neutral-600 dark:bg-stone-700 dark:text-stone-300",
    running: "bg-amber-100 text-amber-700 dark:bg-amber-900/40 dark:text-amber-300",
    done: "bg-emerald-100 text-emerald-700 dark:bg-emerald-900/40 dark:text-emerald-300",
    error: "bg-red-100 text-red-700 dark:bg-red-900/40 dark:text-red-300",
  };
  const label: Record<JobStatus, string> = {
    idle: "En cola",
    running: "Procesando…",
    done: "Listo",
    error: "Error",
  };
  return (
    <span className={`rounded-full px-2 py-0.5 text-xs font-medium ${styles[status]}`}>
      {label[status]}
    </span>
  );
}
