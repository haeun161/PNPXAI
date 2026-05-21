import torch
import numpy as np
from typing import Any

from backend.tasks.base import TaskHandler
from backend.renderers.text_renderer import render_text_attribution

_TEXT_EXPLAINERS = [
    {"name": "IntegratedGradients", "display_name": "Integrated Gradients", "estimated_time": 5},
    {"name": "Lime", "display_name": "LIME", "estimated_time": 25},
    {"name": "KernelShap", "display_name": "KernelSHAP", "estimated_time": 25},
    {"name": "SmoothGrad", "display_name": "SmoothGrad", "estimated_time": 5},
    {"name": "GradientXInput", "display_name": "Gradient × Input", "estimated_time": 3},
    {"name": "Gradient", "display_name": "Gradient", "estimated_time": 2},
]

_loaded_models: dict[str, Any] = {}


class TextTaskHandler(TaskHandler):
    task_name = "text"

    def get_models(self) -> list[dict]:
        return [
            {"name": "bert-base", "display_name": "BERT Base",
             "architecture": "Transformer", "description": "BERT base model for text classification.",
             "task": "text"},
            {"name": "distilbert", "display_name": "DistilBERT",
             "architecture": "Transformer", "description": "Distilled version of BERT, faster inference.",
             "task": "text"},
        ]

    def get_explainers(self, model_name: str) -> list[dict]:
        return [
            {"name": e["name"], "display_name": e["display_name"],
             "estimated_compute_time_seconds": e["estimated_time"],
             "compatible": True, "incompatibility_reason": None}
            for e in _TEXT_EXPLAINERS
        ]

    def load_model(self, model_name: str) -> torch.nn.Module:
        if model_name not in _loaded_models:
            from transformers import AutoModelForSequenceClassification
            model_map = {
                "bert-base": "bert-base-uncased",
                "distilbert": "distilbert-base-uncased",
            }
            hf_name = model_map.get(model_name, model_name)
            model = AutoModelForSequenceClassification.from_pretrained(hf_name, num_labels=2)
            model.eval()
            _loaded_models[model_name] = model
        return _loaded_models[model_name]

    def preprocess_input(self, raw_data: Any) -> Any:
        return raw_data  # Text is passed as string, tokenized in pipeline

    def get_modality(self):
        from pnpxai.core.modality.modality import TextModality
        return TextModality()

    def render_result(self, attribution: np.ndarray, input_data: Any, output_path: str) -> str:
        tokens = input_data.split() if isinstance(input_data, str) else ["[token]"] * len(attribution)
        return render_text_attribution(tokens, attribution, output_path)
