# XAI Demo Platform

Interactive eXplainable AI demo platform for image classification. Upload an image, select a pre-trained model and XAI explainers, and visualize heatmap explanations with quality metrics.

## Features

- **Drag-and-drop image upload** with preview
- **3 pre-trained models**: ResNet-50, VGG-16, DenseNet-121 (ImageNet)
- **5 XAI algorithms**: LRP, Guided Grad-CAM, LIME, Integrated Gradients, KernelSHAP
- **3 evaluation metrics**: Correctness, Continuity, Compactness
- **Results ranked by Correctness** with side-by-side heatmap comparison
- **Progressive results** - see each explainer's output as it completes

## Tech Stack

- **Frontend**: Next.js 14 + TypeScript + Tailwind CSS
- **Backend**: FastAPI + PyTorch + Captum (XAI)
- **Metrics**: Faithfulness Correlation, Continuity, Sparseness

## Quick Start

### Backend

```bash
cd backend
pip install -r requirements.txt
uvicorn backend.main:app --reload
```

Server runs at http://localhost:8000

### Frontend

```bash
cd frontend
npm install
npm run dev
```

App runs at http://localhost:3000

## Architecture

```
User uploads image
  -> Frontend sends to FastAPI backend
  -> Backend loads pre-trained model
  -> Runs inference (Top-K predictions)
  -> For each selected XAI algorithm:
     -> Computes attribution map (via Captum)
     -> Computes 3 metrics
     -> Renders heatmap overlay
  -> Results returned progressively via polling
  -> Frontend displays ranked heatmaps + metrics
```

## API Endpoints

| Method | Path | Description |
|--------|------|-------------|
| GET | /api/models | List available models |
| GET | /api/explainers | List available explainers |
| POST | /api/explain | Submit analysis job |
| GET | /api/jobs/{id} | Get job status + results |
| GET | /api/jobs/{id}/heatmaps/{name}.png | Get heatmap image |

## Notes

- LRP is only compatible with VGG-16 (requires nn.Sequential architecture)
- LIME and KernelSHAP are slower (~20-30s on CPU) due to perturbation-based approach
- Backend uses `run_in_executor` to keep the API responsive during computation
