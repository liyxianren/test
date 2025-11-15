"""
Quick demo script for calling Zhipu ChatGLM (glm-4.6) in CBT context.

Usage:
    pip install zai-sdk
    python demo_zhipu.py

The script reads API key/model from environment variables, falling back to
the sample values provided in .env.
"""
import os
from zai import ZhipuAiClient  # type: ignore


def main() -> None:
    api_key = os.getenv(
        "ZHIPU_API_KEY",
        "acc95d604f5041f79f7e0d15058e3ba4.ZAzj5m76OXEsTpu4",
    )
    model = os.getenv("ZHIPU_MODEL_NAME", "glm-4.6")

    client = ZhipuAiClient(api_key=api_key)

    prompt = """你是一名 CBT 情绪教练。请阅读下面的日记内容，
根据认知行为疗法输出一个 JSON，包含总体情绪、情绪强度（0-1）、
关键情绪、可能的认知偏差以及 2 条行动建议。

日记：今天工作又被领导批评，我觉得自己一无是处，也担心明天再被点名。"""

    try:
        response = client.chat.completions.create(
            model=model,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.7,
        )
    except Exception as exc:
        print("调用 ChatGLM 失败：", exc)
        return

    print("Raw response:")
    print(response)
    print("\nAssistant output:")
    print(response.choices[0].message.content)


if __name__ == "__main__":
    main()
