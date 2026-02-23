# ML Model Build & Deployment

## Overview

The answer evaluator uses a fine-tuned DistilBERT sentence transformer converted to ONNX format for Lambda deployment. ONNX eliminates the `torch`/`sentence_transformers` dependency, reducing the Docker image from ~2GB to ~1.3GB.

## Artifacts

| Path | Description |
|------|-------------|
| `final_similarity_model/` | Original trained model (safetensors format, ~255MB) - source of truth |
| `final_similarity_model_onnx/` | ONNX export used by Lambda (~253MB) - committed to git |
| `src/shared/model_utils.py` | Model loading/inference via `onnxruntime` |
| `lambda/answer-evaluator/lambda_function.py` | Lambda handler |
| `lambda/answer-evaluator/Dockerfile` | Copies `final_similarity_model_onnx/` into image |

## Re-exporting the Model to ONNX

Run this when `final_similarity_model/` is retrained or updated.

**Prerequisites:**
```bash
pip install sentence-transformers optimum[exporters] onnx
```

**Export:**
```python
from optimum.exporters.onnx import main_export

main_export(
    model_name_or_path="./final_similarity_model",
    output="./final_similarity_model_onnx",
    task="feature-extraction",
    opset=14,
)
```

After export, verify `final_similarity_model_onnx/` contains `model.onnx` plus tokenizer files (`tokenizer.json`, `vocab.txt`, `config.json`, etc.).

## Verifying the Export

Quick smoke test before committing:
```python
import onnxruntime as ort
import numpy as np
from transformers import AutoTokenizer

tokenizer = AutoTokenizer.from_pretrained("./final_similarity_model_onnx")
session = ort.InferenceSession("./final_similarity_model_onnx/model.onnx")

enc = tokenizer(["hello world"], return_tensors="np", padding=True, truncation=True)
outputs = session.run(None, {
    "input_ids": enc["input_ids"].astype(np.int64),
    "attention_mask": enc["attention_mask"].astype(np.int64),
})
print("Output shape:", outputs[0].shape)  # expect (1, seq_len, 768)
```

## How Inference Works

`ModelManager` in `src/shared/model_utils.py`:
1. Loads `model.onnx` via `onnxruntime.InferenceSession`
2. Tokenizes input with `transformers.AutoTokenizer`
3. Runs inference, applies mean pooling + L2 normalization
4. Returns cosine similarity via `sklearn`

Model is loaded once at Lambda cold start and cached for the container lifetime.

## Local Docker Test

```bash
docker build -f lambda/answer-evaluator/Dockerfile -t answer-evaluator-test .
docker run --rm answer-evaluator-test python3 -c "
import sys; sys.path.insert(0, '/var/task')
from lambda_function import handler
print(handler({'httpMethod':'GET','path':'/health','headers':{},'body':None}, {}))
"
```

## CI/CD

ONNX model files are committed to git (Git LFS on Gitea). On every push to `main`, the Gitea pipeline builds the Docker image and deploys via CDK → ECR → Lambda.

The first deploy after a model update will be slow (~10-20 min) due to the 1.3GB image push to ECR.
