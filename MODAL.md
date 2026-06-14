# Modal vLLM Deployment

This project can use Modal-hosted vLLM servers through the existing OpenAI-compatible `LLMClient`.

## Models

- Qwen: `Qwen/Qwen3.5-27B-FP8`, served as `qwen3.5-27b-fp8`
- Nemotron: `nvidia/NVIDIA-Nemotron-3-Nano-30B-A3B-BF16`, served as `nemotron-3-nano-30b-bf16`

The deployment keeps one container warm per model with `min_containers=1`, so both endpoints avoid cold starts after deploy. Qwen uses one L40S. Nemotron BF16 uses two L40S GPUs with tensor parallel size 2. This means the warm containers continue running while deployed.

The server is launched with `--language-model-only` because EZ JOB uses text-only agents. App requests pass `chat_template_kwargs={"enable_thinking": false}` so Qwen returns direct parser/optimizer output instead of visible reasoning traces.

## Setup

```bash
uv run --with modal modal setup
```

Create a Modal secret for Hugging Face access. This is required for gated or license-accepted models and is still useful for reliable downloads.

```bash
uv run --with modal modal secret create huggingface-secret HF_TOKEN=hf_your_token_here
```

## Deploy

```bash
uv run --with modal modal deploy modal_vllm.py
```

Print the deployed endpoint URLs:

```bash
uv run --with modal modal run modal_vllm.py
```

Modal will print the Qwen and Nemotron URLs. Append `/v1` when using either as an OpenAI-compatible base URL.

## Test

```bash
uv run --with openai python scripts/test_modal_llm.py \
  --base-url "https://YOUR-WORKSPACE--ezjob-vllm-qwen.modal.run/v1" \
  --model "qwen3.5-27b-fp8"

uv run --with openai python scripts/test_modal_llm.py \
  --base-url "https://YOUR-WORKSPACE--ezjob-vllm-nemotron.modal.run/v1" \
  --model "nemotron-3-nano-30b-bf16"
```

## Use In EZ JOB

Choose Qwen or Nemotron in the UI model selector. You can still override the default model in `.env`:

```env
MODEL__NAME=qwen3.5-27b-fp8
MODEL__BASE_URL=https://YOUR-WORKSPACE--ezjob-vllm-qwen.modal.run/v1
MODEL__TEMPERATURE=0.3
```
