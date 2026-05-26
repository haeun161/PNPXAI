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

  useEffect(() => {
    if (!task) { setSamples([]); setSelected(null); return; }
    fetch(`/api/samples/${task}`)
      .then((r) => r.json())
      .then(setSamples)
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
    <div className="space-y-1.5">
      <label className="block text-xs font-semibold text-gray-500">Or use sample data</label>
      <div className="flex flex-wrap gap-1.5">
        {samples.map((s) => (
          <button
            key={s.name}
            onClick={() => handleSelect(s)}
            disabled={disabled || loading}
            className={`text-[11px] px-2.5 py-1 rounded-lg border transition-colors disabled:opacity-50 capitalize ${
              selected === s.name
                ? "border-blue-500 bg-blue-100 text-blue-700 font-medium"
                : "border-gray-200 text-gray-600 hover:border-blue-400 hover:bg-blue-50 hover:text-blue-700"
            }`}
          >
            {displayName(s.name)}
          </button>
        ))}
      </div>
    </div>
  );
}
