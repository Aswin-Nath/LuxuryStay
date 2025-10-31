import os
import time
import base64
import asyncio
from uuid import uuid4

import httpx
from fastapi import UploadFile

# Primary external upload endpoint; can be overridden with env var IMAGE_UPLOAD_API
EXTERNAL_API = os.getenv("IMAGE_UPLOAD_API", "https://image-upload-backend-v12y.onrender.com/upload")


async def save_uploaded_image(image: UploadFile) -> str:
    """Upload an image to the configured external upload API with retries and
    a GitHub fallback.

    This function no longer accepts an image_name from the caller. A random
    human-friendly name is generated internally for storage purposes.

    Behavior:
    - Try the external upload endpoint with exponential backoff until a 60s
      deadline is reached.
    - If external upload fails, and GITHUB_TOKEN + GITHUB_UPLOAD_REPO are set,
      upload the image file into the repo using the GitHub Contents API and
      return a raw.githubusercontent URL.

    Environment variables (optional):
    - IMAGE_UPLOAD_API: external service URL (default kept for compatibility)
    - GITHUB_TOKEN: personal access token for repo uploads
    - GITHUB_UPLOAD_REPO: owner/repo (e.g. myorg/myrepo)
    - GITHUB_UPLOAD_PATH: path inside repo where images are stored (default 'images')
    - GITHUB_BRANCH: branch to commit to (default 'main')
    """

    def _generate_random_name() -> str:
        import secrets

        adjectives = [
            "bright", "calm", "eager", "fancy", "gentle", "happy", "jolly", "kind",
            "lucky", "merry", "nice", "proud", "quick", "sly", "tidy", "vivid",
        ]
        nouns = [
            "sun", "lake", "field", "breeze", "stone", "cloud", "leaf", "river",
            "peak", "meadow", "orchard", "garden", "harbor", "island", "grove", "trail",
        ]
        return f"{secrets.choice(adjectives)}-{secrets.choice(nouns)}-{uuid4().hex[:8]}"

    unique_name = _generate_random_name()
    form_data = {"image_name": unique_name}
    content = await image.read()

    # Total time we are willing to wait for the external service to become available
    total_timeout = 60.0
    deadline = time.time() + total_timeout
    backoff = 1.0

    async with httpx.AsyncClient(timeout=httpx.Timeout(total_timeout)) as client:
        # Retry loop until deadline
        while True:
            try:
                files = {"image": (image.filename, content, image.content_type)}
                resp = await client.post(EXTERNAL_API, data=form_data, files=files)
                if resp.status_code == 200:
                    # Expecting JSON with 'url'
                    data = resp.json()
                    url = data.get("url")
                    if url:
                        return url
                    else:
                        raise Exception(f"External upload returned no url: {data}")
                else:
                    # Treat non-200 as transient and retry until deadline
                    err = f"External upload failed ({resp.status_code}): {resp.text}"
                    raise Exception(err)
            except (httpx.RequestError, Exception):
                # If deadline exceeded, break and try fallback
                now = time.time()
                if now + backoff > deadline:
                    break
                await asyncio.sleep(backoff)
                backoff = min(backoff * 2, 10.0)

    # Fallback: try uploading to GitHub repository if configured
    github_token = os.getenv("GITHUB_TOKEN")
    github_repo = os.getenv("GITHUB_UPLOAD_REPO")
    github_path = os.getenv("GITHUB_UPLOAD_PATH", "images").lstrip("/")
    github_branch = os.getenv("GITHUB_BRANCH", "main")

    if github_token and github_repo:
        try:
            owner, repo = github_repo.split("/", 1)
        except Exception:
            raise Exception("GITHUB_UPLOAD_REPO must be in 'owner/repo' format")

        filename = f"{unique_name}_{image.filename}"
        path = f"{github_path.rstrip('/')}/{filename}" if github_path else filename

        url = f"https://api.github.com/repos/{owner}/{repo}/contents/{path}"
        headers = {"Authorization": f"token {github_token}", "Accept": "application/vnd.github+json"}
        payload = {
            "message": f"Add image {filename}",
            "content": base64.b64encode(content).decode(),
            "branch": github_branch,
        }

        async with httpx.AsyncClient(timeout=httpx.Timeout(total_timeout)) as client:
            resp = await client.put(url, json=payload, headers=headers)
            if resp.status_code in (200, 201):
                j = resp.json()
                # Prefer the raw/download URL if GitHub provides it
                download = j.get("content", {}).get("download_url")
                if download:
                    return download
                # Construct raw.githubusercontent URL as a fallback
                return f"https://raw.githubusercontent.com/{owner}/{repo}/{github_branch}/{path}"
            else:
                raise Exception(f"GitHub upload failed ({resp.status_code}): {resp.text}")

    raise Exception("All upload attempts failed: external service unreachable and no GitHub fallback configured")
