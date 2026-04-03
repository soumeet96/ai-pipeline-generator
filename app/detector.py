"""
Reads a GitHub repository tree and detects the tech stack.
Uses the GitHub API — no cloning required.
"""

import httpx

GITHUB_API = "https://api.github.com"


async def detect_stack(owner: str, repo: str, token: str) -> dict:
    headers = {
        "Authorization": f"Bearer {token}",
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
    }

    async with httpx.AsyncClient(headers=headers, timeout=20) as client:
        # Get full file tree
        resp = await client.get(
            f"{GITHUB_API}/repos/{owner}/{repo}/git/trees/HEAD",
            params={"recursive": "1"},
        )
        resp.raise_for_status()
        files = [item["path"] for item in resp.json().get("tree", [])]

        stack = {
            "language": "unknown",
            "version": None,
            "has_dockerfile": False,
            "has_tests": False,
            "has_helm": False,
            "has_terraform": False,
            "has_existing_ci": False,
        }

        file_set = set(files)

        # Detect language
        if "package.json" in file_set:
            stack["language"] = "nodejs"
            # Try to read package.json for node version
            r = await client.get(
                f"{GITHUB_API}/repos/{owner}/{repo}/contents/package.json"
            )
            if r.status_code == 200:
                import base64, json
                content = json.loads(base64.b64decode(r.json()["content"]).decode())
                engines = content.get("engines", {})
                stack["version"] = engines.get("node", "18")
        elif any(f in file_set for f in ["requirements.txt", "pyproject.toml", "setup.py"]):
            stack["language"] = "python"
            stack["version"] = "3.12"
        elif any(f == "Cargo.toml" or f.endswith("/Cargo.toml") for f in files):
            stack["language"] = "rust"
            stack["version"] = "stable"
        elif any(f == "go.mod" or f.endswith("/go.mod") for f in files):
            stack["language"] = "go"
            stack["version"] = "1.22"
        elif any(f in file_set or any(f2.endswith(f) for f2 in files) for f in ["pom.xml", "build.gradle", "build.gradle.kts"]):
            stack["language"] = "java"
            stack["version"] = "21"

        # Detect other indicators
        stack["has_dockerfile"] = any(
            f in file_set for f in ["Dockerfile", "dockerfile"]
        )
        stack["has_tests"] = any(
            f.startswith(("test/", "tests/", "__tests__/", "spec/", "src/test/"))
            for f in files
        )
        stack["has_helm"] = any(
            f in file_set or f.startswith("helm/") or f.startswith("charts/")
            for f in ["Chart.yaml", "chart/Chart.yaml"]
        )
        stack["has_terraform"] = any(f.endswith(".tf") for f in files)
        stack["has_existing_ci"] = any(
            f.startswith(".github/workflows/") for f in files
        )

        return stack
