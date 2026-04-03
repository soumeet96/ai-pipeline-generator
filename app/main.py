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


@app.post("/test-github")
async def test_github(req: GenerateRequest):
    """Step-by-step GitHub API diagnostic endpoint."""
    import base64
    import httpx
    from datetime import datetime, timezone

    GITHUB_API = "https://api.github.com"
    results = {}

    try:
        path = urlparse(req.repo_url).path.strip("/")
        owner, repo = path.split("/")[:2]
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid repo_url")

    headers = {
        "Authorization": f"Bearer {req.github_token}",
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
    }

    async with httpx.AsyncClient(headers=headers, timeout=20) as client:
        # Step 1: get repo
        r = await client.get(f"{GITHUB_API}/repos/{owner}/{repo}")
        results["1_get_repo"] = {"status": r.status_code}
        if r.status_code != 200:
            return results
        default_branch = r.json()["default_branch"]
        results["1_get_repo"]["default_branch"] = default_branch

        # Step 2: get ref
        r = await client.get(f"{GITHUB_API}/repos/{owner}/{repo}/git/ref/heads/{default_branch}")
        results["2_get_ref"] = {"status": r.status_code}
        if r.status_code != 200:
            return results
        base_sha = r.json()["object"]["sha"]
        results["2_get_ref"]["base_sha"] = base_sha[:8]

        # Step 3: create branch
        branch_name = f"ai-test-{datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S')}"
        r = await client.post(
            f"{GITHUB_API}/repos/{owner}/{repo}/git/refs",
            json={"ref": f"refs/heads/{branch_name}", "sha": base_sha},
        )
        results["3_create_branch"] = {"status": r.status_code, "branch": branch_name}
        if r.status_code not in (200, 201):
            results["3_create_branch"]["error"] = r.text
            return results

        # Step 4: commit file
        content_b64 = base64.b64encode(b"# test file").decode()
        r = await client.put(
            f"{GITHUB_API}/repos/{owner}/{repo}/contents/.github/workflows/test-generated.yml",
            json={"message": "test commit", "content": content_b64, "branch": branch_name},
        )
        results["4_commit_file"] = {"status": r.status_code}
        if r.status_code not in (200, 201):
            results["4_commit_file"]["error"] = r.text

        # Cleanup: delete test branch
        await client.request(
            "DELETE",
            f"{GITHUB_API}/repos/{owner}/{repo}/git/refs/heads/{branch_name}",
        )
        results["5_cleanup"] = "branch deleted"

    return results


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
