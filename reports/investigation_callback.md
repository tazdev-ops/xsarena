# Investigation: app.callback() and CLIContext initialization

## Current state
- [x] app.callback() exists in registry.py at line 27
- [x] CLIContext.load() works standalone

## 73e8878 state
no callback in 73e8878 registry.py

## Conclusion
The app.callback() was added after commit 73e8878, so the claim about missing callback is outdated. The callback exists and CLIContext works.
