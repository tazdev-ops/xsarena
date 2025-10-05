// ==UserScript==
// @name         LMASudio Bridge Userscript
// @namespace    http://tampermonkey.net/
// @version      0.1
// @description  Bridge to connect LMArena with local LMASudio server
// @author       You
// @match        https://lmarena.ai/*
// @grant        GM_xmlhttpRequest
// ==/UserScript==

(function() {
    'use strict';

    function resolveBase() {
        try {
            const u = new URL(location.href);
            // Accept ?bridge=5103 or #bridge=5103
            const fromQuery = u.searchParams.get("bridge");
            const fromHash = (location.hash.match(/(?:^|[#&])bridge=(\d+)/) || [])[1];
            const fromStorage = localStorage.getItem("lma_bridge_port");
            const port = (fromQuery || fromHash || fromStorage || "8080").trim();
            // Persist for this tab domain
            localStorage.setItem("lma_bridge_port", port);
            return "http://127.0.0.1:" + port;
        } catch (e) {
            return "http://127.0.0.1:8080";
        }
    }
    const BASE = resolveBase();
    console.log("[LMASudioBridge] Using bridge:", BASE);

    // Quick setter in devtools: lmaSetBridgePort(5103)
    window.lmaSetBridgePort = function(p){ localStorage.setItem("lma_bridge_port", String(p)); location.reload(); };

    // GM wrapper functions for CSP-safe requests
    function gmGet(path) {
        return new Promise((resolve, reject) => {
            GM_xmlhttpRequest({
                method: "GET",
                url: BASE + path,
                onload: function(response) {
                    try {
                        resolve(JSON.parse(response.responseText));
                    } catch (e) {
                        resolve(response.responseText);
                    }
                },
                onerror: function(err) {
                    reject(err);
                }
            });
        });
    }

    function gmPost(path, data) {
        return new Promise((resolve, reject) => {
            GM_xmlhttpRequest({
                method: "POST",
                url: BASE + path,
                headers: {
                    "Content-Type": "application/json"
                },
                data: JSON.stringify(data),
                onload: function(response) {
                    try {
                        resolve(JSON.parse(response.responseText));
                    } catch (e) {
                        resolve(response.responseText);
                    }
                },
                onerror: function(err) {
                    reject(err);
                }
            });
        });
    }

    // Example usage of the bridge
    // This would connect to the actual LMASudio engine
    console.log("LMASudio Bridge initialized, connecting to:", BASE);
})();