# tools/id_updater.py
import http.server
import socketserver
import json
import re
import threading
import os
import requests

HOST, PORT = "127.0.0.1", 5103
CONFIG_PATH = 'config.jsonc'

def update_config_value(key, value):
    try:
        with open(CONFIG_PATH, 'r', encoding='utf-8') as f:
            content = f.read()
        pattern = re.compile(rf'("{key}"\s*:\s*")[^"]*(")')
        new_content, count = pattern.subn(rf'\g<1>{value}\g<2>', content, 1)
        if count == 0: return False
        with open(CONFIG_PATH, 'w', encoding='utf-8') as f:
            f.write(new_content)
        return True
    except Exception as e:
        print(f"❌ Error updating '{CONFIG_PATH}': {e}")
        return False

class RequestHandler(http.server.SimpleHTTPRequestHandler):
    def do_POST(self):
        if self.path == '/update':
            try:
                content_length = int(self.headers['Content-Length'])
                data = json.loads(self.rfile.read(content_length))
                session_id, message_id = data.get('sessionId'), data.get('messageId')
                if session_id and message_id:
                    print("\n" + "="*50 + f"\n🎉 Captured IDs:\n  - Session ID: {session_id}\n  - Message ID: {message_id}\n" + "="*50)
                    if update_config_value("session_id", session_id) and update_config_value("message_id", message_id):
                        print("✅ Config updated. Server will shut down.")
                    self.send_response(200)
                    self.end_headers()
                    threading.Thread(target=self.server.shutdown).start()
            except Exception as e:
                self.send_response(500)
                self.end_headers()
                print(f"Error handling POST: {e}")
        else: self.send_response(404)
    def log_message(self, format, *args): return

def run_server():
    with socketserver.TCPServer((HOST, PORT), RequestHandler) as httpd:
        print(f"🚀 ID Updater listening at http://{HOST}:{PORT}")
        httpd.serve_forever()

def notify_api_server():
    try:
        requests.post("http://127.0.0.1:5102/internal/start_id_capture", timeout=3)
        print("✅ Notified main server to activate capture mode.")
        return True
    except requests.ConnectionError:
        print("❌ Cannot connect to main API server. Is it running?")
        return False

if __name__ == "__main__":
    if notify_api_server():
        run_server()
        print("Server shut down.")