// ==UserScript==
// @name         XSArena Bridge v2 (WebSocket-based)
// @namespace    http://tampermonkey.net/
// @version      0.7
// @description  WebSocket-based bridge for XSArena, supporting all XSArena features.
// @match        https://lmarena.ai/*
// @match        https://*.lmarena.ai/*
// @grant        GM_xmlhttpRequest
// @connect      127.0.0.1
// @connect      localhost
// @connect      ws://127.0.0.1
// @connect      ws://localhost
// @scripts/agent_connect.sh 127.0.0.1
// @scripts/agent_connect.sh localhost
// @run-at       document-end
// ==/UserScript==

(function () {
  'use strict';

  // Bridge configuration with localStorage persistence
  const urlParams = new URLSearchParams(window.location.hash.substring(1));
  const storedPort = localStorage.getItem('xsa.bridge.port');
  const storedHost = localStorage.getItem('xsa.bridge.host') || '127.0.0.1';
  const internalToken = localStorage.getItem('xsa.internalToken') || 'dev-token-change-me';

  // Get bridge port from URL hash parameter, localStorage, or default to 5102
  const bridgePort = urlParams.get('bridge') || storedPort || '5102';
  // Persist the port to localStorage if it was specified in URL
  if (urlParams.get('bridge')) {
    localStorage.setItem('xsa.bridge.port', bridgePort);
  }

  const bridgeHost = storedHost; // Use stored host, with default fallback
  const WS_URL = `ws://${bridgeHost}:${bridgePort}/ws`;

  let ws = null;
  let isCaptureModeActive = false;
  let isApiBridgeRequest = false; // Flag to avoid recursive capture
  let reconnectAttempts = 0;
  const maxReconnectDelay = 10000; // 10 seconds max
  let lastActivity = Date.now();
  let heartbeatInterval = null;

  // Function to connect WebSocket with backoff and heartbeats
  function connectWebSocket() {
    try {
      ws = new WebSocket(WS_URL);

      ws.onopen = function(event) {
        logDebug("[XSArenaBridge] Connected to bridge server at", WS_URL);
        if (document.title.startsWith("❌ ")) {
          document.title = document.title.substring(3);
        }
        if (!document.title.startsWith("✅ ")) {
          document.title = "✅ " + document.title;
        }
        // Reset reconnect attempts on successful connection
        reconnectAttempts = 0;

        // Start heartbeat interval
        if (heartbeatInterval) {
          clearInterval(heartbeatInterval);
        }
        heartbeatInterval = setInterval(sendHeartbeat, 30000); // Every 30 seconds
      };

      ws.onmessage = function(event) {
        try {
          lastActivity = Date.now(); // Update last activity timestamp
          const message = JSON.parse(event.data);
          const command = message.command;

          if (command) {
            // Handle commands from bridge server
            if (command === "refresh") {
              logDebug("[XSArenaBridge] Refresh command received, reloading page...");
              location.reload();
            } else if (command === "reconnect") {
              logDebug("[XSArenaBridge] Reconnect command received, reloading page...");
              location.reload();
            } else if (command === "activate_id_capture") {
              logDebug("[XSArenaBridge] ID capture activation command received");
              isCaptureModeActive = true;
              if (!document.title.startsWith("🎯 ")) {
                document.title = "🎯 " + document.title;
              }
            } else if (command === "send_page_source") {
              logDebug("[XSArenaBridge] Sending page source to bridge...");
              // Send the full HTML of the page to the bridge
              const htmlContent = document.documentElement.outerHTML;
              // Size cap: if html.length > ~1.8MB, send a truncated version
              let contentToSend = htmlContent;
              if (htmlContent.length > 1800000) { // ~1.8MB
                contentToSend = `<!-- XSA-TRUNCATED -->${htmlContent.substring(0, 1800000)}`;
              }
              fetch(`http://${bridgeHost}:${bridgePort}/internal/update_available_models`, {
                method: 'POST',
                headers: {
                  'Content-Type': 'text/html',
                  'x-internal-token': internalToken
                },
                body: contentToSend,
              })
              .then(response => response.json())
              .then(data => {
                logDebug("[XSArenaBridge] Model update response:", data);
              })
              .catch(error => {
                logError("[XSArenaBridge] Error sending page source:", error);
              });
            } else if (command === "cloudflare_refresh") {
              logDebug("[XSArenaBridge] Cloudflare refresh command received, reloading page...");
              location.reload();
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
          logError("[XSArenaBridge] Error processing message:", e, event.data);
        }
      };

      ws.onclose = function(event) {
        logDebug("[XSArenaBridge] Disconnected from bridge server", event);
        if (!document.title.startsWith("❌ ")) {
          document.title = "❌ " + document.title;
        }
        // Clear heartbeat interval
        if (heartbeatInterval) {
          clearInterval(heartbeatInterval);
          heartbeatInterval = null;
        }

        // Implement exponential backoff with capped delay
        const delay = Math.min(Math.pow(2, reconnectAttempts) * 1000, maxReconnectDelay);
        reconnectAttempts++;
        logDebug(`[XSArenaBridge] Reconnecting in ${delay}ms (attempt ${reconnectAttempts})...`);
        setTimeout(connectWebSocket, delay);
      };

      ws.onerror = function(error) {
        logError("[XSArenaBridge] WebSocket error:", error);
      };
    } catch (e) {
      logError("[XSArenaBridge] Failed to create WebSocket:", e);
      // Implement exponential backoff with capped delay
      const delay = Math.min(Math.pow(2, reconnectAttempts) * 1000, maxReconnectDelay);
      reconnectAttempts++;
      logDebug(`[XSArenaBridge] Reconnecting in ${delay}ms (attempt ${reconnectAttempts})...`);
      setTimeout(connectWebSocket, delay);
    }
  }

  // Function to send heartbeat ping
  function sendHeartbeat() {
    if (ws && ws.readyState === WebSocket.OPEN) {
      // Update last activity timestamp for heartbeats too
      lastActivity = Date.now();
      ws.send(JSON.stringify({ type: 'ping', timestamp: Date.now() }));
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
          if (typeof url === 'string' && !args[1]?.headers?.['X-Api-Bridge-Request']) {
            // Generic ID capture using multiple regex patterns to catch various API endpoints
            const patterns = [
              // Original nextjs-api pattern
              /\/nextjs-api\/stream\/(?:retry-)?evaluation-session-message\/([a-f0-9-]+)\/messages\/([a-f0-9-]+)/i,
              // Generic UUID patterns in API endpoints
              /\/(?:api|v\d|nextjs-api)\/.*?\/([a-f0-9]{8}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{12}).*?\/([a-f0-9]{8}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{12})/i,
              // Pattern for session/message IDs in various formats
              /(?:session|conversation)\/([a-f0-9-]+).*?message(?:s)?\/([a-f0-9-]+)/i,
              /(?:session|conversation)Id=([a-f0-9-]+).*?message(?:s)?Id=([a-f0-9-]+)/i,
              // Direct UUID capture in URL path
              /\/([a-f0-9]{8}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{12})\/(?:messages|message)\/([a-f0-9]{8}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{12})/i,
              // More generic pattern for consecutive UUIDs in path
              /\/([a-f0-9-]{36})\/(?:messages|message|chat|conversation)\/([a-f0-9-]{36})/i
            ];

            for (const pattern of patterns) {
              const match = url.match(pattern);
              if (match && match[1] && match[2]) {
                const capturedSessionId = match[1];
                const capturedMessageId = match[2];

                // Validate that captured IDs look like UUIDs
                const uuidRegex = /^[a-f0-9]{8}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{12}$/i;
                const isSessionIdValid = uuidRegex.test(capturedSessionId) || /^[a-f0-9-]+$/.test(capturedSessionId);
                const isMessageIdValid = uuidRegex.test(capturedMessageId) || /^[a-f0-9-]+$/.test(capturedMessageId);

                if (isSessionIdValid && isMessageIdValid) {
                  logDebug("[XSArenaBridge] Captured IDs:", capturedSessionId, capturedMessageId);

                  // Send captured IDs to the ID updater service
                  fetch(`http://${bridgeHost}:${bridgePort}/internal/id_capture/update`, {
                    method: 'POST',
                    headers: {
                      'Content-Type': 'application/json',
                      'x-internal-token': internalToken
                    },
                    body: JSON.stringify({
                      session_id: capturedSessionId,
                      message_id: capturedMessageId
                    }),
                  })
                  .then(response => {
                    if (response.status === 200) {
                      logDebug("[XSArenaBridge] ID capture update successful:", { session_id: capturedSessionId, message_id: capturedMessageId });
                    } else if (response.status === 401) {
                      logError("[XSArenaBridge] ID capture update failed: Unauthorized - check internal token");
                    } else if (response.status === 503) {
                      logError("[XSArenaBridge] ID capture update failed: Service unavailable");
                    } else {
                      logError("[XSArenaBridge] ID capture update failed with status:", response.status);
                    }
                    return response.json();
                  })
                  .then(data => {
                    logDebug("[XSArenaBridge] ID update response:", data);
                  })
                  .catch(error => {
                    logError("[XSArenaBridge] Error updating IDs:", error);
                  });

                  // Reset capture mode after successful capture
                  isCaptureModeActive = false;
                  if (document.title.startsWith("🎯 ")) {
                    document.title = document.title.substring(2);
                  }
                  break; // Exit the loop after first successful capture
                }
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

        // Check for Cloudflare or busy state responses
        if (resp.status === 503 || resp.status === 429 || txt.toLowerCase().includes('cloudflare') || txt.toLowerCase().includes('captcha') || txt.toLowerCase().includes('access denied')) {
          logDebug("[XSArenaBridge] Detected Cloudflare/busy state, triggering refresh command");
          // Send cloudflare refresh command to WebSocket
          if (ws && ws.readyState === WebSocket.OPEN) {
            ws.send(JSON.stringify({ command: "cloudflare_refresh" }));
          } else {
            location.reload(); // Fallback to direct refresh
          }
          sendResponse(requestId, { error: `Service temporarily unavailable (status ${resp.status}). Page refresh initiated.` });
          return;
        }

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

  // Rate-limited logging functions
  let lastLogTime = {};
  const LOG_RATE_LIMIT = 3000; // 3 seconds

  function logDebug(...args) {
    if (localStorage.getItem('xsa.debug') === '1') {
      const now = Date.now();
      const key = args[0]; // Use first argument as key for rate limiting
      if (!lastLogTime[key] || now - lastLogTime[key] >= LOG_RATE_LIMIT) {
        console.log(...args);
        lastLogTime[key] = now;
      }
    }
  }

  function logError(...args) {
    if (localStorage.getItem('xsa.debug') === '1') {
      const now = Date.now();
      const key = args[0]; // Use first argument as key for rate limiting
      if (!lastLogTime[key] || now - lastLogTime[key] >= LOG_RATE_LIMIT) {
        console.error(...args);
        lastLogTime[key] = now;
      }
    } else {
      // Always log errors, but rate-limited
      const now = Date.now();
      const key = args[0];
      if (!lastLogTime[key] || now - lastLogTime[key] >= LOG_RATE_LIMIT) {
        console.error(...args);
        lastLogTime[key] = now;
      }
    }
  }

  // Function to send response back to bridge server
  function sendResponse(requestId, data) {
    if (ws && ws.readyState === WebSocket.OPEN) {
      ws.send(JSON.stringify({ request_id: requestId, data: data }));
    } else {
      logDebug("[XSArenaBridge] WebSocket not ready, cannot send response:", data);
    }
  }

  // Start the WebSocket connection
  logDebug("[XSArenaBridge] Starting WebSocket bridge for port", bridgePort, "...");
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

  // Add debug toggle function to global scope
  window.xsaDebug = function(enable) {
    if (enable) {
      localStorage.setItem('xsa.debug', '1');
      console.log('[XSArenaBridge] Debug logging enabled');
    } else {
      localStorage.setItem('xsa.debug', '0');
      console.log('[XSArenaBridge] Debug logging disabled');
    }
  };

})();
