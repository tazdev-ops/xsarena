# Glossary

## Core Terms

### Autopilot
- A loop that sends "BEGIN" then continues from an anchor chunk by chunk, writing to a file

### Anchor
- The tail ~N characters of the last assistant output that are injected into the next prompt to maintain continuity

### Hammer
- Anti-wrap continuation hint for self-study; prevents the model from wrapping up sections prematurely

### Repetition Guard
- Jaccard n-gram similarity checking between the last tail and the new head of output to avoid loops

### Chunk
- A segment of text output from the AI model, typically within token limits

### Mastery Profile
- Settings for maximally comprehensive content equivalent to master's level depth

### SNAPSHOT+JOBS
- Advanced snapshot mode that includes minimal job context for debugging

### Compressed Overlay
- Style that produces dense prose with no drills or checklists

## CLI Concepts

### Continuation
- Strategy for maintaining flow between chunks; can be normal or anchor mode

### Output Budget
- System addendum that pushes the model to use its full token window

### Push Passes
- In-chunk micro-continues to reach a minimal length

### Density Knobs
- Settings like /out.minchars, /out.passes that control output characteristics# Bridge Userscript Guide

## Tampermonkey Best Practices

### @connect Rules
- Use host-only permissions instead of wildcards when possible
- Example: `// @connect lmarena.ai` instead of `// @connect *`
- This improves security and reduces permission requests

### HTTP Requests
- Use GM_xmlhttpRequest for cross-origin requests
- Ensure proper headers are set for API communication
- Handle errors gracefully in the userscript

### Security Considerations
- Limit @connect to required domains only
- Avoid @connect * unless absolutely necessary
- Test on HTTP endpoints if HTTPS causes issues

### Bridge Configuration
- BASE port: Default is usually 8080 or similar
- Ensure browser and CLI are using same port configuration
- Check firewall settings if bridge server isn't accessible

### Retry Capture Steps
1. Run `/capture` in CLI
2. Click "Retry" once in the browser on the target chat
3. CLI should receive session and message IDs
4. Verify connection with `/status`
