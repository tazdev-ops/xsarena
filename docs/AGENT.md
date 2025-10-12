# Agent Journal System

## Overview
The agent journal system provides session continuity by maintaining a log of interactions and decisions. This enables resumption of work with full context preservation.

## Journal Structure
- Location: `.xsarena/agent/journal.jsonl`
- Format: JSONL (JSON Lines) - one JSON object per line
- Rotation: Automatic at 1MB to prevent excessive growth

## Journal Entry Format
Each entry contains:
- `timestamp`: ISO 8601 formatted time
- `type`: Entry type (command, decision, result, note, etc.)
- `content`: The actual content or command
- `context`: Relevant context for the entry

## Continuity Features
- On startup, the system reads the last 20 lines of the journal
- Provides a summary of recent activity
- Enables context-aware responses

## Best Practices
- Keep entries concise but informative
- Include relevant context for future reference
- Use structured data where possible# Agent Environment Variables

## XSA_QUALITY_PROFILE
- Values: pedagogy | compressed
- Purpose: Controls quality profile (affects penalties for drills/checklists)

## XSA_USE_PTK
- Values: 0 | 1 (default: 1)
- Purpose: Disable PTK interface (set to 0 for fallback REPL)

## OPENROUTER_API_KEY
- Purpose: API key for OpenRouter backend
- Security: Never commit to repository

## XSA_ROUTER_BACKEND
- Purpose: Router backend configuration

## LITELLM_BASE
- Purpose: Base URL for LiteLLM router

## LITELLM_API_KEY
- Purpose: API key for LiteLLM router
