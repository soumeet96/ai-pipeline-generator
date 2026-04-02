# AI Pipeline Generator

An AI agent that reads any GitHub repository, detects its tech stack, generates a production-grade CI/CD pipeline tailored to that codebase, opens a PR, and posts an AI review — all in one command.

[![CI](https://github.com/soumeet96/ai-pipeline-generator/actions/workflows/ci.yml/badge.svg)](https://github.com/soumeet96/ai-pipeline-generator/actions/workflows/ci.yml)

---

## What it does

```
You give it a GitHub repo URL + your token
        ↓
Reads the actual code — detects language, tests, Dockerfile, Helm, Terraform
        ↓
Groq (Llama 3.3 70B) generates a tailored GitHub Actions pipeline
        ↓
Opens a PR on your repo with the pipeline file
        ↓
Posts an AI review comment on that same PR
        ↓
Returns a clean summary in your terminal
```

---

## Demo

```bash
curl -X POST https://ai-pipeline-generator.onrender.com/generate \
  -H "Content-Type: application/json" \
  -d '{
    "repo_url": "https://github.com/owner/repo",
    "github_token": "ghp_your_token_here"
  }'
```

**Output:**
```
✅  Stack Detected
    Language   : Node.js 18
    Tests      : Yes
    Dockerfile : Yes
    Helm       : No
    Terraform  : No
    Existing CI: No

🔧  Pipeline Generated
    File       : .github/workflows/ci-generated.yml
    Tailored for Node.js stack

🔗  Pull Request Opened
    https://github.com/owner/repo/pull/1

🤖  AI Review Posted
    Summary: Looks Good — minor caching improvement suggested
    Full review is posted as a comment on the PR above.
```

---

## Supported Stacks

| Language | Detected via |
|---|---|
| Node.js | `package.json` |
| Python | `requirements.txt`, `pyproject.toml` |
| Rust | `Cargo.toml` |
| Go | `go.mod` |
| Java | `pom.xml`, `build.gradle` |

Also detects: Dockerfile, test suites, Helm charts, Terraform configs, existing CI workflows.

---

## Tech Stack

- **API:** Python FastAPI + Uvicorn
- **AI:** Groq API (Llama 3.3 70B) — free tier
- **GitHub integration:** GitHub REST API (repo reading + PR creation)
- **Containerization:** Docker
- **CI/CD:** GitHub Actions → GHCR
- **Deployment:** Render.com (free tier)

---

## Running Locally

```bash
export GROQ_API_KEY=your_key_here
docker compose up --build
# API available at http://localhost:8000
```

---

## Architecture

```
POST /generate
      │
      ▼
detector.py — GitHub API → reads repo tree → detects stack
      │
      ▼
generator.py — Groq API → generates tailored pipeline YAML
      │
      ▼
generator.py — Groq API → reviews the generated pipeline
      │
      ▼
pr_opener.py — GitHub API → creates branch → commits file → opens PR → posts review comment
      │
      ▼
Plain text summary returned to caller
```

---

## Author

**Soumeet Acharya** — [github.com/soumeet96](https://github.com/soumeet96)
