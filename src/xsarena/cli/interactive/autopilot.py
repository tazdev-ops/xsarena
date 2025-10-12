#!/usr/bin/env python3
"""
Autopilot functions extracted from interactive.py
"""

import asyncio
import os

from lma_stream import (
    build_anchor_continue_prompt,
    jaccard_ngrams,
    strip_next_marker,
)


async def autorun_loop(state):
    """
    Args:
        state: dict containing all shared state and functions needed by the autorun loop
    """
    # Extract state variables
    AUTO_ON = state["AUTO_ON"]
    AUTO_COUNT = state["AUTO_COUNT"]
    LAST_NEXT_HINT = state.get("LAST_NEXT_HINT")
    NEXT_OVERRIDE = state.get("NEXT_OVERRIDE")
    AUTO_PAUSE = state.get("AUTO_PAUSE", False)
    AUTO_OUT = state.get("AUTO_OUT")
    AUTO_MAX = state.get("AUTO_MAX")
    AUTO_DELAY = state.get("AUTO_DELAY", 1.0)
    CONT_MODE = state.get("CONT_MODE", "anchor")
    CONT_ANCHOR_CHARS = state.get("CONT_ANCHOR_CHARS", 200)
    REPEAT_WARN = state.get("REPEAT_WARN", True)
    REPEAT_THRESH = state.get("REPEAT_THRESH", 0.35)
    REPEAT_NGRAM = state.get("REPEAT_NGRAM", 4)
    SESSION_MODE = state.get("SESSION_MODE")
    COVERAGE_HAMMER_ON = state.get("COVERAGE_HAMMER_ON", True)
    OUTPUT_PUSH_ON = state.get("OUTPUT_PUSH_ON", True)
    OUTPUT_MIN_CHARS = state.get("OUTPUT_MIN_CHARS", 4500)
    OUTPUT_PUSH_MAX_PASSES = state.get("OUTPUT_PUSH_MAX_PASSES", 3)

    # Functions
    send_and_collect = state["send_and_collect"]
    build_payload = state["build_payload"]
    continuation_anchor = state["continuation_anchor"]
    anchor_from_text = state["anchor_from_text"]
    any_end_marker = state["any_end_marker"]
    write_to_file = state["write_to_file"]
    book_save = state["book_save"]
    ok = state.get("ok", print)
    warn = state.get("warn", print)

    # Lists/dicts that need to be mutable
    HISTORY = state["HISTORY"]
    SAVE_SYSTEM_STACK = state.get("SAVE_SYSTEM_STACK", [])

    first = True
    while state["AUTO_ON"] and (AUTO_MAX is None or AUTO_COUNT < AUTO_MAX):
        # Pause support
        while state["AUTO_ON"] and state.get("AUTO_PAUSE", False):
            await asyncio.sleep(0.2)
        if not state["AUTO_ON"]:
            break

        # Decide next prompt
        if first:
            user_text = "BEGIN"
            first = False
        else:
            if state.get("NEXT_OVERRIDE"):
                user_text = state["NEXT_OVERRIDE"]
                state["NEXT_OVERRIDE"] = None
            elif CONT_MODE == "anchor":
                anch = continuation_anchor(CONT_ANCHOR_CHARS)
                if anch:
                    user_text = build_anchor_continue_prompt(anch)
                    if SESSION_MODE == "zero2hero" and COVERAGE_HAMMER_ON:
                        user_text += (
                            "\nDo not conclude or summarize; coverage is not complete. "
                            "Continue teaching the field and its subfields to the target depth."
                        )
                else:
                    user_text = "continue."
            else:
                user_text = "continue."

        print()
        print(
            f"{state.get('C_USER', '')}{state.get('C_B', '')}You{state.get('C_R', '')}: {user_text}\n"
        )

        # First segment
        reply = await send_and_collect(build_payload(user_text))
        body, hint = strip_next_marker(reply)  # strip NEXT from main body; capture hint
        state["LAST_NEXT_HINT"] = hint

        # Auto-extend within the same subtopic to hit OUTPUT_MIN_CHARS
        accumulated = body
        local_hint = hint
        micro = 0
        while (
            OUTPUT_PUSH_ON
            and len(accumulated) < OUTPUT_MIN_CHARS
            and micro < OUTPUT_PUSH_MAX_PASSES
            and state["AUTO_ON"]
        ):
            # Build a local anchor from the accumulated text (not from full HISTORY)
            local_anch = anchor_from_text(accumulated, CONT_ANCHOR_CHARS)
            ext_prompt = (
                build_anchor_continue_prompt(local_anch)
                + "\nFill to the per-response output limit within this same subtopic. "
                "Do not reintroduce or restart; continue exactly. "
                "Do not write a NEXT line yet; do not conclude."
            )
            print()
            print(
                f"{state.get('C_USER', '')}{state.get('C_B', '')}You{state.get('C_R', '')}: [extend] {ext_prompt}\n"
            )
            ext_reply = await send_and_collect(build_payload(ext_prompt))
            ext_body, ext_hint = strip_next_marker(
                ext_reply
            )  # strip any premature NEXT
            if not ext_body.strip():
                break
            # Optional repetition guard: stop if highly repetitive vs last portion
            if REPEAT_WARN:
                prev_tail = anchor_from_text(
                    accumulated, min(800, CONT_ANCHOR_CHARS * 4)
                )
                rep = jaccard_ngrams(
                    prev_tail, ext_body[: max(400, CONT_ANCHOR_CHARS)], n=REPEAT_NGRAM
                )
                if rep > REPEAT_THRESH:
                    warn(
                        f"High repetition during extension (Jaccard~{rep:.2f}). Stopping extend; you may /next steer."
                    )
                    break
            accumulated += ("\n\n" if not accumulated.endswith("\n") else "") + ext_body
            if ext_hint:  # keep only the last NEXT if the final step later adds it
                local_hint = ext_hint
            micro += 1

        # Now use the accumulated text as the final body for this iteration
        final_body = accumulated
        final_hint = local_hint

        # Persist to history and file
        HISTORY.append({"role": "user", "content": user_text})
        HISTORY.append({"role": "assistant", "content": final_body})
        if AUTO_OUT:
            write_to_file(AUTO_OUT, final_body)

        # Optional repetition detection (vs previous chunk)
        if REPEAT_WARN:
            prev_tail = continuation_anchor(min(800, CONT_ANCHOR_CHARS * 4))
            rep = jaccard_ngrams(
                prev_tail, final_body[: max(400, CONT_ANCHOR_CHARS)], n=REPEAT_NGRAM
            )
            if rep > REPEAT_THRESH:
                warn(
                    f"High repetition detected (Jaccard~{rep:.2f}). Auto-pausing. Use /next to steer or /book.resume."
                )
                state["AUTO_PAUSE"] = True

        state["AUTO_COUNT"] += 1

        # Auto-save checkpoint
        if AUTO_COUNT % 5 == 0 or not state["AUTO_ON"]:
            await book_save(os.path.basename(AUTO_OUT).replace(".md", ""), state=state)

        # Stop on explicit END
        if (
            any_end_marker(reply)
            or any_end_marker(final_body)
            or (
                final_hint and final_hint.upper() in {"END", "DONE", "STOP", "FINISHED"}
            )
        ):
            ok("NEXT: [END] detected — stopping.")
            state["AUTO_ON"] = False
            break

        # Carry hint forward (we do not inject hint text into the next prompt, we rely on anchors)
        state["LAST_NEXT_HINT"] = final_hint

        await asyncio.sleep(AUTO_DELAY)

    ok(
        f"Autopilot finished after {state['AUTO_COUNT']} chunk(s). Output: {AUTO_OUT or '(none)'}"
    )
    if SAVE_SYSTEM_STACK:
        sys_old = SAVE_SYSTEM_STACK.pop()
        # We can't call set_system here without passing it, so we'll assume the caller handles this
