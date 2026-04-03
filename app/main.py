"""
AI Pipeline Generator — FastAPI application
POST /generate  → reads repo, generates CI/CD pipeline, opens PR with AI review
GET  /health    → health check
"""

from urllib.parse import urlparse

from fastapi import FastAPI, HTTPException
from fastapi.responses import PlainTextResponse
from pydantic import BaseModel

from app.detector import detect_stack
from app.generator import generate_pipeline, review_pipeline
from app.pr_opener import open_pr

app = FastAPI(title="AI Pipeline Generator", version="1.0.0")


class GenerateRequest(BaseModel):
    repo_url: str
    github_token: str


@app.get("/health")
async def health():
    return {"status": "ok"}




@app.post("/generate", response_class=PlainTextResponse)
async def generate(req: GenerateRequest):
    # Parse owner/repo from URL
    try:
        path = urlparse(req.repo_url).path.strip("/")
        owner, repo = path.split("/")[:2]
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid repo_url. Use https://github.com/owner/repo format.")

    try:
        # Step 1 — Detect stack
        stack = await detect_stack(owner, repo, req.github_token)

        # Step 2 — Generate pipeline
        pipeline_yaml = generate_pipeline(stack, owner, repo)

        # Step 3 — AI review of the generated pipeline
        ai_review = review_pipeline(pipeline_yaml, stack)

        # Step 4 — Open PR with pipeline + post review comment
        pr_url = await open_pr(owner, repo, req.github_token, pipeline_yaml, ai_review)

        # Extract one-line summary from AI review (last line with verdict)
        summary_line = next(
            (line for line in ai_review.splitlines() if "Summary" in line or "verdict" in line.lower()),
            "Review posted on PR"
        )

        # Step 5 — Return clean human-readable output
        yes_no = lambda v: "Yes" if v else "No"
        output = f"""
✅  Stack Detected
    Language   : {stack["language"].capitalize()} {stack.get("version") or ""}
    Tests      : {yes_no(stack["has_tests"])}
    Dockerfile : {yes_no(stack["has_dockerfile"])}
    Helm       : {yes_no(stack["has_helm"])}
    Terraform  : {yes_no(stack["has_terraform"])}
    Existing CI: {yes_no(stack["has_existing_ci"])}

🔧  Pipeline Generated
    File       : .github/workflows/ci-generated.yml
    Tailored for {stack["language"].capitalize()} stack

🔗  Pull Request Opened
    {pr_url}

🤖  AI Review Posted
    {summary_line.strip()}
    Full review is posted as a comment on the PR above.
"""
        return output.strip()

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
