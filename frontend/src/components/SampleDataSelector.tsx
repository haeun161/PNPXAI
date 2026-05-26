"use client";
import { useEffect, useState } from "react";
import { TaskType } from "@/lib/types";

interface SampleFile {
  name: string;
  path: string;
}

interface Props {
  task: TaskType | "";
  onSampleSelect: (file: Blob, preview: string) => void;
  disabled?: boolean;
}

export default function SampleDataSelector({ task, onSampleSelect, disabled }: Props) {
  const [samples, setSamples] = useState<SampleFile[]>([]);
  const [loading, setLoading] = useState(false);
  const [selected, setSelected] = useState<string | null>(null);
  const [previews, setPreviews] = useState<Record<string, string>>({});

  useEffect(() => {
    if (!task) { setSamples([]); setSelected(null); setPreviews({}); return; }
    fetch(`/api/samples/${task}`)
      .then((r) => r.json())
      .then((data: SampleFile[]) => {
        setSamples(data);
        // Load previews for all samples
        data.forEach(async (s) => {
          try {
            const res = await fetch(`/api/samples/${task}/${s.name}`);
            const blob = await res.blob();
            if (task === "image") {
              setPreviews((prev) => ({ ...prev, [s.name]: URL.createObjectURL(blob) }));
            } else if (task === "text") {
              const text = await blob.text();
              setPreviews((prev) => ({ ...prev, [s.name]: text }));
            } else if (task === "timeseries") {
              const text = await blob.text();
              setPreviews((prev) => ({ ...prev, [s.name]: text }));
            }
          } catch { /* ignore */ }
        });
      })
      .catch(() => setSamples([]));
  }, [task]);

  if (!task || samples.length === 0) return null;

  const handleSelect = async (sample: SampleFile) => {
    setLoading(true);
    try {
      const res = await fetch(`/api/samples/${task}/${sample.name}`);
      const blob = await res.blob();

      let preview = sample.name;
      if (task === "image") {
        preview = URL.createObjectURL(blob);
      } else if (task === "text") {
        preview = await blob.text();
      }

      setSelected(sample.name);
      onSampleSelect(blob, preview);
    } catch {
      // ignore
    } finally {
      setLoading(false);
    }
  };

  const displayName = (name: string) => name.replace(/\.[^.]+$/, "").replace(/[_-]/g, " ");

  return (
    <div className="space-y-2">
      {/* no label - tab already indicates this is sample data */}
      <div className="grid gap-2" style={{ gridTemplateColumns: `repeat(${Math.min(samples.length, 3)}, 1fr)` }}>
        {samples.map((s) => (
          <button
            key={s.name}
            onClick={() => handleSelect(s)}
            disabled={disabled || loading}
            className={`rounded-lg border p-2 transition-colors disabled:opacity-50 text-left ${
              selected === s.name
                ? "border-blue-500 bg-blue-50 ring-1 ring-blue-300"
                : "border-gray-200 hover:border-blue-400 hover:bg-blue-50/30"
            }`}
          >
            {/* Preview */}
            {task === "image" && previews[s.name] && (
              <img src={previews[s.name]} alt={s.name} className="w-full h-16 object-cover rounded mb-1.5" />
            )}
            {task === "text" && previews[s.name] && (
              <div className="w-full h-16 overflow-hidden rounded bg-gray-50 border border-gray-100 p-1.5 mb-1.5 text-[9px] text-gray-500 leading-tight">
                {previews[s.name].slice(0, 120)}...
              </div>
            )}
            {task === "timeseries" && previews[s.name] && (
              <div className="w-full h-16 rounded bg-gray-50 border border-gray-100 mb-1.5 flex items-end px-1 pb-1 gap-px overflow-hidden">
                {(() => {
                  const vals = previews[s.name]
                    .split("\n").filter((l) => l && l !== "value")
                    .join(",").split(",")
                    .map((v) => parseFloat(v.trim()))
                    .filter((v) => !isNaN(v));
                  const min = Math.min(...vals);
                  const max = Math.max(...vals);
                  const range = max - min || 1;
                  const step = Math.max(1, Math.floor(vals.length / 30));
                  const sampled = vals.filter((_, i) => i % step === 0);
                  return sampled.map((v, i) => (
                    <div
                      key={i}
                      className="bg-blue-400 rounded-t-sm flex-1 min-w-[2px]"
                      style={{ height: `${((v - min) / range) * 100}%`, minHeight: 2 }}
                    />
                  ));
                })()}
              </div>
            )}
            {/* Label */}
            <p className={`text-[10px] text-center capitalize truncate ${
              selected === s.name ? "text-blue-700 font-semibold" : "text-gray-600"
            }`}>
              {displayName(s.name)}
            </p>
          </button>
        ))}
      </div>
    </div>
  );
}
