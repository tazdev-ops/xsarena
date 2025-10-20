# Snapshot Fix Playbook (only if necessary)

Use this only when policy/config can't solve your issue (e.g., hard crash). Keep changes surgical; don't expand scope.

1) TOML parsing crash (TypeError: str expected by tomllib.loads)
- Symptom: xsarena ops snapshot write — crashes when .snapshot.toml exists.
- Root cause: tomllib.loads expects bytes; code calls read_text.
- Surgical fix (guidance):
  - File: xsarena/utils/snapshot_simple.py, read_snapshot_config()
  - Ensure the TOML is read as bytes:
    data = tomllib.loads(config_path.read_bytes())
  - Or:
    with open(config_path, "rb") as f:
        data = tomllib.load(f)

2) mode=max NameError (exclude_patterns not set)
- Symptom: collect_paths("max") raises NameError on exclude_patterns.
- Surgical fix:
  - File: xsarena/utils/snapshot_simple.py, collect_paths()
  - When mode == "max", set:
    include_patterns = ["**/*"]; exclude_patterns = []

3) Best-effort git context (builder shouldn't crash in non-git dirs)
- Symptom: write tries to gather git info and errors out.
- Surgical fix:
  - File: xsarena/utils/snapshot_simple.py, build_git_context()
  - Wrap subprocess calls in try/except and return a friendly string ("Git: (Not a git repository)") on failure.

4) Binary/text handling clarity
- If builder emits undecodable text:
  - File: xsarena/utils/snapshot_simple.py, write_text_snapshot/write_zip_snapshot()
  - Ensure is_binary_sample(b) detection remains as the gate. If binary, write a metadata line "[BINARY FILE] size=… sha256=…".

5) Redaction toggle safety
- If redaction can't be applied for some reason, it should not crash; fallback to unredacted text or warn clearly.
  - Keep any redaction errors non-fatal; proceed with unredacted text + note in output.

Post-fix acceptance
- Minimal and maximal flows run without exceptions.
- Verify preflight or postflight returns "OK" under the policy you set.
- No secrets leaked (txt redaction on; verify preflight passes "secrets" check).
