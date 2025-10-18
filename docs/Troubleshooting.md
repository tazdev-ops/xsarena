# Troubleshooting

This document covers common issues and their solutions when using XSArena.

## Cloudflare Protection

If you encounter Cloudflare protection pages:

1. Manually solve the CAPTCHA in your browser
2. Wait a few minutes before trying again
3. Consider using a different IP address if the issue persists
4. Check that your session is still valid in the AI platform

## ID Capture Issues

If session or message IDs are not captured:

1. Ensure the userscript is enabled for the correct domain
2. Verify that you clicked 'Retry' in the browser after starting ID capture
3. Check that the bridge server is running on `http://127.0.0.1:5102`
4. Confirm that your AI platform session is active when attempting capture

## Stream Timeouts

For stream timeouts during generation:

1. Check your internet connection
2. Verify the AI backend is responsive
3. Consider reducing the `minChars` setting to create smaller chunks
4. Increase timeout settings in your configuration if needed

## Resume-Safe Jobs

XSArena jobs are designed to be resume-safe:

- Job state is saved in `.xsarena/jobs/<job_id>/`
- If interrupted, use `xsarena jobs resume <job_id>` to continue
- Events are logged to `events.jsonl` for debugging
- Partial content is preserved in the output file

## Common Configuration Issues

If you're having configuration problems:

1. Run `xsarena doctor` to check system health
2. Verify `.xsarena/config.yml` contains valid settings
3. Check that API keys (if required) are properly set as environment variables
4. Ensure the bridge userscript is properly installed and enabled
