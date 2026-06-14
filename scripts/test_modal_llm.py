import argparse

from openai import OpenAI


def main() -> None:
    parser = argparse.ArgumentParser(description="Test an OpenAI-compatible Modal vLLM endpoint.")
    parser.add_argument("--base-url", required=True, help="Endpoint base URL, for example https://...modal.run/v1")
    parser.add_argument("--model", required=True, help="Served model name, for example minicpm-1b")
    parser.add_argument("--prompt", default="Reply with one short sentence confirming the service works.")
    args = parser.parse_args()

    client = OpenAI(base_url=args.base_url.rstrip("/") + "/", api_key="EMPTY")
    extra_body = None
    if args.model.lower().startswith("qwen"):
        extra_body = {"top_k": 20, "chat_template_kwargs": {"enable_thinking": False}}
    elif "nemotron" in args.model.lower():
        extra_body = {"chat_template_kwargs": {"enable_thinking": False}}
    response = client.chat.completions.create(
        model=args.model,
        messages=[{"role": "user", "content": args.prompt}],
        temperature=0.2,
        max_tokens=128,
        extra_body=extra_body,
    )
    print(response.choices[0].message.content)


if __name__ == "__main__":
    main()
