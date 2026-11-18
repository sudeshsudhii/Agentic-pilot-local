import { AlertTriangle, ChevronDown, ChevronRight, Download } from "lucide-react";
import { useEffect, useRef, useState } from "react";
import { DesignFile, DesignJob, DesignJobStatus, getDesignJob, resolveApiUrl } from "../api/client";

const POLL_INTERVAL_MS = 1200;
const POLL_TIMEOUT_MS = 6 * 60 * 1000;
const MAX_CONSECUTIVE_ERRORS = 5;

type Props = {
  jobId: string | null;
};

/** A phase of real backend work, listed in the order the pipeline runs them. */
const PHASES = [
  { key: "analysing", label: "Analyzing" },
  { key: "reasoning", label: "Reasoning" },
  { key: "executing", label: "Executing" },
  { key: "building", label: "Building" }
];

function isTerminal(status: DesignJobStatus): boolean {
  return status === "succeeded" || status === "failed";
}

/** True once the FreeCAD hand-off has settled, so polling can stop. */
function liveSettled(job: DesignJob | null): boolean {
  if (!job || !isTerminal(job.status)) {
    return false;
  }
  if (job.status === "failed") {
    return true;
  }
  const live = job.live_status;
  return !job.live || live === "shown" || live === "partial" || live === "unavailable";
}

/** Index of the phase in progress, or PHASES.length once everything is done. */
function currentPhase(job: DesignJob | null): number {
  if (!job) {
    return 0;
  }
  if (liveSettled(job)) {
    return PHASES.length;
  }
  if (job.status === "queued") {
    return 0;
  }
  if (job.status === "generating") {
    return 1;
  }
  if (job.status === "running") {
    return 2;
  }
  return 3;
}

function formatBytes(bytes: number | null | undefined): string {
  if (typeof bytes !== "number" || !Number.isFinite(bytes) || bytes < 0) {
    return "unknown size";
  }
  if (bytes < 1024) {
    return `${bytes} B`;
  }
  if (bytes < 1024 * 1024) {
    return `${(bytes / 1024).toFixed(1)} KB`;
  }
  return `${(bytes / (1024 * 1024)).toFixed(2)} MB`;
}

function formatBbox(bbox: number[] | null | undefined): string | null {
  if (!Array.isArray(bbox) || bbox.length === 0) {
    return null;
  }
  const parts = bbox
    .filter((value): value is number => typeof value === "number" && Number.isFinite(value))
    .map((value) => `${Number(value.toFixed(2))}`);
  return parts.length === 0 ? null : `${parts.join(" × ")} mm`;
}

function formatVolume(volume: number | null | undefined): string | null {
  if (typeof volume !== "number" || !Number.isFinite(volume)) {
    return null;
  }
  return `${volume.toLocaleString(undefined, { maximumFractionDigits: 2 })} mm³`;
}

function formatDuration(durationMs: number | null | undefined): string | null {
  if (typeof durationMs !== "number" || !Number.isFinite(durationMs) || durationMs <= 0) {
    return null;
  }
  return `${(durationMs / 1000).toFixed(1)} s`;
}

/**
 * Progress panel for one design job.
 *
 * The model itself is shown in the FreeCAD window, not duplicated here. Once the
 * build there has finished, the CAD output can be pulled into the page on demand.
 */
export function DesignResult({ jobId }: Props) {
  const [job, setJob] = useState<DesignJob | null>(null);
  const [transportError, setTransportError] = useState<string | null>(null);
  const [loaded, setLoaded] = useState(false);
  const [scriptOpen, setScriptOpen] = useState(false);
  const errorStreak = useRef(0);

  useEffect(() => {
    setJob(null);
    setTransportError(null);
    setLoaded(false);
    setScriptOpen(false);
    errorStreak.current = 0;
    if (!jobId) {
      return;
    }

    let cancelled = false;
    const startedAt = Date.now();

    async function tick() {
      try {
        const next = await getDesignJob(jobId as string);
        if (cancelled) {
          return;
        }
        errorStreak.current = 0;
        setJob(next);
        // Keep polling past "succeeded" until FreeCAD has finished building, so
        // the build phase is visible instead of being skipped over.
        if (liveSettled(next)) {
          window.clearInterval(timer);
        }
      } catch (err) {
        errorStreak.current += 1;
        if (errorStreak.current >= MAX_CONSECUTIVE_ERRORS && !cancelled) {
          window.clearInterval(timer);
          setTransportError(err instanceof Error ? err.message : "Lost contact with the design service.");
        }
      }
      if (!cancelled && Date.now() - startedAt > POLL_TIMEOUT_MS) {
        window.clearInterval(timer);
        setTransportError("Timed out waiting for this design. It may still be running on the backend.");
      }
    }

    const timer = window.setInterval(tick, POLL_INTERVAL_MS);
    void tick();
    return () => {
      cancelled = true;
      window.clearInterval(timer);
    };
  }, [jobId]);

  if (!jobId) {
    return null;
  }

  const status = job?.status ?? "queued";
  const phase = currentPhase(job);
  const settled = liveSettled(job);
  const failed = status === "failed";
  const files: DesignFile[] = job?.files ?? [];
  const bbox = formatBbox(job?.metrics?.bbox_mm);
  const volume = formatVolume(job?.metrics?.volume_mm3);
  const duration = formatDuration(job?.duration_ms);

  const stageNote =
    phase === 3 && job?.live_step && job?.live_step_total
      ? `${job.live_step_index}/${job.live_step_total} · ${job.live_step}`
      : null;

  return (
    <section className="panel design-result-panel">
      {transportError ? (
        <div className="design-error">
          <AlertTriangle size={18} />
          <p>{transportError}</p>
        </div>
      ) : null}

      {!failed && phase < PHASES.length ? (
        <div className="design-pulse" key={PHASES[phase].key}>
          <span className="design-pulse-dot" />
          <span className="design-pulse-word">{PHASES[phase].label}</span>
          <span className="design-pulse-dots">
            <i />
            <i />
            <i />
          </span>
          {stageNote ? <span className="design-pulse-note">{stageNote}</span> : null}
        </div>
      ) : null}

      {failed && job?.error ? (
        <div className="design-error">
          <AlertTriangle size={18} />
          <p>{job.error}</p>
        </div>
      ) : null}

      {settled && !failed ? (
        <div className="design-handoff">
          <p className="muted">
            {job?.live_status === "shown" || job?.live_status === "partial"
              ? "The model is open in FreeCAD."
              : "The model was built headlessly; the FreeCAD window could not be opened."}
          </p>
          {!loaded ? (
            <button className="primary-button" onClick={() => setLoaded(true)}>
              <Download size={18} /> Load from FreeCAD
            </button>
          ) : null}
        </div>
      ) : null}

      {settled && !failed && loaded ? (
        <>
          {job?.preview_url ? (
            <div className="design-preview">
              <img src={resolveApiUrl(job.preview_url)} alt="Orthographic views of the generated part" />
            </div>
          ) : null}

          {bbox || volume || duration ? (
            <div className="execution-dashboard design-metrics">
              {bbox ? (
                <div className="dashboard-card">
                  <span className="dashboard-label">Bounding box</span>
                  <p>{bbox}</p>
                </div>
              ) : null}
              {volume ? (
                <div className="dashboard-card">
                  <span className="dashboard-label">Volume</span>
                  <p>{volume}</p>
                </div>
              ) : null}
              {duration ? (
                <div className="dashboard-card">
                  <span className="dashboard-label">Build time</span>
                  <p>{duration}</p>
                </div>
              ) : null}
            </div>
          ) : null}

          {files.length > 0 ? (
            <div className="design-files">
              {files
                .filter((file) => !file.name.startsWith("step_"))
                .map((file) => (
                  <a
                    key={file.name}
                    className="design-file"
                    href={resolveApiUrl(file.url)}
                    download={file.name}
                    target="_blank"
                    rel="noreferrer"
                  >
                    <Download size={16} />
                    <span className="design-file-kind">{file.kind.toUpperCase()}</span>
                    <span className="muted">{formatBytes(file.size_bytes)}</span>
                  </a>
                ))}
            </div>
          ) : null}

          {job?.script ? (
            <div className="design-script">
              <button className="disclosure" onClick={() => setScriptOpen((open) => !open)}>
                {scriptOpen ? <ChevronDown size={16} /> : <ChevronRight size={16} />}
                Generated FreeCAD script
              </button>
              {scriptOpen ? <pre className="result-block design-script-body">{job.script}</pre> : null}
            </div>
          ) : null}
        </>
      ) : null}
    </section>
  );
}
