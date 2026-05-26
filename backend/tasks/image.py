import torch
import torchvision.models as models
import numpy as np
from typing import Any, Optional
from PIL import Image

from backend.tasks.base import TaskHandler
from backend.core.image_utils import preprocess_image, get_original_image_array
from backend.renderers.image_renderer import render_heatmap

_IMAGE_MODELS = {
    "resnet50": {
        "display_name": "ResNet-50",
        "architecture": "Residual Network",
        "description": "50-layer deep residual network, widely used in XAI research.",
        "loader": lambda: models.resnet50(weights=models.ResNet50_Weights.IMAGENET1K_V2),
    },
    "vgg16": {
        "display_name": "VGG-16",
        "architecture": "Sequential CNN",
        "description": "16-layer sequential CNN, ideal for layer-wise XAI methods.",
        "loader": lambda: models.vgg16(weights=models.VGG16_Weights.IMAGENET1K_V1),
    },
    "densenet121": {
        "display_name": "DenseNet-121",
        "architecture": "Dense Connections",
        "description": "121-layer densely connected network.",
        "loader": lambda: models.densenet121(weights=models.DenseNet121_Weights.IMAGENET1K_V1),
    },
}

_loaded_models: dict[str, torch.nn.Module] = {}
_hf_image_cache: dict[str, dict] = {}

_IMAGE_EXPLAINERS = [
    {"name": "IntegratedGradients", "display_name": "Integrated Gradients", "estimated_time": 5},
    {"name": "GradCam", "display_name": "Grad-CAM", "estimated_time": 3},
    {"name": "GuidedGradCam", "display_name": "Guided Grad-CAM", "estimated_time": 3},
    {"name": "SmoothGrad", "display_name": "SmoothGrad", "estimated_time": 5},
    {"name": "VarGrad", "display_name": "VarGrad", "estimated_time": 5},
    {"name": "GradientXInput", "display_name": "Gradient × Input", "estimated_time": 2},
    {"name": "Gradient", "display_name": "Gradient", "estimated_time": 2},
    {"name": "LRPUniformEpsilon", "display_name": "LRP (Uniform Epsilon)", "estimated_time": 3},
    {"name": "Lime", "display_name": "LIME", "estimated_time": 25},
    {"name": "KernelShap", "display_name": "KernelSHAP", "estimated_time": 25},
    {"name": "RAP", "display_name": "RAP", "estimated_time": 5},
]


class _HFImageWrapper(torch.nn.Module):
    """Wraps a HuggingFace image classification model to return raw logits tensor."""
    def __init__(self, model):
        super().__init__()
        self.model = model

    def forward(self, pixel_values):
        out = self.model(pixel_values=pixel_values)
        return out.logits if hasattr(out, "logits") else out


def _check_hf_model_compatibility(model_id: str):
    """Raises ValueError with a clear message if the model can't be loaded via transformers."""
    try:
        from huggingface_hub import HfApi
        info = HfApi().model_info(model_id)
        library = info.library_name or "unknown"
        if library not in ("transformers", None):
            raise ValueError(
                f"This model uses the '{library}' library, which is not supported. "
                f"Only transformers-based image classification models are supported."
            )
    except ValueError:
        raise
    except Exception:
        pass  # HF Hub unavailable or model not found — let the actual load fail with its own error


def _load_hf_image_model(model_id: str) -> dict:
    if model_id not in _hf_image_cache:
        from transformers import AutoModelForImageClassification, AutoImageProcessor

        _check_hf_model_compatibility(model_id)

        try:
            processor = AutoImageProcessor.from_pretrained(model_id)
        except OSError:
            raise ValueError(
                f"'{model_id}' does not have a standard image processor config. "
                f"Make sure the model is a transformers image classification model with a preprocessor_config.json."
            )

        try:
            raw_model = AutoModelForImageClassification.from_pretrained(model_id)
        except ValueError as e:
            if "Unrecognized model" in str(e) or "model_type" in str(e):
                raise ValueError(
                    f"'{model_id}' uses an unrecognized architecture. "
                    f"The model may require a third-party library that is not installed."
                )
            raise

        raw_model.eval()
        wrapper = _HFImageWrapper(raw_model)
        label_map = {}
        if hasattr(raw_model.config, "id2label"):
            label_map = {int(k): v for k, v in raw_model.config.id2label.items()}
        _hf_image_cache[model_id] = {
            "wrapper": wrapper,
            "processor": processor,
            "label_map": label_map,
        }
    return _hf_image_cache[model_id]


class ImageTaskHandler(TaskHandler):
    task_name = "image"

    def get_models(self) -> list[dict]:
        return [
            {"name": name, "display_name": info["display_name"],
             "architecture": info["architecture"], "description": info["description"],
             "task": "image"}
            for name, info in _IMAGE_MODELS.items()
        ]

    def get_explainers(self, model_name: str) -> list[dict]:
        # zennit's SequentialMergeBatchNorm canonizer fails on DenseNet's dense connections:
        # it tries to merge a cross-block BatchNorm (96-channel) into conv2 (32-channel),
        # leaving the model in a corrupted state that breaks subsequent explainers.
        _DENSENET_INCOMPATIBLE = {"LRPUniformEpsilon", "RAP"}
        is_densenet = model_name == "densenet121"

        result = []
        for e in _IMAGE_EXPLAINERS:
            incompatible = is_densenet and e["name"] in _DENSENET_INCOMPATIBLE
            result.append({
                "name": e["name"],
                "display_name": e["display_name"],
                "estimated_compute_time_seconds": e["estimated_time"],
                "compatible": not incompatible,
                "incompatibility_reason": (
                    "Not compatible with DenseNet's dense connections (zennit batch norm canonizer fails)."
                    if incompatible else None
                ),
            })
        return result

    def load_model(self, model_name: str) -> torch.nn.Module:
        if model_name not in _IMAGE_MODELS:
            return _load_hf_image_model(model_name)["wrapper"]
        if model_name not in _loaded_models:
            model = _IMAGE_MODELS[model_name]["loader"]()
            model.eval()
            _loaded_models[model_name] = model
        return _loaded_models[model_name]

    def get_hf_label_map(self, model_name: str) -> dict:
        if model_name not in _IMAGE_MODELS:
            return _load_hf_image_model(model_name).get("label_map", {})
        return {}

    def preprocess_input(self, raw_data: Any, model_name: Optional[str] = None) -> Any:
        if model_name and model_name not in _IMAGE_MODELS:
            cache = _load_hf_image_model(model_name)
            inputs = cache["processor"](images=raw_data, return_tensors="pt")
            return inputs["pixel_values"]
        if isinstance(raw_data, Image.Image):
            return preprocess_image(raw_data)
        return raw_data

    def get_modality(self):
        from pnpxai.core.modality.modality import ImageModality
        return ImageModality()

    def render_result(self, attribution: np.ndarray, input_data: Any, output_path: str) -> str:
        if isinstance(input_data, Image.Image):
            original_array = get_original_image_array(input_data)
        else:
            original_array = None
        return render_heatmap(attribution, output_path)
