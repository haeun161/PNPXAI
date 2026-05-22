"use client";
import { useEffect, useRef, useState } from "react";
import { ExplainerInfo, TaskType } from "@/lib/types";
import { getExplainers, getRecommendedExplainers } from "@/lib/api";

interface Props {
  task: TaskType | "";
  model: string;
  selected: string[];
  onSelect: (names: string[]) => void;
  disabled?: boolean;
}

export default function ExplainerSelector({ task, model, selected, onSelect, disabled }: Props) {
  const [explainers, setExplainers] = useState<ExplainerInfo[]>([]);
  const [recommended, setRecommended] = useState<string[]>([]);
  const [recommending, setRecommending] = useState(false);
  const didAutoSelect = useRef(false);

  useEffect(() => {
    if (!task || !model) { setExplainers([]); setRecommended([]); return; }
    didAutoSelect.current = false;
    getExplainers(task, model).then(setExplainers).catch(console.error);

    setRecommending(true);
    getRecommendedExplainers(task as TaskType, model)
      .then((names) => {
        setRecommended(names);
        if (!didAutoSelect.current) {
          didAutoSelect.current = true;
          onSelect(names);
        }
      })
      .catch(console.error)
      .finally(() => setRecommending(false));
  }, [task, model]); // eslint-disable-line react-hooks/exhaustive-deps

  const toggle = (name: string) => {
    if (selected.includes(name)) {
      onSelect(selected.filter((n) => n !== name));
    } else {
      onSelect([...selected, name]);
    }
  };

  const formatTime = (seconds: number) => {
    if (seconds < 10) return `~${seconds}s`;
    return `~${Math.round(seconds)}s`;
  };

  if (!task || !model) {
    return (
      <div className="space-y-2">
        <label className="block text-sm font-semibold text-gray-700">Select Explainers</label>
        <p className="text-xs text-gray-400">{!task ? "Select a task first" : "Select a model first"}</p>
      </div>
    );
  }

  return (
    <div className="space-y-2">
      <div className="flex items-center justify-between">
        <label className="block text-sm font-semibold text-gray-700">
          Select Explainers
          <span className="font-normal text-gray-400 ml-1">({selected.length} selected)</span>
        </label>
        <div className="flex items-center gap-2">
          {recommending && <span className="text-xs text-gray-400 animate-pulse">detecting...</span>}
          <button
            onClick={() => {
              const compatible = explainers.filter((e) => e.compatible).map((e) => e.name);
              onSelect(selected.length === compatible.length ? [] : compatible);
            }}
            disabled={disabled}
            className="text-xs text-blue-600 hover:text-blue-700 disabled:opacity-50"
          >
            {selected.length === explainers.filter((e) => e.compatible).length ? "Deselect All" : "Select All"}
          </button>
        </div>
      </div>
      {recommended.length > 0 && (
        <button
          onClick={() => onSelect(recommended)}
          disabled={disabled}
          className="text-xs text-green-600 hover:text-green-700 disabled:opacity-50"
        >
          Reset to recommended
        </button>
      )}
      <div className="space-y-1 max-h-48 overflow-y-auto">
        {explainers.map((exp) => {
          const isIncompat = !exp.compatible;
          const isSlow = exp.estimated_compute_time_seconds >= 20;
          const isRecommended = recommended.includes(exp.name);
          return (
            <label
              key={exp.name}
              className={`flex items-center gap-2 rounded-lg border px-3 py-2 text-sm transition-colors ${
                isIncompat
                  ? "border-gray-200 bg-gray-50 opacity-50 cursor-not-allowed"
                  : selected.includes(exp.name)
                  ? "border-blue-500 bg-blue-50"
                  : "border-gray-200 hover:border-gray-300 cursor-pointer"
              } ${disabled ? "pointer-events-none opacity-50" : ""}`}
            >
              <input
                type="checkbox"
                checked={selected.includes(exp.name)}
                onChange={() => toggle(exp.name)}
                disabled={disabled || isIncompat}
                className="rounded border-gray-300 text-blue-600 focus:ring-blue-500"
              />
              <div className="flex-1 min-w-0">
                <div className="flex items-center gap-2 flex-wrap">
                  <span className="font-medium">{exp.display_name}</span>
                  <span className="text-xs text-gray-400">{formatTime(exp.estimated_compute_time_seconds)}</span>
                  {isRecommended && <span className="text-xs bg-green-100 text-green-700 px-1.5 py-0.5 rounded">recommended</span>}
                  {isSlow && <span className="text-xs bg-yellow-100 text-yellow-700 px-1.5 py-0.5 rounded">slow</span>}
                </div>
              </div>
            </label>
          );
        })}
      </div>
    </div>
  );
}
