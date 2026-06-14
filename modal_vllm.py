import json
import subprocess

import modal


APP_NAME = "ezjob-vllm"
VLLM_PORT = 8000
MINUTES = 60
WARM_CONTAINERS = 1

QWEN_MODEL = "Qwen/Qwen3.5-27B-FP8"
NEMOTRON_MODEL = "nvidia/NVIDIA-Nemotron-3-Nano-30B-A3B-BF16"

vllm_image = (
    modal.Image.from_registry("nvidia/cuda:12.9.0-devel-ubuntu22.04", add_python="3.12")
    .entrypoint([])
    .uv_pip_install("vllm==0.21.0", "huggingface_hub", "hf_transfer", "openai")
    .env(
        {
            "HF_HUB_ENABLE_HF_TRANSFER": "1",
            "HF_XET_HIGH_PERFORMANCE": "1",
            "VLLM_LOG_STATS_INTERVAL": "10",
        }
    )
)

hf_cache_vol = modal.Volume.from_name("ezjob-huggingface-cache", create_if_missing=True)
vllm_cache_vol = modal.Volume.from_name("ezjob-vllm-cache", create_if_missing=True)

app = modal.App(APP_NAME)


@app.function(
    image=vllm_image,
    gpu="L40S:1",
    timeout=20 * MINUTES,
    min_containers=WARM_CONTAINERS,
    scaledown_window=10 * MINUTES,
    volumes={
        "/root/.cache/huggingface": hf_cache_vol,
        "/root/.cache/vllm": vllm_cache_vol,
    },
    secrets=[modal.Secret.from_name("huggingface-secret")],
)
@modal.concurrent(max_inputs=32)
@modal.web_server(port=VLLM_PORT, startup_timeout=20 * MINUTES)
def qwen():
    _serve_vllm(
        model=QWEN_MODEL,
        served_model_name="qwen3.5-27b-fp8",
        max_model_len=32768,
        max_num_seqs=8,
        extra_args=[
            "--trust-remote-code",
            "--gpu-memory-utilization",
            "0.92",
            "--kv-cache-dtype",
            "fp8",
            "--reasoning-parser",
            "qwen3",
            "--language-model-only",
        ],
    )


@app.function(
    image=vllm_image,
    gpu="L40S:2",
    timeout=20 * MINUTES,
    min_containers=WARM_CONTAINERS,
    scaledown_window=10 * MINUTES,
    volumes={
        "/root/.cache/huggingface": hf_cache_vol,
        "/root/.cache/vllm": vllm_cache_vol,
    },
    secrets=[modal.Secret.from_name("huggingface-secret")],
)
@modal.concurrent(max_inputs=32)
@modal.web_server(port=VLLM_PORT, startup_timeout=20 * MINUTES)
def nemotron():
    _serve_vllm(
        model=NEMOTRON_MODEL,
        served_model_name="nemotron-3-nano-30b-bf16",
        max_model_len=32768,
        max_num_seqs=8,
        tensor_parallel_size=2,
        extra_args=[
            "--trust-remote-code",
            "--gpu-memory-utilization",
            "0.92",
            "--kv-cache-dtype",
            "fp8",
            "--enable-auto-tool-choice",
            "--tool-call-parser",
            "hermes",
        ],
    )


def _serve_vllm(
    model: str,
    served_model_name: str,
    max_model_len: int,
    max_num_seqs: int,
    tensor_parallel_size: int = 1,
    extra_args: list[str] | None = None,
) -> None:
    cmd = [
        "vllm",
        "serve",
        model,
        "--served-model-name",
        served_model_name,
        model,
        "--host",
        "0.0.0.0",
        "--port",
        str(VLLM_PORT),
        "--uvicorn-log-level",
        "info",
        "--tensor-parallel-size",
        str(tensor_parallel_size),
        "--max-model-len",
        str(max_model_len),
        "--max-num-seqs",
        str(max_num_seqs)
    ]
    cmd.extend(extra_args or [])
    print("Starting vLLM:", json.dumps(cmd))
    subprocess.Popen(cmd)


@app.local_entrypoint()
async def urls():
    print("Qwen:", await qwen.get_web_url.aio())
    print("Nemotron:", await nemotron.get_web_url.aio())
