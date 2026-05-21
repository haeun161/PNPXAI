"use client";
import { TaskType } from "@/lib/types";
import ImageUploader from "./ImageUploader";
import TextInput from "./TextInput";
import TimeSeriesInput from "./TimeSeriesInput";

interface Props {
  task: TaskType | "";
  onDataReady: (data: File | Blob, preview: string) => void;
  disabled?: boolean;
}

export default function DataInput({ task, onDataReady, disabled }: Props) {
  if (!task) return null;

  if (task === "image") {
    return (
      <ImageUploader
        onImageSelect={(file) => onDataReady(file, file.name)}
        disabled={disabled}
      />
    );
  }

  if (task === "text") {
    return <TextInput onTextReady={onDataReady} disabled={disabled} />;
  }

  if (task === "timeseries") {
    return <TimeSeriesInput onDataReady={onDataReady} disabled={disabled} />;
  }

  return null;
}
