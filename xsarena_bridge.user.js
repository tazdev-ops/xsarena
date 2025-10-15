// ==UserScript==
// @name         XSArena Bridge (CSP-safe polling, no fetch override)
// @namespace    http://tampermonkey.net/
// @version      0.4
// @description  Poll local CLI via GM_xmlhttpRequest, capture IDs via PerformanceObserver, stream chunks back.
// @match        https://lmarena.ai/*
// @match        https://*.lmarena.ai/*
// @grant        GM_xmlhttpRequest
// @connect      127.0.0.1
// @connect      localhost
// @run-at       document-end
// ==/UserScript==

(function () {
  'use strict';

  const BASE = "http://127.0.0.1:5102";
  let isCaptureMode = false;
  let polling = false;

  // ---- Helpers (GM requests bypass page CSP) ----
  function gmGet(path, onOk, onErr) {
    GM_xmlhttpRequest({
      method: "GET",
      url: BASE + path,
      timeout: 5000,
      onload: r => { try { onOk && onOk(JSON.parse(r.responseText || "{}")); } catch (e) { onErr && onErr(e); } },
      onerror: e => onErr && onErr(e),
      ontimeout: e => onErr && onErr(e),
    });
  }
  function gmPost(path, body, onOk, onErr) {
    GM_xmlhttpRequest({
      method: "POST",
      url: BASE + path,
      data: JSON.stringify(body || {}),
      headers: {"Content-Type": "application/json"},
      timeout: 20000,
      onload: r => onOk && onOk(r),
      onerror: e => onErr && onErr(e),
      ontimeout: e => onErr && onErr(e),
    });
  }

  // ---- Poll loop: fetch capture flag + any pending job from CLI ----
  function startPoll() {
    if (polling) return;
    polling = true;

    const loop = () => {
      gmGet("/bridge/poll", async (resp) => {
        try {
          if (resp.capture) {
            isCaptureMode = true;
            if (!document.title.startsWith("🎯 ")) document.title = "🎯 " + document.title;
            console.log("[MinimalBridge] Capture ON. Click Retry in LMArena.");
          }

          if (resp.job && resp.job.request_id && resp.job.payload) {
            await executeJob(resp.job.request_id, resp.job.payload);
            setTimeout(loop, 150);
            return;
          }
          setTimeout(loop, 500);
        } catch (e) {
          console.warn("[MinimalBridge] poll error:", e);
          setTimeout(loop, 1000);
        }
      }, () => setTimeout(loop, 1000));
    };

    loop();
  }

  // ---- ID capture without overriding fetch: use PerformanceObserver on resource entries ----
  function startResourceObserver() {
    try {
      const re = /\/nextjs-api\/stream\/(?:retry-)?evaluation-session-message\/([a-f0-9-]+)\/messages\/([a-f0-9-]+)/i;

      // Observe future entries
      const obs = new PerformanceObserver((list) => {
        for (const entry of list.getEntries()) {
          if (!isCaptureMode) continue;
          const url = entry.name || "";
          const m = url.match(re);
          if (m) {
            isCaptureMode = false;
            if (document.title.startsWith("🎯 ")) document.title = document.title.substring(2);
            const sessionId = m[1], messageId = m[2];
            console.log("[MinimalBridge] Captured IDs:", sessionId, messageId);
            gmPost("/internal/id_capture/update", { sessionId, messageId });
          }
        }
      });
      obs.observe({ entryTypes: ["resource"] });

      // Optional: check past entries (usually not needed for "Retry")
      // for (const e of performance.getEntriesByType("resource")) {
      //   if (!isCaptureMode) break;
      //   const m = (e.name || "").match(re);
      //   if (m) { ... }
      // }
    } catch (e) {
      console.warn("[MinimalBridge] PerformanceObserver not available:", e);
    }
  }

  // ---- Execute a chat job from CLI ----
  async function executeJob(requestId, payload) {
    try {
      const { message_templates, target_model_id, session_id, message_id, is_image_request } = payload || {};
      if (!Array.isArray(message_templates) || !session_id || !message_id) {
        gmPost("/bridge/push", { request_id: requestId, data: { error: "Invalid payload from CLI." } });
        gmPost("/bridge/push", { request_id: requestId, data: "[DONE]" });
        return;
      }

      const apiUrl = `/nextjs-api/stream/retry-evaluation-session-message/${session_id}/messages/${message_id}`;
      const newMessages = [];
      let lastId = null;

      for (let i = 0; i < message_templates.length; i++) {
        const t = message_templates[i];
        const id = crypto.randomUUID();
        const parents = lastId ? [lastId] : [];
        const status = is_image_request ? "success" : (i === message_templates.length - 1 ? "pending" : "success");
        newMessages.push({
          role: t.role,
          content: t.content,
          id,
          evaluationId: null,
          evaluationSessionId: session_id,
          parentMessageIds: parents,
          experimental_attachments: Array.isArray(t.attachments) ? t.attachments : [],
          failureReason: null,
          metadata: null,
          participantPosition: t.participantPosition || "a",
          createdAt: new Date().toISOString(),
          updatedAt: new Date().toISOString(),
          status
        });
        lastId = id;
      }

      const body = { messages: newMessages, modelId: target_model_id || null };
      const resp = await fetch(apiUrl, {
        method: "PUT",
        headers: { "Content-Type": "text/plain;charset=UTF-8", "Accept": "*/*" },
        credentials: "include",
        body: JSON.stringify(body)
      });
      if (!resp.ok || !resp.body) {
        const txt = await resp.text().catch(() => "");
        gmPost("/bridge/push", { request_id: requestId, data: { error: `Bad response ${resp.status}: ${txt}` } });
        return;
      }

      const reader = resp.body.getReader();
      const dec = new TextDecoder();
      while (true) {
        const { value, done } = await reader.read();
        if (done) break;
        gmPost("/bridge/push", { request_id: requestId, data: dec.decode(value) });
      }
      gmPost("/bridge/push", { request_id: requestId, data: "[DONE]" });
    } catch (e) {
      console.error("[MinimalBridge] job error:", e);
      gmPost("/bridge/push", { request_id: requestId, data: { error: e.message || String(e) } });
    }
  }

  console.log("[MinimalBridge] CSP-safe polling bridge starting…");
  startPoll();
  startResourceObserver();
})();