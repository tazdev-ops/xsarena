# Troubleshooting Guide

## Bridge Capture Issues
- Tampermonkey @connect rules: ensure proper domain access
- Host-only @connect: use host-only permissions instead of wildcard
- HTTP only: Some sites may require HTTP permissions
- BASE port: Check that the bridge server is running on the expected port
- Retry capture steps: Click "Retry" once in browser after capture command

## Stalls and Cloudflare
- Cancel stream: Ctrl+C once (if using PTK)
- Check Cloudflare status: `/cf.status`
- Solve challenge and resume: `/cf.resume` → `/book.resume`
- Reduce window size: `/window 60` or lower

## OpenRouter Status
- Verify API key is set: Check OPENROUTER_API_KEY environment variable
- Test connection: `/or.status`
- Check model availability: `/or.model openrouter/auto`

## Repetitive Output
- Enable repetition guard: `/repeat.warn on`
- Adjust threshold: `/repeat.thresh 0.35`
- Lower passes: Reduce `/out.passes` value
- Adjust min chars: Tweak `/out.minchars`

## Density Settings
- Dense output: `/out.budget off`; `/out.minchars 2500-3200`; `/out.passes 0-1`
- Terse output: `/out.budget on`; `/out.minchars 4500-5200`; `/out.passes 2-3`

## Crash Paths
- Unknown commands in PTK: Set `XSA_USE_PTK=0` to use fallback REPL
- Server startup on Windows: Allow Python through firewall on Private networks only
- Output not in English: Add "English only" to system prompt# Security Note

## Content Policy
- All generated content should be SFW/PG-13 appropriate
- No test security violations or cheating materials
- Respect academic integrity in all outputs

## Secrets Management
- Never commit API keys, tokens, or secrets to repository
- Keep OPENROUTER_API_KEY and other credentials in environment variables
- Do not include secrets in README or documentation files
- Sanitize snapshots to remove sensitive information

## Data Privacy
- When using OpenRouter, prompts/outputs go to selected model provider
- Do not send sensitive data you aren't comfortable sharing with providers
- Bridge backend streams via browser; treat browser session as authenticated

## Responsible Use
- Use AI-generated content responsibly
- Verify accuracy of generated materials before use
- Be aware of potential AI biases in generated content
