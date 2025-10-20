# src/xsarena/bridge_v2/payload_converter.py
import json
import random


async def convert_openai_to_lmarena_payload(
    openai_data: dict,
    session_id: str,
    message_id: str,
    model_name: str,
    model_name_to_id_map: dict,
    model_endpoint_map: dict,
    config: dict,
) -> dict:
    messages = openai_data.get("messages", [])

    target_model_id = model_name_to_id_map.get(model_name)

    # Handle role mapping: merge 'developer' role into 'system'
    processed_messages = []
    for msg in messages:
        role = msg.get("role", "")
        content = msg.get("content", "")

        # Map 'developer' role to 'system'
        if role == "developer":
            role = "system"

        processed_messages.append({"role": role, "content": content})

    # Determine mode and target from per-model mapping or config
    mode = "direct_chat"  # default
    battle_target = "a"  # default

    # Check if model has specific endpoint mapping with mode/battle_target
    if model_name in model_endpoint_map:
        endpoint_config = model_endpoint_map[model_name]
        if isinstance(endpoint_config, list):
            # If it's a list, pick randomly
            endpoint_config = random.choice(endpoint_config)

        if isinstance(endpoint_config, dict):
            # Prefer mapping values if provided
            if "mode" in endpoint_config and endpoint_config["mode"] is not None:
                mode = endpoint_config["mode"]
            if (
                "battle_target" in endpoint_config
                and endpoint_config["battle_target"] is not None
            ):
                battle_target = endpoint_config["battle_target"]

    # If not set by mapping, read from config keys
    if mode == "direct_chat":  # Only update if still default
        config_mode = config.get("id_updater_last_mode")
        if config_mode:
            mode = config_mode

    if battle_target == "a":  # Only update if still default
        config_battle_target = config.get("id_updater_battle_target")
        if config_battle_target:
            battle_target = config_battle_target

    # Apply tavern mode logic if enabled
    tavern_mode_enabled = config.get("tavern_mode_enabled", False)
    bypass_enabled = config.get("bypass_enabled", False)

    # Separate messages by role for processing
    system_messages = []
    user_messages = []
    assistant_messages = []

    for msg in processed_messages:
        role = msg["role"]
        content = msg["content"]
        if role == "system":
            system_messages.append(
                content if isinstance(content, str) else str(content)
            )
        elif role == "user":
            user_messages.append(content if isinstance(content, str) else str(content))
        elif role == "assistant":
            assistant_messages.append(
                content if isinstance(content, str) else str(content)
            )

    # If tavern mode enabled, merge multiple system messages
    final_messages = []

    if system_messages:
        if tavern_mode_enabled:
            # Merge all system messages into one
            merged_system_content = "\n\n".join(system_messages)
            system_message = {
                "role": "system",
                "content": merged_system_content,
            }
        else:
            # Just use the last system message
            system_message = {
                "role": "system",
                "content": system_messages[-1] if system_messages else "",
            }

        # Determine participantPosition for system message based on mode
        if mode == "direct_chat":
            system_message["participantPosition"] = "b"
        elif mode == "battle":
            # In battle mode, system gets the battle_target position
            system_message["participantPosition"] = battle_target
        else:
            # Default to 'a' if mode is unknown
            system_message["participantPosition"] = "a"

        final_messages.append(system_message)

    # Process remaining messages with proper participantPosition based on mode
    for msg in processed_messages:
        role = msg["role"]
        content = msg["content"]

        # Skip system messages since we already handled them above
        if role == "system":
            continue

        message_obj = {"role": role, "content": content}

        # Determine participantPosition based on mode
        if mode == "direct_chat":
            message_obj[
                "participantPosition"
            ] = "a"  # non-system in direct mode gets 'a'
        elif mode == "battle":
            # In battle mode, all messages get the battle_target position
            message_obj["participantPosition"] = battle_target
        else:
            # Default to 'a' if mode is unknown
            message_obj["participantPosition"] = "a"

        final_messages.append(message_obj)

    # Apply bypass mode if enabled and for text models
    is_image_request = False
    # Check if this is an image request based on models.json
    if model_name in model_name_to_id_map:
        try:
            with open("models.json", "r", encoding="utf-8") as f:
                models_data = json.load(f)
            model_info = models_data.get(model_name)
            if model_info and isinstance(model_info, dict):
                if model_info.get("type") == "image":
                    is_image_request = True
        except (FileNotFoundError, json.JSONDecodeError):
            pass

    # First-message guard: if the first message is an assistant message, insert a fake user message
    if final_messages and final_messages[0]["role"] == "assistant":
        # Insert a fake user message at the beginning
        final_messages.insert(
            0,
            {
                "role": "user",
                "content": "Hi",
                "participantPosition": final_messages[0].get(
                    "participantPosition", "a"
                ),
            },
        )

    # If bypass mode is enabled and this is a text model, append a trailing user message
    if bypass_enabled and not is_image_request:
        final_messages.append(
            {"role": "user", "content": " ", "participantPosition": "a"}
        )

    return {
        "message_templates": final_messages,
        "target_model_id": target_model_id,
        "session_id": session_id,
        "message_id": message_id,
        "is_image_request": is_image_request,
    }
