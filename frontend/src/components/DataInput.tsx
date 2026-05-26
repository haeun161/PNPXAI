"use client";
import { useState } from "react";
import { TaskType } from "@/lib/types";
import ImageUploader from "./ImageUploader";
import TextInput from "./TextInput";
import TimeSeriesInput from "./TimeSeriesInput";
import SampleDataSelector from "./SampleDataSelector";

interface Props {
  task: TaskType | "";
  onDataReady: (data: File | Blob, preview: string) => void;
  disabled?: boolean;
}

export default function DataInput({ task, onDataReady, disabled }: Props) {
  const [mode, setMode] = useState<"sample" | "upload">("sample");

  if (!task) return null;

  return (
    <div className="space-y-2">
      <div className="flex items-center gap-1 bg-gray-100 rounded-lg p-0.5">
        <button
          onClick={() => setMode("sample")}
          disabled={disabled}
          className={`flex-1 text-xs py-1.5 rounded-md font-medium transition-colors ${
            mode === "sample"
              ? "bg-white text-blue-700 shadow-sm"
              : "text-gray-500 hover:text-gray-700"
          }`}
        >
          Sample Data
        </button>
        <button
          onClick={() => setMode("upload")}
          disabled={disabled}
          className={`flex-1 text-xs py-1.5 rounded-md font-medium transition-colors ${
            mode === "upload"
              ? "bg-white text-blue-700 shadow-sm"
              : "text-gray-500 hover:text-gray-700"
          }`}
        >
          Upload
        </button>
      </div>

      {mode === "sample" && (
        <SampleDataSelector task={task} onSampleSelect={onDataReady} disabled={disabled} />
      )}

      {mode === "upload" && (
        <>
          {task === "image" && (
            <ImageUploader onImageSelect={(file) => onDataReady(file, file.name)} disabled={disabled} />
          )}
          {task === "text" && (
            <TextInput onTextReady={onDataReady} disabled={disabled} />
          )}
          {task === "timeseries" && (
            <TimeSeriesInput onDataReady={onDataReady} disabled={disabled} />
          )}
        </>
      )}
    </div>
  );
}
