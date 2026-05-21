import os
import numpy as np
import torch

from backend.tasks import get_task_handler
from backend.core.pnpxai_adapter import normalize_attribution, extract_metric_value
from backend.core.job_manager import (
    get_uploaded_data, update_job_status, update_job_predictions,
    update_job_result, VISUALIZATION_DIR,
)

# ImageNet class labels
_imagenet_labels: list[str] = []


def _load_imagenet_labels() -> list[str]:
    global _imagenet_labels
    if _imagenet_labels:
        return _imagenet_labels
    try:
        from torchvision.models import ResNet50_Weights
        weights = ResNet50_Weights.IMAGENET1K_V2
        _imagenet_labels = list(weights.meta["categories"])
    except Exception:
        _imagenet_labels = [str(i) for i in range(1000)]
    return _imagenet_labels


def _get_pnpxai_explainer(name: str):
    """Dynamically get a PnPXAI explainer class by name."""
    from pnpxai import explainers as exp_mod
    cls = getattr(exp_mod, name, None)
    if cls is None:
        raise ValueError(f"PnPXAI explainer not found: {name}")
    return cls


def _get_pnpxai_metric(name: str, model, explainer_instance=None):
    """Instantiate a PnPXAI metric by name."""
    from pnpxai.evaluator import metrics as met_mod
    cls = getattr(met_mod, name, None)
    if cls is None:
        raise ValueError(f"PnPXAI metric not found: {name}")
    return cls(model=model, explainer=explainer_instance)


def run_explanation_pipeline(
    job_id: str,
    task: str,
    model_name: str,
    explainer_names: list[str],
    ranking_metric: str,
    params: dict,
):
    """Synchronous pipeline - runs in thread pool executor via run_in_executor."""
    try:
        update_job_status(job_id, "running")

        handler = get_task_handler(task)

        # Step 1: Load model
        model = handler.load_model(model_name)

        # Step 2: Load and preprocess input
        raw_data = get_uploaded_data(job_id)
        if raw_data is None:
            update_job_status(job_id, "failed", "Uploaded data not found.")
            return

        input_data = handler.preprocess_input(raw_data)

        # Step 3: Run inference for predictions (image classification only for now)
        if task == "image":
            input_tensor = input_data
            model.eval()
            with torch.no_grad():
                output = model(input_tensor)
                probabilities = torch.softmax(output, dim=1)[0]
                top5_probs, top5_indices = torch.topk(probabilities, min(5, len(probabilities)))

            labels = _load_imagenet_labels()
            target_class = top5_indices[0].item()

            predictions = [
                {"class_name": labels[idx.item()] if idx.item() < len(labels) else str(idx.item()),
                 "probability": round(prob.item() * 100, 2)}
                for prob, idx in zip(top5_probs, top5_indices)
            ]
            update_job_predictions(job_id, predictions)
        else:
            target_class = 0
            input_tensor = input_data if isinstance(input_data, torch.Tensor) else None

        # Step 4-8: For each explainer
        job_dir = os.path.join(VISUALIZATION_DIR, job_id)
        os.makedirs(job_dir, exist_ok=True)

        all_results = []

        for exp_name in explainer_names:
            exp_info = next((e for e in handler.get_explainers(model_name) if e["name"] == exp_name), None)
            display_name = exp_info["display_name"] if exp_info else exp_name

            update_job_result(job_id, {
                "explainer_name": exp_name,
                "display_name": display_name,
                "status": "running",
            })

            try:
                # Get PnPXAI explainer class and instantiate
                ExplainerClass = _get_pnpxai_explainer(exp_name)
                explainer_instance = ExplainerClass(model)

                # Compute attribution
                if input_tensor is not None:
                    inp = input_tensor.clone().requires_grad_(True)
                    target_tensor = torch.tensor([target_class], dtype=torch.long)
                    # PnPXAI uses positional (inputs, targets) - avoid keyword arg issues
                    try:
                        attribution_raw = explainer_instance.attribute(inp, target_tensor)
                    except TypeError:
                        # Fallback: some explainers may use keyword
                        attribution_raw = explainer_instance.attribute(inputs=inp, targets=target_tensor)
                    attribution = normalize_attribution(attribution_raw)
                else:
                    attribution = np.zeros(10)

                # Compute metrics - signature: evaluate(inputs, targets, attributions)
                metric_values = {}
                for metric_name in ["MuFidelity", "AbPC", "Sensitivity", "Complexity"]:
                    try:
                        metric_instance = _get_pnpxai_metric(metric_name, model, explainer_instance)
                        if input_tensor is not None:
                            result = metric_instance.evaluate(
                                input_tensor.clone(), target_tensor, attribution_raw
                            )
                            metric_values[metric_name.lower()] = extract_metric_value(result)
                        else:
                            metric_values[metric_name.lower()] = None
                    except Exception as me:
                        import traceback
                        traceback.print_exc()
                        metric_values[metric_name.lower()] = None

                # Render visualization
                viz_path = os.path.join(job_dir, f"{exp_name}.png")
                handler.render_result(attribution, raw_data, viz_path)

                result_entry = {
                    "explainer_name": exp_name,
                    "display_name": display_name,
                    "status": "completed",
                    "visualization_url": f"/api/jobs/{job_id}/visualizations/{exp_name}.png",
                    "mu_fidelity": round(metric_values.get("mufidelity") or 0, 4) if metric_values.get("mufidelity") is not None else None,
                    "abpc": round(metric_values.get("abpc") or 0, 4) if metric_values.get("abpc") is not None else None,
                    "sensitivity": round(metric_values.get("sensitivity") or 0, 4) if metric_values.get("sensitivity") is not None else None,
                    "complexity": round(metric_values.get("complexity") or 0, 4) if metric_values.get("complexity") is not None else None,
                }
                all_results.append(result_entry)
                update_job_result(job_id, result_entry)

            except Exception as e:
                import traceback
                traceback.print_exc()
                result_entry = {
                    "explainer_name": exp_name,
                    "display_name": display_name,
                    "status": "failed",
                    "error_message": str(e),
                }
                all_results.append(result_entry)
                update_job_result(job_id, result_entry)

        # Step 9: Rank results by user-selected metric (descending, higher = better)
        # "average" = mean of mu_fidelity (as accuracy), sensitivity, complexity
        def _rank_score(r):
            if ranking_metric == "average":
                vals = [r.get(k) for k in ["mu_fidelity", "sensitivity", "complexity"] if r.get(k) is not None]
                return sum(vals) / len(vals) if vals else 0
            return r.get(ranking_metric, 0) or 0

        completed = [r for r in all_results if r["status"] == "completed"]
        completed.sort(key=_rank_score, reverse=True)
        for i, r in enumerate(completed):
            r["rank"] = i + 1
            update_job_result(job_id, r)

        update_job_status(job_id, "completed")

    except Exception as e:
        update_job_status(job_id, "failed", str(e))
