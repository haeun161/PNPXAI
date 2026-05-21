import torch
import torchvision.models as models
import numpy as np
from typing import Any
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

# Explainers compatible with image classification
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
        return [
            {"name": e["name"], "display_name": e["display_name"],
             "estimated_compute_time_seconds": e["estimated_time"],
             "compatible": True, "incompatibility_reason": None}
            for e in _IMAGE_EXPLAINERS
        ]

    def load_model(self, model_name: str) -> torch.nn.Module:
        if model_name not in _IMAGE_MODELS:
            raise ValueError(f"Unknown image model: {model_name}")
        if model_name not in _loaded_models:
            model = _IMAGE_MODELS[model_name]["loader"]()
            model.eval()
            _loaded_models[model_name] = model
        return _loaded_models[model_name]

    def preprocess_input(self, raw_data: Any) -> Any:
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
