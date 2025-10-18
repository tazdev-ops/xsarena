// ==UserScript==
// @name         XSArena Bridge v2 (WebSocket-based)
// @namespace    http://tampermonkey.net/
// @version      0.5
// @description  WebSocket-based bridge for XSArena, supporting all XSArena features.
// @match        https://lmarena.ai/*
// @match        https://*.lmarena.ai/*
// @grant        GM_xmlhttpRequest
// @connect      127.0.0.1
// @connect      localhost
// @run-at       document-end
// ==/UserScript==

(function () {
  'use strict';

  // Get bridge port from URL hash parameter, default to 5102
  const urlParams = new URLSearchParams(window.location.hash.substring(1));
  const bridgePort = urlParams.get('bridge') || '5102';
  const WS_URL = `ws://127.0.0.1:${bridgePort}/ws`;

  let ws = null;
  let isCaptureModeActive = false;
  let isApiBridgeRequest = false; // Flag to avoid recursive capture

  // Function to connect WebSocket
  function connectWebSocket() {
    try {
      ws = new WebSocket(WS_URL);

      ws.onopen = function(event) {
        console.log("[XSArenaBridge] Connected to bridge server at", WS_URL);
        if (document.title.startsWith("❌ ")) {
          document.title = document.title.substring(3);
        }
        if (!document.title.startsWith("✅ ")) {
          document.title = "✅ " + document.title;
        }
      };

      ws.onmessage = function(event) {
        try {
          const message = JSON.parse(event.data);
          const command = message.command;

          if (command) {
            // Handle commands from bridge server
            if (command === "refresh") {
              console.log("[XSArenaBridge] Refresh command received, reloading page...");
              location.reload();
            } else if (command === "reconnect") {
              console.log("[XSArenaBridge] Reconnect command received, reloading page...");
              location.reload();
            } else if (command === "activate_id_capture") {
              console.log("[XSArenaBridge] ID capture activation command received");
              isCaptureModeActive = true;
              if (!document.title.startsWith("🎯 ")) {
                document.title = "🎯 " + document.title;
              }
            } else if (command === "send_page_source") {
              console.log("[XSArenaBridge] Sending page source to bridge...");
              // Send the full HTML of the page to the bridge
              const htmlContent = document.documentElement.outerHTML;
              fetch(`http://127.0.0.1:${bridgePort}/internal/update_available_models`, {
                method: 'POST',
                headers: {
                  'Content-Type': 'text/html',
                },
                body: htmlContent,
              })
              .then(response => response.json())
              .then(data => {
                console.log("[XSArenaBridge] Model update response:", data);
              })
              .catch(error => {
                console.error("[XSArenaBridge] Error sending page source:", error);
              });
            }
          } else {
            // Handle payload requests from bridge server
            const requestId = message.request_id;
            const payload = message.payload;

            if (requestId && payload) {
              executeLMArenaRequest(requestId, payload);
            }
          }
        } catch (e) {
          console.error("[XSArenaBridge] Error processing message:", e, event.data);
        }
      };

      ws.onclose = function(event) {
        console.log("[XSArenaBridge] Disconnected from bridge server", event);
        if (!document.title.startsWith("❌ ")) {
          document.title = "❌ " + document.title;
        }
        // Try to reconnect after a delay
        setTimeout(connectWebSocket, 5000);
      };

      ws.onerror = function(error) {
        console.error("[XSArenaBridge] WebSocket error:", error);
      };
    } catch (e) {
      console.error("[XSArenaBridge] Failed to create WebSocket:", e);
      setTimeout(connectWebSocket, 5000);
    }
  }

  // Function to execute LMArena request
  async function executeLMArenaRequest(requestId, payload) {
    try {
      const { message_templates, target_model_id, session_id, message_id, is_image_request } = payload || {};
      if (!Array.isArray(message_templates) || !session_id || !message_id) {
        sendResponse(requestId, { error: "Invalid payload from bridge server." });
        sendResponse(requestId, "[DONE]");
        return;
      }

      // Intercept fetch calls to capture session/message IDs when in capture mode
      if (isCaptureModeActive) {
        const originalFetch = window.fetch;
        window.fetch = function(...args) {
          const url = args[0];
          if (typeof url === 'string') {
            const idRegex = /\/nextjs-api\/stream\/(?:retry-)?evaluation-session-message\/([a-f0-9-]+)\/messages\/([a-f0-9-]+)/i;
            const match = url.match(idRegex);
            if (match && isCaptureModeActive) {
              const capturedSessionId = match[1];
              const capturedMessageId = match[2];
              console.log("[XSArenaBridge] Captured IDs:", capturedSessionId, capturedMessageId);

              // Send captured IDs to the ID updater service
              fetch(`http://127.0.0.1:5103/update`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                  sessionId: capturedSessionId,
                  messageId: capturedMessageId
                }),
              })
              .then(response => response.json())
              .then(data => {
                console.log("[XSArenaBridge] ID update response:", data);
              })
              .catch(error => {
                console.error("[XSArenaBridge] Error updating IDs:", error);
              });

              // Reset capture mode
              isCaptureModeActive = false;
              if (document.title.startsWith("🎯 ")) {
                document.title = document.title.substring(2);
              }
            }
          }

          // Call original fetch
          return originalFetch.apply(this, args);
        };
      }

      const apiUrl = `/nextjs-api/stream/retry-evaluation-session-message/${session_id}/messages/${message_id}`;

      // Construct message chain for LMArena
      const newMessages = [];
      let lastId = null;

      for (let i = 0; i < message_templates.length; i++) {
        const template = message_templates[i];
        const id = crypto.randomUUID();
        const parents = lastId ? [lastId] : [];

        // Determine status based on position
        const isLastMessage = (i === message_templates.length - 1);
        const status = isLastMessage ? "pending" : "success";

        // Get participant position from template or default
        let participantPosition = template.participantPosition || "a";
        if (!participantPosition) {
          // Default logic for participant position
          if (template.role === "system") {
            participantPosition = "system"; // or appropriate default
          } else {
            participantPosition = "a"; // default for user/assistant
          }
        }

        const messageObj = {
          role: template.role,
          content: template.content,
          id,
          evaluationId: null,
          evaluationSessionId: session_id,
          parentMessageIds: parents,
          experimental_attachments: template.attachments || [], // Include attachments if present
          failureReason: null,
          metadata: null,
          participantPosition,
          createdAt: new Date().toISOString(),
          updatedAt: new Date().toISOString(),
          status
        };

        newMessages.push(messageObj);
        lastId = id;
      }

      const body = {
        messages: newMessages,
        modelId: target_model_id || null
      };

      // Mark this as an API bridge request to avoid recursive capture
      isApiBridgeRequest = true;

      const resp = await fetch(apiUrl, {
        method: "PUT",
        headers: {
          "Content-Type": "text/plain;charset=UTF-8",
          "Accept": "*/*",
          "X-Api-Bridge-Request": "true"  // Custom header to identify bridge requests
        },
        credentials: "include",
        body: JSON.stringify(body)
      });

      // Reset the flag after request
      isApiBridgeRequest = false;

      if (!resp.ok || !resp.body) {
        const txt = await resp.text().catch(() => "");
        sendResponse(requestId, { error: `Bad response ${resp.status}: ${txt}` });
        return;
      }

      // Stream response back to bridge server
      const reader = resp.body.getReader();
      const dec = new TextDecoder();
      while (true) {
        const { value, done } = await reader.read();
        if (done) break;
        const chunk = dec.decode(value);

        // Check if this is an image response for image models
        if (is_image_request && chunk.includes("http")) {
          // This might be an image URL, format as markdown image
          const imageUrlMatch = chunk.match(/(https?:\/\/[^\s'"]+\.(?:jpg|jpeg|png|gif|webp))/i);
          if (imageUrlMatch) {
            sendResponse(requestId, `![Image](${imageUrlMatch[1]})`);
          } else {
            sendResponse(requestId, chunk);
          }
        } else {
          sendResponse(requestId, chunk);
        }
      }
      sendResponse(requestId, "[DONE]");
    } catch (e) {
      console.error("[XSArenaBridge] job error:", e);
      isApiBridgeRequest = false; // Reset flag on error
      sendResponse(requestId, { error: e.message || String(e) });
    }
  }

  // Function to send response back to bridge server
  function sendResponse(requestId, data) {
    if (ws && ws.readyState === WebSocket.OPEN) {
      ws.send(JSON.stringify({ request_id: requestId, data: data }));
    } else {
      console.warn("[XSArenaBridge] WebSocket not ready, cannot send response:", data);
    }
  }

  // Start the WebSocket connection
  console.log("[XSArenaBridge] Starting WebSocket bridge for port", bridgePort, "...");
  connectWebSocket();

  // Add a visual indicator to the page
  const indicator = document.createElement('div');
  indicator.id = 'xsarena-bridge-indicator';
  indicator.style.cssText = `
    position: fixed;
    top: 10px;
    right: 10px;
    z-index: 10000;
    padding: 8px 12px;
    background: #4CAF50;
    color: white;
    border-radius: 4px;
    font-size: 12px;
    font-family: monospace;
    box-shadow: 0 2px 10px rgba(0,0,0,0.3);
  `;
  indicator.textContent = 'XSArena Bridge v2 Connected';
  document.body.appendChild(indicator);

  // Update indicator based on WebSocket state
  setInterval(() => {
    if (ws && ws.readyState === WebSocket.OPEN) {
      indicator.textContent = 'XSArena Bridge v2 Connected';
      indicator.style.background = '#4CAF50';
    } else {
      indicator.textContent = 'XSArena Bridge v2 Disconnected';
      indicator.style.background = '#f44336';
    }
  }, 1000);

})();
