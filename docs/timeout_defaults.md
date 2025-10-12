# Timeout Defaults

## SHORT ops (ls/find/grep/cat small files): timeout 15s <cmd>

## NORMAL ops (snapshot, small xsarena commands, grep -R): timeout 60s <cmd>

## HEAVY ops (xsarena doctor run, large synth, publish/audio): timeout 180s <cmd> (max 300s unless operator approves)

## Examples:
- `timeout 15s grep -RIn "PATTERN" .`
- `timeout 60s xsarena snapshot run --chunk`
- `timeout 180s xsarena doctor run --subject "Smoke" --max 2 --min 800`

## macOS note: if timeout is missing, use gtimeout (coreutils). If neither, ask before running.
