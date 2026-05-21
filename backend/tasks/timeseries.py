import torch
import numpy as np
import pandas as pd
from typing import Any

from backend.tasks.base import TaskHandler
from backend.renderers.timeseries_renderer import render_timeseries_attribution

_TS_EXPLAINERS = [
    {"name": "IntegratedGradients", "display_name": "Integrated Gradients", "estimated_time": 5},
    {"name": "SmoothGrad", "display_name": "SmoothGrad", "estimated_time": 5},
    {"name": "GradientXInput", "display_name": "Gradient × Input", "estimated_time": 3},
    {"name": "Gradient", "display_name": "Gradient", "estimated_time": 2},
    {"name": "Lime", "display_name": "LIME", "estimated_time": 25},
    {"name": "KernelShap", "display_name": "KernelSHAP", "estimated_time": 25},
]

_loaded_models: dict[str, Any] = {}


class SimpleTimeSeriesModel(torch.nn.Module):
    """Simple 1D CNN for time-series classification demo."""
    def __init__(self, input_dim: int = 100, num_classes: int = 2):
        super().__init__()
        self.conv = torch.nn.Sequential(
            torch.nn.Conv1d(1, 16, kernel_size=5, padding=2),
            torch.nn.ReLU(),
            torch.nn.AdaptiveAvgPool1d(1),
        )
        self.fc = torch.nn.Linear(16, num_classes)

    def forward(self, x):
        if x.dim() == 2:
            x = x.unsqueeze(1)
        out = self.conv(x).squeeze(-1)
        return self.fc(out)


class TimeSeriesTaskHandler(TaskHandler):
    task_name = "timeseries"

    def get_models(self) -> list[dict]:
        return [
            {"name": "simple-cnn-1d", "display_name": "Simple 1D CNN",
             "architecture": "1D CNN", "description": "Simple 1D convolutional network for time-series demo.",
             "task": "timeseries"},
        ]

    def get_explainers(self, model_name: str) -> list[dict]:
        return [
            {"name": e["name"], "display_name": e["display_name"],
             "estimated_compute_time_seconds": e["estimated_time"],
             "compatible": True, "incompatibility_reason": None}
            for e in _TS_EXPLAINERS
        ]

    def load_model(self, model_name: str) -> torch.nn.Module:
        if model_name not in _loaded_models:
            model = SimpleTimeSeriesModel()
            model.eval()
            _loaded_models[model_name] = model
        return _loaded_models[model_name]

    def preprocess_input(self, raw_data: Any) -> Any:
        if isinstance(raw_data, bytes):
            import io
            df = pd.read_csv(io.BytesIO(raw_data))
            values = df.iloc[:, 0].values.astype(np.float32)
            return torch.tensor(values).unsqueeze(0)  # (1, seq_len)
        elif isinstance(raw_data, str):
            values = [float(v.strip()) for v in raw_data.split(",") if v.strip()]
            return torch.tensor(values, dtype=torch.float32).unsqueeze(0)
        return raw_data

    def get_modality(self):
        from pnpxai.core.modality.modality import TimeSeriesModality
        return TimeSeriesModality()

    def render_result(self, attribution: np.ndarray, input_data: Any, output_path: str) -> str:
        if isinstance(input_data, torch.Tensor):
            signal = input_data.squeeze().numpy()
        elif isinstance(input_data, bytes):
            import io
            df = pd.read_csv(io.BytesIO(input_data))
            signal = df.iloc[:, 0].values.astype(np.float32)
        else:
            signal = np.zeros(len(attribution))
        return render_timeseries_attribution(signal, attribution, output_path)
