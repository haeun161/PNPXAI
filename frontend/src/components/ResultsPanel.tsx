"use client";
import { useState } from "react";
import { ExplainerResult, TaskType } from "@/lib/types";
import ResultCard from "./ResultCard";

interface Props {
  results: ExplainerResult[];
  task: TaskType;
  rankingMetric: string;
}

const ALL_RANKING_OPTIONS = [
  { value: "average", label: "Average (All)" },
  { value: "mu_fidelity", label: "Accuracy (Fidelity)" },
  { value: "abpc", label: "Accuracy (AbPC)" },
  { value: "sensitivity", label: "Sensitivity" },
  { value: "complexity", label: "Complexity" },
];

function rerank(results: ExplainerResult[], metric: string): ExplainerResult[] {
  const completed = results
    .filter((r) => r.status === "completed")
    .map((r) => ({ ...r }));

  completed.sort((a, b) => {
    const scoreA = getRankScore(a, metric);
    const scoreB = getRankScore(b, metric);
    return scoreB - scoreA;
  });

  completed.forEach((r, i) => { r.rank = i + 1; });

  const others = results.filter((r) => r.status !== "completed");
  return [...completed, ...others];
}

function getRankScore(r: ExplainerResult, metric: string): number {
  if (metric === "average") {
    // Average of Fidelity (as accuracy), Sensitivity, Complexity
    const vals = [r.mu_fidelity, r.sensitivity, r.complexity].filter((v) => v != null) as number[];
    return vals.length > 0 ? vals.reduce((a, b) => a + b, 0) / vals.length : 0;
  }
  return (r as any)[metric] ?? 0;
}

export default function ResultsPanel({ results, task, rankingMetric: initialMetric }: Props) {
  const RANKING_OPTIONS = task === "text"
    ? ALL_RANKING_OPTIONS.filter((o) => o.value !== "mu_fidelity")
    : ALL_RANKING_OPTIONS;
  const [activeMetric, setActiveMetric] = useState(initialMetric);
  const [expanded, setExpanded] = useState(false);

  if (results.length === 0) {
    return (
      <div className="text-center py-12 text-gray-400">
        <svg className="mx-auto h-12 w-12 mb-3" fill="none" viewBox="0 0 24 24" stroke="currentColor">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1} d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z" />
        </svg>
        <p className="text-sm">Results will appear here after analysis</p>
      </div>
    );
  }

  const rankedResults = rerank(results, activeMetric).filter((r) => r.status !== "failed");
  const activeLabel = RANKING_OPTIONS.find((o) => o.value === activeMetric)?.label ?? activeMetric;

  // Expanded: fullscreen overlay showing all results in a grid
  if (expanded) {
    return (
      <div className="fixed inset-0 z-50 bg-white overflow-y-auto">
        <div className="sticky top-0 bg-white border-b border-gray-200 px-6 py-3 flex items-center justify-between z-10">
          <h3 className="text-base font-semibold text-gray-800">
            XAI Results
            <span className="font-normal text-gray-400 ml-1">(ranked by {activeLabel})</span>
          </h3>
          <div className="flex items-center gap-3">
            <div className="flex gap-1">
              {RANKING_OPTIONS.map((opt) => (
                <button
                  key={opt.value}
                  onClick={() => setActiveMetric(opt.value)}
                  className={`text-xs px-2.5 py-1 rounded-md border transition-colors ${
                    activeMetric === opt.value
                      ? "border-blue-500 bg-blue-50 text-blue-700 font-medium"
                      : "border-gray-200 text-gray-500 hover:border-gray-300"
                  }`}
                >
                  {opt.label}
                </button>
              ))}
            </div>
            <button
              onClick={() => setExpanded(false)}
              className="flex items-center gap-1 text-sm text-gray-500 hover:text-gray-700 border border-gray-300 rounded-lg px-3 py-1.5"
            >
              <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
              </svg>
              Close
            </button>
          </div>
        </div>
        <div className="p-6">
          <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-4 xl:grid-cols-5 gap-4">
            {rankedResults.map((r) => (
              <ResultCard key={r.explainer_name} result={r} task={task} rankingMetric={activeMetric} />
            ))}
          </div>
        </div>
      </div>
    );
  }

  // Normal: horizontal scroll with 3 visible
  return (
    <div>
      <div className="flex items-center justify-between mb-3">
        <div className="flex items-center gap-2">
          <h3 className="text-sm font-semibold text-gray-700">
            XAI Results
            <span className="font-normal text-gray-400 ml-1">(ranked by {activeLabel})</span>
          </h3>
          {rankedResults.length > 3 && (
            <button
              onClick={() => setExpanded(true)}
              className="flex items-center gap-1 text-xs text-blue-600 hover:text-blue-700 border border-blue-200 rounded-md px-2 py-0.5"
              title="View all results in full screen"
            >
              <svg className="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 8V4m0 0h4M4 4l5 5m11-1V4m0 0h-4m4 0l-5 5M4 16v4m0 0h4m-4 0l5-5m11 5v-4m0 4h-4m4 0l-5-5" />
              </svg>
              Expand All ({rankedResults.length})
            </button>
          )}
        </div>
        <div className="flex gap-1">
          {RANKING_OPTIONS.map((opt) => (
            <button
              key={opt.value}
              onClick={() => setActiveMetric(opt.value)}
              className={`text-[10px] px-2 py-1 rounded-md border transition-colors ${
                activeMetric === opt.value
                  ? "border-blue-500 bg-blue-50 text-blue-700 font-medium"
                  : "border-gray-200 text-gray-500 hover:border-gray-300"
              }`}
            >
              {opt.label}
            </button>
          ))}
        </div>
      </div>
      <div className="flex gap-4 overflow-x-auto pb-2">
        {rankedResults.map((r) => (
          <div key={r.explainer_name} className="flex-shrink-0" style={{ width: "calc((100% - 2rem) / 3)" }}>
            <ResultCard result={r} task={task} rankingMetric={activeMetric} />
          </div>
        ))}
      </div>
    </div>
  );
}
