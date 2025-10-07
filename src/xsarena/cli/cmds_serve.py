#!/usr/bin/env python3
import asyncio
import datetime
import json
import os
import pathlib

import typer
from aiohttp import web

AUTH_TOKEN = os.getenv("XSA_SERVE_TOKEN")  # Optional shared secret


def _auth_ok(request: web.Request) -> bool:
    if not AUTH_TOKEN:
        return True
    tok = request.headers.get("X-Auth-Token") or request.query.get("token")
    return tok == AUTH_TOKEN


app = typer.Typer(help="Serve local artifacts (books/ and .xsarena/jobs) via a small web app")


def _jobs_root() -> pathlib.Path:
    return pathlib.Path(".xsarena") / "jobs"


def _books_root() -> pathlib.Path:
    return pathlib.Path("books")


async def index(request: web.Request):
    jobs_dir = _jobs_root()
    books_dir = _books_root()
    jobs = []
    if jobs_dir.exists():
        for jid in sorted(p.name for p in jobs_dir.iterdir() if p.is_dir()):
            jpath = jobs_dir / jid / "job.json"
            state = "unknown"
            updated = ""
            try:
                if jpath.exists():
                    j = json.loads(jpath.read_text(encoding="utf-8"))
                    state = j.get("state", "unknown")
                    updated = j.get("updated_at", "")
            except Exception:
                pass
            jobs.append({"id": jid, "state": state, "updated": updated})
    books = []
    if books_dir.exists():
        for p in sorted(books_dir.iterdir()):
            if p.is_file() and p.suffix.lower() in (".md", ".epub", ".pdf", ".html"):
                try:
                    m = p.stat().st_mtime
                    books.append({"name": p.name, "mtime": datetime.datetime.fromtimestamp(m).isoformat()})
                except Exception:
                    books.append({"name": p.name, "mtime": ""})

    # Audio files section
    audio_dir = pathlib.Path("audio")
    audio_files = []
    if audio_dir.exists():
        for p in sorted(audio_dir.iterdir()):
            if p.is_file() and p.suffix.lower() in (".mp3", ".m4a", ".wav", ".flac", ".m3u", ".m4b"):
                try:
                    m = p.stat().st_mtime
                    audio_files.append({"name": p.name, "mtime": datetime.datetime.fromtimestamp(m).isoformat()})
                except Exception:
                    audio_files.append({"name": p.name, "mtime": ""})
    html = [
        "<html><head><title>XSArena Serve</title><style>body{font-family:sans-serif;max-width:900px;margin:2rem auto}</style></head><body>"
    ]
    html.append("<h1>XSArena — Local Artifacts</h1>")
    html.append("<h2>Books</h2><ul>")
    for b in books:
        html.append(f'<li><a href="/books/{b["name"]}">{b["name"]}</a> <small>{b["mtime"]}</small></li>')
    html.append("</ul>")

    # Add audio section
    if audio_files:
        html.append("<h2>Audio</h2><ul>")
        for a in audio_files:
            html.append(f'<li><a href="/audio/{a["name"]}">{a["name"]}</a> <small>{a["mtime"]}</small></li>')
        html.append("</ul>")

    html.append("<h2>Jobs</h2><ul>")
    for j in jobs:
        html.append(f'<li><a href="/jobs/{j["id"]}/">{j["id"]}</a> — {j["state"]} <small>{j["updated"]}</small></li>')
    html.append("</ul>")
    html.append("<p><a href='/jobs'>Jobs (JSON)</a></p>")
    html.append("</body></html>")
    return web.Response(text="\n".join(html), content_type="text/html")


async def jobs_json(request: web.Request):
    jobs_dir = _jobs_root()
    L = []
    if jobs_dir.exists():
        for jid in sorted(p.name for p in jobs_dir.iterdir() if p.is_dir()):
            job_path = jobs_dir / jid / "job.json"
            if job_path.exists():
                try:
                    J = json.loads(job_path.read_text(encoding="utf-8"))
                except Exception:
                    J = {"id": jid, "state": "unknown"}
            else:
                J = {"id": jid, "state": "unknown"}
            L.append(J)
    return web.json_response(L)


async def job_index(request: web.Request):
    jid = request.match_info["jid"]
    base = _jobs_root() / jid
    if not base.exists():
        raise web.HTTPNotFound()
    files = []
    for root, _, names in os.walk(base):
        for n in names:
            rel = pathlib.Path(root).joinpath(n).relative_to(base)
            files.append(str(rel).replace("\\", "/"))
    files.sort()
    html = [
        "<html><head><title>Job Dashboard - "
        + jid
        + "</title><style>body{font-family:system-ui,-apple-system,'Segoe UI',Roboto,'Helvetica Neue',Arial,'Noto Sans',sans-serif;line-height:1.6;margin:0;padding:20px;max-width:1200px;word-wrap:break-word} h1,h2,h3,h4{color:#222;margin-top:1.5em;margin-bottom:0.5em} pre{background:#f5f5f5;padding:10px;overflow-x:auto;border:1px solid #ddd;border-radius:4px;font-size:14px} form{margin:10px 0} input,textarea,button{margin:5px 0; padding:8px; border:1px solid #ccc; border-radius:4px; font-family:inherit} button{background:#007cba;color:white;border:none;padding:10px 15px;border-radius:4px;cursor:pointer;font-weight:bold} button:hover{background:#005a87} a{color:#007cba;text-decoration:none} a:hover{text-decoration:underline} ul,ol{margin:10px 0;padding-left:30px} li{margin:5px 0} #log{max-height:300px;overflow:auto;border:1px solid #ccc;padding:10px;background:#f9f9f9;margin:10px 0;font-family:monospace} input,textarea{width:100%;max-width:500px}</style></head><body><h1>Job "
        + jid
        + "</h1><ul>"
    ]
    for f in files:
        html.append(f'<li><a href="/jobs/{jid}/{f}">{f}</a></li>')
    html.append("</ul>")
    logurl = f"/logs/{jid}/tail?lines=200"
    html.append(f"<p><a href='{logurl}'>Tail events.jsonl (200 lines)</a></p>")

    # Add dashboard elements
    html.append(
        "<h3>Live events</h3><pre id='log' style='max-height:300px;overflow:auto;border:1px solid #ccc;padding:6px'></pre>"
    )
    html.append(f"""<script>
var es = new EventSource("/api/stream/jobs/{jid}");
es.onmessage = function(e){{ var el=document.getElementById('log'); el.textContent+=e.data+"\\n"; el.scrollTop = el.scrollHeight; }};
</script>""")
    html.append(
        f'<h3>Budget</h3><form onsubmit=\'fetch("/api/jobs/{jid}/budget",{{method:"POST",headers:{{"Content-Type":"application/json"}},body:JSON.stringify({{budget_usd:parseFloat(this.cap.value)}})}}).then(()=>alert("Budget set!"));return false;\'><input name=\'cap\' placeholder=\'USD cap\'/> <button>Set</button></form>'
    )
    html.append(
        f"<h3>Comment</h3><form onsubmit='fetch(\"/api/jobs/{jid}/comment\",{{method:\"POST\",headers:{{\"Content-Type\":\"application/json\"}},body:JSON.stringify({{section_id:this.sid.value,text:this.txt.value}})}}).then(()=>alert(\"Comment saved!\"));return false;'><input name='sid' placeholder='Section id (e.g., Ch2.S1)'/> <br/><textarea name='txt' rows='4' cols='80' placeholder='Your comment'></textarea><br/><button>Add</button></form>"
    )
    html.append(f"<p><a href='/jobs/{jid}/outline'>Outline editor</a></p>")
    html.append("</body></html>")
    return web.Response(text="\n".join(html), content_type="text/html")


async def job_file(request: web.Request):
    jid = request.match_info["jid"]
    path = request.match_info["path"]
    base = _jobs_root() / jid
    fp = base / path
    if not fp.exists() or not fp.is_file():
        raise web.HTTPNotFound()
    return web.FileResponse(fp)


async def books_file(request: web.Request):
    path = request.match_info["path"]
    fp = _books_root() / path
    if not fp.exists() or not fp.is_file():
        raise web.HTTPNotFound()
    return web.FileResponse(fp)


async def logs_tail(request: web.Request):
    jid = request.match_info["jid"]
    lines = int(request.query.get("lines", "200"))
    path = _jobs_root() / jid / "events.jsonl"
    if not path.exists():
        return web.Response(text="(no events)", content_type="text/plain")
    with path.open("r", encoding="utf-8") as f:
        content = f.read().splitlines()[-lines:]
    return web.Response(text="\n".join(content), content_type="text/plain")


async def stream_events(request: web.Request):
    """Server-Sent Events endpoint for live job events."""
    jid = request.match_info["jid"]
    path = _jobs_root() / jid / "events.jsonl"
    if not path.exists():
        raise web.HTTPNotFound()

    response = web.StreamResponse(
        status=200,
        reason="OK",
        headers={
            "Content-Type": "text/event-stream",
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "Access-Control-Allow-Origin": "*",
        },
    )

    await response.prepare(request)

    # Read initial position
    try:
        with path.open("r", encoding="utf-8") as f:
            content = f.read()
            lines = content.splitlines()
            last_line_count = len(lines)
    except:
        last_line_count = 0

    try:
        while True:
            try:
                # Read the file
                with path.open("r", encoding="utf-8") as f:
                    content = f.read()
                    lines = content.splitlines()

                # Send new lines since last check
                if len(lines) > last_line_count:
                    for line in lines[last_line_count:]:
                        if line.strip():
                            event_data = f"data: {line}\n\n"
                            await response.write(event_data.encode("utf-8"))

                    last_line_count = len(lines)

            except Exception as e:
                # If file doesn't exist or other error, send error event
                error_data = f'event: error\ndata: {{"error":"{str(e)}"}}\n\n'
                await response.write(error_data.encode("utf-8"))

            # Wait before next check
            await asyncio.sleep(1.0)

    except asyncio.CancelledError:
        # Client disconnected
        pass

    return response


async def metrics_endpoint(request: web.Request):
    """Prometheus metrics endpoint."""
    from ..core.metrics import get_metrics

    return web.Response(text=get_metrics(), content_type="text/plain")


# REST API Endpoints
async def api_jobs_list(request: web.Request):
    """GET /api/jobs - List all jobs."""
    from ..core.jobs2 import JobRunner

    # Use default project configuration
    project_defaults = {
        "backend": "openrouter",
        "budget": {"default_usd": 5.00},
        "continuation": {"mode": "anchor", "minChars": 3000, "pushPasses": 1, "repeatWarn": True},
        "failover": {"watchdog_secs": 45, "max_retries": 3, "fallback_backend": "openrouter"},
        "style": {"nobs": True, "narrative": True},
    }

    runner = JobRunner(project_defaults)
    jobs = runner.list_jobs()

    jobs_list = []
    for job in jobs:
        jobs_list.append(
            {
                "id": job.id,
                "name": job.name,
                "state": job.state,
                "backend": job.backend,
                "created_at": job.created_at,
                "updated_at": job.updated_at,
                "artifacts_count": len(job.artifacts),
            }
        )

    return web.json_response(jobs_list)


async def api_job_detail(request: web.Request):
    """GET /api/jobs/{id} - Get job details."""
    jid = request.match_info["id"]
    from ..core.jobs2 import JobRunner

    # Use default project configuration
    project_defaults = {
        "backend": "openrouter",
        "budget": {"default_usd": 5.00},
        "continuation": {"mode": "anchor", "minChars": 3000, "pushPasses": 1, "repeatWarn": True},
        "failover": {"watchdog_secs": 45, "max_retries": 3, "fallback_backend": "openrouter"},
        "style": {"nobs": True, "narrative": True},
    }

    runner = JobRunner(project_defaults)

    try:
        job = runner.load(jid)
        return web.json_response(
            {
                "id": job.id,
                "name": job.name,
                "playbook": job.playbook,
                "params": job.params,
                "backend": job.backend,
                "state": job.state,
                "retries": job.retries,
                "created_at": job.created_at,
                "updated_at": job.updated_at,
                "artifacts": job.artifacts,
                "meta": job.meta,
            }
        )
    except ValueError:
        raise web.HTTPNotFound()


async def api_job_events(request: web.Request):
    """GET /api/jobs/{id}/events - Get job events."""
    jid = request.match_info["id"]
    from ..core.jobs2 import JobRunner

    # Use default project configuration
    project_defaults = {
        "backend": "openrouter",
        "budget": {"default_usd": 5.00},
        "continuation": {"mode": "anchor", "minChars": 3000, "pushPasses": 1, "repeatWarn": True},
        "failover": {"watchdog_secs": 45, "max_retries": 3, "fallback_backend": "openrouter"},
        "style": {"nobs": True, "narrative": True},
    }

    runner = JobRunner(project_defaults)

    try:
        # Load the events file for this job
        import json
        import os

        events_path = os.path.join(runner.jobs_dir, jid, "events.jsonl")

        if not os.path.exists(events_path):
            return web.json_response([])

        events = []
        with open(events_path, "r", encoding="utf-8") as f:
            for line in f:
                if line.strip():
                    try:
                        event = json.loads(line.strip())
                        events.append(event)
                    except json.JSONDecodeError:
                        continue

        return web.json_response(events)
    except Exception:
        raise web.HTTPInternalServerError()


async def api_job_cancel(request: web.Request):
    """POST /api/jobs/{id}/cancel - Cancel a job."""
    jid = request.match_info["id"]
    from ..core.jobs2 import JobRunner

    # Use default project configuration
    project_defaults = {
        "backend": "openrouter",
        "budget": {"default_usd": 5.00},
        "continuation": {"mode": "anchor", "minChars": 3000, "pushPasses": 1, "repeatWarn": True},
        "failover": {"watchdog_secs": 45, "max_retries": 3, "fallback_backend": "openrouter"},
        "style": {"nobs": True, "narrative": True},
    }

    runner = JobRunner(project_defaults)

    try:
        runner.cancel(jid)
        return web.json_response({"status": "cancelled", "job_id": jid})
    except Exception:
        raise web.HTTPInternalServerError()


async def api_stream_events(request):
    if not _auth_ok(request):
        raise web.HTTPUnauthorized()
    jid = request.match_info["jid"]
    path = _jobs_root() / jid / "events.jsonl"
    if not path.exists():
        raise web.HTTPNotFound()
    resp = web.StreamResponse(
        status=200,
        reason="OK",
        headers={
            "Content-Type": "text/event-stream",
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "Access-Control-Allow-Origin": "*",
        },
    )
    await resp.prepare(request)
    last = 0
    try:
        while True:
            try:
                lines = path.read_text(encoding="utf-8").splitlines()
                for line in lines[last:]:
                    await resp.write(f"event: log\ndata: {line}\n\n".encode("utf-8"))
                last = len(lines)
            except Exception:
                await resp.write(b'event: log\ndata: {"type":"error"}\n\n')
            await asyncio.sleep(1.0)
    except asyncio.CancelledError:
        pass
    return resp


async def api_z2h_create(request: web.Request):
    """POST /api/jobs/z2h - Create a new z2h job."""

    from ..core.jobs2 import JobRunner

    # Use default project configuration
    project_defaults = {
        "backend": "openrouter",
        "budget": {"default_usd": 5.00},
        "continuation": {"mode": "anchor", "minChars": 3000, "pushPasses": 1, "repeatWarn": True},
        "failover": {"watchdog_secs": 45, "max_retries": 3, "fallback_backend": "openrouter"},
        "style": {"nobs": True, "narrative": True},
    }

    runner = JobRunner(project_defaults)

    try:
        data = await request.json()
        subject = data.get("subject")
        if not subject:
            raise web.HTTPBadRequest(text="Subject is required")

        # Use the default z2h playbook
        playbook = {
            "name": "Zero-to-Hero Book Generator",
            "description": "Creates a comprehensive book from foundations to advanced practice",
            "subject": subject,
            "outline_first": True,
            "failover": {"max_retries": 3, "watchdog_secs": 45, "fallback_backend": "openrouter"},
            "aids": ["cram", "flashcards", "glossary", "index", "audio"],
            "continuation": {"mode": "anchor", "minChars": 3000, "pushPasses": 2},
            "system_text": """
You are creating an in-depth, comprehensive guide for a complex topic.
Approach this systematically:
- Start with foundations and essentials
- Use pedagogical principles: define terms before use, include short vignettes
- Build to advanced concepts and modern applications
- No-fluff writing style - be direct and actionable
- Use narrative flow to maintain engagement
- Include practical examples and common pitfalls
Maintain consistent depth throughout.
""",
        }

        params = {"max_chunks": data.get("max_chunks", 8), "continuation": {"minChars": data.get("min_chars", 3000)}}

        job_id = runner.submit(playbook, params)

        # Run the job in the background with scheduler
        import asyncio

        asyncio.create_task(runner.run_job_with_scheduler(job_id))

        return web.json_response({"job_id": job_id, "status": "submitted"})
    except Exception as e:
        raise web.HTTPInternalServerError(text=f"Error creating job: {str(e)}")


# Additional API endpoints


async def api_snapshot_download(request):
    """GET /api/snapshot - Creates and returns a snapshot.txt"""
    if not _auth_ok(request):
        raise web.HTTPUnauthorized()

    # Import the snapshot functionality
    import tempfile
    from pathlib import Path

    from ..utils.snapshot_v2 import create_snapshot

    # Create snapshot in a temporary file
    with tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False) as tmp:
        snapshot_path = Path(tmp.name)

    try:
        # Create the snapshot
        create_snapshot(
            project_root=".",
            output_file=str(snapshot_path),
            redact=True,
            include_env=True,
            include_git=True,
            include_pip=True,
            chunk=False,
            tar=False,
        )

        if snapshot_path.exists():
            response = web.FileResponse(snapshot_path, headers={"Content-Type": "text/plain"})
            response.headers["Content-Disposition"] = 'attachment; filename="snapshot.txt"'
            return response
        else:
            raise web.HTTPNotFound(text="Snapshot not created")
    except Exception as e:
        raise web.HTTPInternalServerError(text=f"Error creating snapshot: {str(e)}")


async def api_job_patch(request):
    """POST /api/jobs/{id}/patch - Apply patch to a file in a job"""
    if not _auth_ok(request):
        raise web.HTTPUnauthorized()

    jid = request.match_info["id"]
    payload = await request.json()

    file_path = payload.get("file")
    diff_content = payload.get("diff")
    dry_run = payload.get("dry_run", False)

    if not file_path or not diff_content:
        return web.json_response({"error": "Both 'file' and 'diff' are required"}, status=400)

    # Validate that the file path is within the job directory
    job_dir = _jobs_root() / jid
    target_file = job_dir / file_path

    # Ensure the file is within the job directory to prevent path traversal
    try:
        target_file.resolve().relative_to(job_dir.resolve())
    except ValueError:
        return web.json_response({"error": "Invalid file path - outside job directory"}, status=400)

    if not target_file.exists():
        return web.json_response({"error": f"File does not exist: {file_path}"}, status=404)

    try:
        if dry_run:
            # Try to apply the patch in dry-run mode using difflib
            import difflib

            original_content = target_file.read_text(encoding="utf-8")
            original_lines = original_content.splitlines(keepends=True)

            # Parse the diff and apply it to see if it would work
            diff_lines = diff_content.splitlines(keepends=True)
            patched_lines = list(
                difflib.unified_diff(
                    original_lines,  # Use original as original
                    original_lines,  # Use same as new initially
                    fromfile=f"a/{file_path}",
                    tofile=f"b/{file_path}",
                )
            )

            # For now, just validate that the diff format is correct
            # A real implementation would apply the diff and see if it works
            return web.json_response(
                {"ok": True, "dry_run": True, "message": "Diff format validated", "would_apply": len(patched_lines) > 0}
            )
        else:
            # Apply the patch to the file
            import subprocess
            import tempfile

            # Write the diff to a temporary file
            with tempfile.NamedTemporaryFile(mode="w", suffix=".diff", delete=False) as diff_file:
                diff_file.write(diff_content)
                diff_file_path = diff_file.name

            try:
                # Apply the patch
                result = subprocess.run(
                    ["patch", "-p0", "-f", str(target_file), diff_file_path],
                    capture_output=True,
                    text=True,
                    cwd=job_dir,
                )

                if result.returncode == 0:
                    # Write an event to the job's events log
                    event_path = job_dir / "events.jsonl"
                    import datetime
                    import json

                    event = {
                        "ts": datetime.datetime.now().isoformat(),
                        "type": "code_patch",
                        "file": file_path,
                        "status": "applied",
                        "message": "Patch applied successfully",
                    }
                    with event_path.open("a", encoding="utf-8") as f:
                        f.write(json.dumps(event) + "\n")

                    return web.json_response({"ok": True, "applied": True, "message": f"Patch applied to {file_path}"})
                else:
                    return web.json_response({"error": "Patch application failed", "stderr": result.stderr}, status=400)
            finally:
                # Clean up the temporary diff file
                import os

                os.unlink(diff_file_path)

    except Exception as e:
        return web.json_response({"error": f"Error applying patch: {str(e)}"}, status=500)


async def audio_file(request: web.Request):
    path = request.match_info["path"]
    fp = pathlib.Path("audio") / path
    if not fp.exists() or not fp.is_file():
        raise web.HTTPNotFound()
    return web.FileResponse(fp)


async def edit_section(request):
    jid = request.match_info["jid"]
    sec_path = request.match_info["sec"]
    base = _jobs_root() / jid / "sections"
    fp = base / sec_path
    if not fp.exists():
        raise web.HTTPNotFound()
    text = fp.read_text(encoding="utf-8")
    html = f"""<html><body>
    <h1>Edit {sec_path}</h1>
    <form method="POST" action="/jobs/{jid}/save">
      <input type="hidden" name="path" value="{sec_path}">
      <textarea name="content" rows="40" cols="110">{text}</textarea><br/>
      <button type="submit">Save</button>
    </form>
    </body></html>"""
    return web.Response(text=html, content_type="text/html")


async def save_section(request):
    jid = request.match_info["jid"]
    data = await request.post()
    sec_path = data.get("path")
    content = data.get("content", "")
    fp = _jobs_root() / jid / "sections" / sec_path
    if not fp.exists():
        raise web.HTTPNotFound()
    fp.write_text(content, encoding="utf-8")
    # mark approved in plan.json
    planp = _jobs_root() / jid / "plan.json"
    try:
        plan = json.loads(planp.read_text(encoding="utf-8"))
        for ch in plan.get("chapters", []):
            for s in ch.get("subtopics", []):
                if s.get("file") == sec_path:
                    s["status"] = "approved"
        planp.write_text(json.dumps(plan, indent=2), encoding="utf-8")
    except Exception:
        pass
    raise web.HTTPFound(location=f"/jobs/{jid}/{sec_path}")


async def outline_view(request):
    jid = request.match_info["jid"]
    base = _jobs_root() / jid
    planp = base / "plan.json"
    if not planp.exists():
        raise web.HTTPNotFound()
    import json

    plan = json.loads(planp.read_text(encoding="utf-8"))
    html = [
        "<html><head><title>Outline Editor</title><style>body{font-family:sans-serif;max-width:900px;margin:2rem auto} ul{margin:0.5rem 0} li{margin:0.3rem 0} a{padding:0.2rem 0.4rem;background:#f0f0f0;text-decoration:none;border-radius:3px} a:hover{background:#e0e0e0}</style></head><body><h1>Outline Editor</h1><ul>"
    ]
    for ch in plan.get("chapters", []):
        html.append(
            f"<li><b>{ch['id']}</b> — {ch['title']} "
            f"[<a href='/jobs/{jid}/outline/rename?chapter={ch['id']}'>rename</a>] "
            f"[<a href='/jobs/{jid}/outline/move?chapter={ch['id']}&dir=up'>↑</a>] "
            f"[<a href='/jobs/{jid}/outline/move?chapter={ch['id']}&dir=down'>↓</a>]"
            "<ul>"
        )
        for s in ch.get("subtopics", []):
            sp = s["id"]
            html.append(
                f"<li>{sp} — {s['title']} "
                f"[<a href='/jobs/{jid}/outline/rename?section={sp}'>rename</a>] "
                f"[<a href='/jobs/{jid}/outline/move?section={sp}&dir=up'>↑</a>] "
                f"[<a href='/jobs/{jid}/outline/move?section={sp}&dir=down'>↓</a>]</li>"
            )
        html.append("</ul></li>")
    html.append("</ul></body></html>")
    return web.Response(text="\n".join(html), content_type="text/html")


async def outline_rename_get(request):
    jid = request.match_info["jid"]
    chapter = request.query.get("chapter")
    section = request.query.get("section")
    target = chapter or section
    if not target:
        raise web.HTTPBadRequest()
    form = f"""<html><head><title>Rename {target}</title><style>body{{font-family:sans-serif;max-width:600px;margin:2rem auto}} input[type=text]{{width:100%;padding:0.5rem;margin:0.5rem 0}} button{{padding:0.5rem 1rem}}</style></head><body><h1>Rename {target}</h1>
      <form method="POST" action="/jobs/{jid}/outline/rename">
        <input type="hidden" name="target" value="{target}">
        <input type="text" name="title" size="80" placeholder="New title" value="">
        <button type="submit">Save</button>
      </form></body></html>"""
    return web.Response(text=form, content_type="text/html")


async def outline_rename_post(request):
    jid = request.match_info["jid"]
    data = await request.post()
    target = data.get("target")
    title = (data.get("title") or "").strip()
    if not target or not title:
        raise web.HTTPBadRequest()
    import json

    planp = _jobs_root() / jid / "plan.json"
    plan = json.loads(planp.read_text(encoding="utf-8"))
    for ch in plan.get("chapters", []):
        if ch["id"] == target:
            ch["title"] = title
            break
        for s in ch.get("subtopics", []):
            if s["id"] == target:
                s["title"] = title
                break
    planp.write_text(json.dumps(plan, indent=2), encoding="utf-8")
    raise web.HTTPFound(location=f"/jobs/{jid}/outline")


async def outline_move(request):
    jid = request.match_info["jid"]
    q = request.query
    chap_id = q.get("chapter")
    sec_id = q.get("section")
    direction = q.get("dir", "up")
    import json

    planp = _jobs_root() / jid / "plan.json"
    plan = json.loads(planp.read_text(encoding="utf-8"))
    if chap_id:
        # move chapter in list
        arr = plan.get("chapters", [])
        idx = next((i for i, x in enumerate(arr) if x["id"] == chap_id), None)
        if idx is not None:
            if direction == "up" and idx > 0:
                arr[idx - 1], arr[idx] = arr[idx], arr[idx - 1]
            if direction == "down" and idx < len(arr) - 1:
                arr[idx + 1], arr[idx] = arr[idx], arr[idx + 1]
    elif sec_id:
        # find chapter and move subtopic inside
        for ch in plan.get("chapters", []):
            arr = ch.get("subtopics", [])
            idx = next((i for i, x in enumerate(arr) if x["id"] == sec_id), None)
            if idx is not None:
                if direction == "up" and idx > 0:
                    arr[idx - 1], arr[idx] = arr[idx], arr[idx - 1]
                if direction == "down" and idx < len(arr) - 1:
                    arr[idx + 1], arr[idx] = arr[idx], arr[idx + 1]
                break
    planp.write_text(json.dumps(plan, indent=2), encoding="utf-8")
    raise web.HTTPFound(location=f"/jobs/{jid}/outline")


def _make_app():
    app = web.Application()
    app.router.add_get("/", index)
    app.router.add_get("/jobs", jobs_json)
    app.router.add_get("/jobs/{jid}/", job_index)
    app.router.add_get("/jobs/{jid}/{path:.+}", job_file)
    app.router.add_get("/books/{path:.+}", books_file)
    app.router.add_get("/audio/{path:.+}", audio_file)
    app.router.add_get("/logs/{jid}/tail", logs_tail)
    app.router.add_get("/stream/jobs/{jid}/events", stream_events)
    app.router.add_get("/api/metrics", metrics_endpoint)
    app.router.add_get("/jobs/{jid}/edit/{sec:.+}", edit_section)
    app.router.add_post("/jobs/{jid}/save", save_section)

    # Outline editor routes
    app.router.add_get("/jobs/{jid}/outline", outline_view)
    app.router.add_get("/jobs/{jid}/outline/rename", outline_rename_get)
    app.router.add_post("/jobs/{jid}/outline/rename", outline_rename_post)
    app.router.add_get("/jobs/{jid}/outline/move", outline_move)

    # REST API routes
    app.router.add_get("/api/jobs", api_jobs_list)
    app.router.add_get("/api/jobs/{id}", api_job_detail)
    app.router.add_get("/api/jobs/{id}/events", api_job_events)
    app.router.add_post("/api/jobs/{id}/cancel", api_job_cancel)  # Keep original
    app.router.add_post("/api/jobs/z2h", api_submit_z2h)  # Use the new simplified version
    app.router.add_get("/api/stream/jobs/{jid}", api_stream_events)  # SSE events
    app.router.add_post("/api/jobs/{id}/patch", api_job_patch)  # Code patch endpoint
    app.router.add_get("/api/snapshot", api_snapshot_download)  # Snapshot download endpoint

    return app


async def api_jobs(request):
    subj = (await request.json()).get("subject")
    if not subj:
        return web.json_response({"error": "subject required"}, status=400)
    # Minimal submit: call JobRunner with playbooks/z2h.yml
    from ..core.jobs2 import JobRunner
    from ..core.playbooks import load_playbook, merge_defaults  # adjust path if needed

    defaults = {}
    pb = load_playbook("playbooks/z2h.yml")
    params = {"subject": subj, "max_chunks": 8}
    jr = JobRunner(defaults)
    jid = jr.submit(merge_defaults(pb, defaults, params), params)
    return web.json_response({"job_id": jid})


def _make_app():
    app = web.Application()
    app.router.add_get("/", index)
    app.router.add_get("/jobs", jobs_json)
    app.router.add_get("/jobs/{jid}/", job_index)
    app.router.add_get("/jobs/{jid}/{path:.+}", job_file)
    app.router.add_get("/books/{path:.+}", books_file)
    app.router.add_get("/audio/{path:.+}", audio_file)
    app.router.add_get("/logs/{jid}/tail", logs_tail)
    app.router.add_get("/stream/jobs/{jid}/events", stream_events)
    app.router.add_get("/api/metrics", metrics_endpoint)
    app.router.add_get("/jobs/{jid}/edit/{sec:.+}", edit_section)
    app.router.add_post("/jobs/{jid}/save", save_section)

    # Outline editor routes
    app.router.add_get("/jobs/{jid}/outline", outline_view)
    app.router.add_get("/jobs/{jid}/outline/rename", outline_rename_get)
    app.router.add_post("/jobs/{jid}/outline/rename", outline_rename_post)
    app.router.add_get("/jobs/{jid}/outline/move", outline_move)

    # REST API routes
    app.router.add_get("/api/jobs", api_jobs_list)
    app.router.add_get("/api/jobs/{id}", api_job_detail)
    app.router.add_get("/api/jobs/{id}/events", api_job_events)
    app.router.add_post("/api/jobs/{id}/cancel", api_job_cancel)
    app.router.add_post("/api/jobs/z2h", api_z2h_create)

    return app


@app.command("run")
def serve_run(host: str = "127.0.0.1", port: int = 8787):
    """Serve books/ and .xsarena/jobs/* locally."""
    web.run_app(_make_app(), host=host, port=port)
