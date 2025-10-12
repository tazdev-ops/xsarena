# Safe Commands

## Pre-approved Linux patterns for grep/find/sed/jq/yq:

### File discovery:
- `find . -type f -name "*.py" -not -path "./.git/*" -not -path "./books/*"`
- `find . -maxdepth 2 -type d | sort`
- `find . -name "__pycache__" -type d -exec rm -rf {} +`

### Text search (exclude heavy dirs):
- `grep -RIn --line-number --binary-files=without-match --exclude-dir={.git,__pycache__,books,node_modules,dist,build,snapshot_chunks} "PATTERN" .`
- `grep -nC2 "PATTERN" FILE`
- `grep -RIn "PATTERN" . | wc -l`

### Text processing:
- `sed -i 's/old/new/g' FILE`
- `head -n 60 FILE; tail -n 60 FILE`
- `wc -lc FILE; du -h FILE; stat -c '%s %n' FILE`

### JSON/YAML processing:
- `jq '.key' file.json`
- `yq '.path' file.yml`

### Output redirection:
- `grep -RIn "PATTERN" . | tee ./review/search_PATTERN.txt`
- `find . -type f -name "*.py" > python_files.txt`

### Always use timeouts:
- `timeout 15s find . -name "__pycache__" -type d`
- `timeout 60s grep -RIn "PATTERN" .`
