#!/usr/bin/env python3
import json, os, sys, urllib.request, urllib.error

GROQ_API_URL = "https://api.groq.com/openai/v1/chat/completions"
MODEL = "llama-3.3-70b-versatile"
MAX_DIFF_CHARS = 12000

SYSTEM_PROMPT = """You are a senior DevOps engineer performing a code review.
Analyze the provided git diff and give a concise, actionable review covering:
1. **Security** — secrets, vulnerabilities, unsafe patterns
2. **DevOps / Infrastructure** — Dockerfile, CI/CD, config concerns
3. **Code Quality** — logic errors, edge cases, improvements
4. **Summary** — Approve / Request Changes / Needs Discussion
Be specific. Format as Markdown. Keep it under 400 words."""

def main():
    api_key = os.environ.get("GROQ_API_KEY")
    if not api_key:
        print("Error: GROQ_API_KEY not set", file=sys.stderr); sys.exit(1)

    diff = open(sys.argv[1], encoding="utf-8", errors="replace").read()
    if len(diff) > MAX_DIFF_CHARS:
        diff = diff[:MAX_DIFF_CHARS] + "\n\n[diff truncated]"

    if not diff.strip():
        print("## AI Review\n\nNo changes detected."); return

    payload = {
        "model": MODEL,
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": f"Review this diff:\n\n```diff\n{diff}\n```"},
        ],
        "temperature": 0.3, "max_tokens": 1024,
    }
    req = urllib.request.Request(
        GROQ_API_URL, json.dumps(payload).encode(),
        {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json", "User-Agent": "ai-pipeline-generator/1.0"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            review = json.loads(r.read())["choices"][0]["message"]["content"]
    except urllib.error.HTTPError as e:
        print(f"Groq error {e.code}: {e.read().decode()}", file=sys.stderr); sys.exit(1)

    print(f"## 🤖 AI Code Review (Groq + Llama 3.3)\n\n{review}\n\n---\n*[ai-pipeline-generator](https://github.com/soumeet96/ai-pipeline-generator)*")

if __name__ == "__main__":
    main()
