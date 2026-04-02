"""
Generates a tailored GitHub Actions CI/CD pipeline using Groq (Llama 3.3).
"""

import json
import urllib.request
import urllib.error
import os

GROQ_API_URL = "https://api.groq.com/openai/v1/chat/completions"
MODEL = "llama-3.3-70b-versatile"


def build_prompt(stack: dict, owner: str, repo: str) -> str:
    indicators = []
    if stack["has_dockerfile"]:
        indicators.append("- Has a Dockerfile (include docker build + push steps)")
    if stack["has_tests"]:
        indicators.append("- Has a test suite (include a test step)")
    if stack["has_helm"]:
        indicators.append("- Has Helm charts (include helm lint step)")
    if stack["has_terraform"]:
        indicators.append("- Has Terraform (include terraform validate step)")
    if stack["has_existing_ci"]:
        indicators.append("- Already has CI workflows (generate a complementary one)")

    indicators_text = "\n".join(indicators) if indicators else "- No special indicators found"

    return f"""You are a senior DevOps engineer. Generate a production-grade GitHub Actions CI/CD pipeline.

Repository: {owner}/{repo}
Language: {stack["language"]} {stack.get("version") or ""}

Detected indicators:
{indicators_text}

Requirements:
- Output ONLY valid GitHub Actions YAML, nothing else — no markdown fences, no explanation
- Use pinned action versions (e.g. actions/checkout@v4)
- Include caching for dependencies where applicable
- Add security best practices (minimal permissions, no hardcoded secrets)
- Keep it practical and clean — a real engineer would use this as-is"""


def call_groq(prompt: str) -> str:
    api_key = os.environ.get("GROQ_API_KEY")
    if not api_key:
        raise RuntimeError("GROQ_API_KEY not set")

    payload = {
        "model": MODEL,
        "messages": [{"role": "user", "content": prompt}],
        "temperature": 0.2,
        "max_tokens": 2048,
    }

    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(
        GROQ_API_URL,
        data=data,
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
            "User-Agent": "ai-pipeline-generator/1.0",
        },
        method="POST",
    )

    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            result = json.loads(resp.read().decode("utf-8"))
            return result["choices"][0]["message"]["content"].strip()
    except urllib.error.HTTPError as e:
        body = e.read().decode("utf-8")
        raise RuntimeError(f"Groq API error {e.code}: {body}") from e


def generate_pipeline(stack: dict, owner: str, repo: str) -> str:
    prompt = build_prompt(stack, owner, repo)
    return call_groq(prompt)


def review_pipeline(pipeline_yaml: str, stack: dict) -> str:
    api_key = os.environ.get("GROQ_API_KEY")
    if not api_key:
        raise RuntimeError("GROQ_API_KEY not set")

    prompt = f"""You are a senior DevOps engineer reviewing a generated CI/CD pipeline.

Stack: {stack["language"]} {stack.get("version") or ""}

Pipeline to review:
```yaml
{pipeline_yaml}
```

Give a concise review covering:
1. **Security** — missing permissions scoping, exposed secrets, unsafe patterns
2. **Best Practices** — caching, pinned versions, job structure
3. **Summary** — one line verdict (Looks Good / Minor Issues / Needs Changes)

Be specific. Keep it under 250 words. Format as Markdown."""

    payload = {
        "model": MODEL,
        "messages": [{"role": "user", "content": prompt}],
        "temperature": 0.2,
        "max_tokens": 512,
    }

    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(
        GROQ_API_URL,
        data=data,
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
            "User-Agent": "ai-pipeline-generator/1.0",
        },
        method="POST",
    )

    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            result = json.loads(resp.read().decode("utf-8"))
            return result["choices"][0]["message"]["content"].strip()
    except urllib.error.HTTPError as e:
        body = e.read().decode("utf-8")
        raise RuntimeError(f"Groq API error {e.code}: {body}") from e
