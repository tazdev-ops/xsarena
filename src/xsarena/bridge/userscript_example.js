// ==UserScript==
// @name         LMArena API Bridge
// @namespace    http://tampermonkey.net/
// @version      2.5
// @description  Bridges LMArena to a local API server via WebSocket.
// @author       Lianues
// @match        https://lmarena.ai/*
// @grant        none
// @run-at       document-end
// ==/UserScript==

(function () {
    'use strict';
    const SERVER_URL = "ws://localhost:5102/ws";
    let socket;
    let isCaptureModeActive = false;

    function connect() {
        console.log(`[API Bridge] Connecting to local server: ${SERVER_URL}...`);
        socket = new WebSocket(SERVER_URL);

        socket.onopen = () => console.log("[API Bridge] ✅ WebSocket connection established.");
        socket.onmessage = async (event) => {
            const message = JSON.parse(event.data);
            if (message.command) {
                if (message.command === 'activate_id_capture') {
                    isCaptureModeActive = true;
                    console.log("[API Bridge] ✅ ID capture mode activated. Trigger a 'Retry' on the desired message.");
                }
                return;
            }
            const { request_id, payload } = message;
            if (request_id && payload) {
                await executeFetchAndStreamBack(request_id, payload);
            }
        };
        socket.onclose = () => {
            console.warn("[API Bridge] 🔌 Connection lost. Retrying in 5 seconds...");
            setTimeout(connect, 5000);
        };
        socket.onerror = (error) => console.error("[API Bridge] ❌ WebSocket error:", error);
    }

    async function executeFetchAndStreamBack(requestId, payload) {
        const { message_templates, target_model_id, session_id, message_id } = payload;
        const apiUrl = `/nextjs-api/stream/retry-evaluation-session-message/${session_id}/messages/${message_id}`;
        let lastMsgIdInChain = null;
        const newMessages = message_templates.map((template, i) => {
            const currentMsgId = crypto.randomUUID();
            const parentIds = lastMsgIdInChain ? [lastMsgIdInChain] : [];
            const status = (i === message_templates.length - 1) ? 'pending' : 'success';
            lastMsgIdInChain = currentMsgId;
            return { ...template, id: currentMsgId, parentMessageIds: parentIds, evaluationSessionId: session_id, status };
        });

        try {
            window.isApiBridgeRequest = true; // Flag to prevent self-interception
            const response = await fetch(apiUrl, {
                method: 'PUT',
                headers: { 'Content-Type': 'text/plain;charset=UTF-8' },
                body: JSON.stringify({ messages: newMessages, modelId: target_model_id }),
                credentials: 'include'
            });
            if (!response.ok || !response.body) throw new Error(`Network response was not ok: ${response.status}`);
            
            const reader = response.body.getReader();
            const decoder = new TextDecoder();
            while (true) {
                const { value, done } = await reader.read();
                if (done) break;
                sendToServer(requestId, decoder.decode(value));
            }
            sendToServer(requestId, "[DONE]");
        } catch (error) {
            sendToServer(requestId, { error: error.message });
        } finally {
            window.isApiBridgeRequest = false;
        }
    }

    function sendToServer(requestId, data) {
        if (socket && socket.readyState === WebSocket.OPEN) {
            socket.send(JSON.stringify({ request_id: requestId, data: data }));
        }
    }

    const originalFetch = window.fetch;
    window.fetch = function(...args) {
        const url = args[0] instanceof Request ? args[0].url : String(args[0]);
        if (isCaptureModeActive && !window.isApiBridgeRequest) {
            const match = url.match(/\/nextjs-api\/stream\/retry-evaluation-session-message\/([a-f0-9-]+)\/messages\/([a-f0-9-]+)/);
            if (match) {
                isCaptureModeActive = false;
                const [_, sessionId, messageId] = match;
                console.log(`[API Bridge] 🎯 Captured IDs! Sending to updater...`);
                fetch('http://127.0.0.1:5103/update', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ sessionId, messageId })
                }).catch(err => console.error('[API Bridge] Failed to send IDs to updater:', err));
            }
        }
        return originalFetch.apply(this, args);
    };
    connect();
})();