from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
import json
import urllib.request

ROOT = Path(__file__).resolve().parents[1]
MODEL = "qwen3-vl:2b"
OLLAMA = "http://127.0.0.1:11434"
ORIGIN = "http://127.0.0.1:8100"
PROMPTS = {
    "search": "Extract 3 to 10 concise material, color or texture search keywords in Chinese and English.",
    "similar": "Describe the dominant surface texture, ignoring objects. Extract 3 to 10 concise material, color or texture keywords in Chinese and English.",
    "classify": "Suggest a Chinese material category, color and texture tags. State uncertainties in summary.",
    "brand": "Organize the provided evidence by wall, floor and counter in Chinese. Distinguish observed features from suggestions. Do not assert actual product codes or brand attribution.",
}


class Handler(SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=str(ROOT), **kwargs)

    def reply(self, status, payload):
        body = json.dumps(payload, ensure_ascii=False).encode()
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        if self.headers.get("Host") != "127.0.0.1:8100":
            return self.send_error(403)
        if self.path == "/api/ai":
            try:
                with urllib.request.urlopen(OLLAMA + "/api/tags", timeout=3) as response:
                    ready = any(row["name"] == MODEL for row in json.load(response)["models"])
            except (OSError, ValueError, KeyError):
                ready = False
            return self.reply(200, {"ready": ready, "model": MODEL})
        target = Path(self.translate_path(self.path)).resolve()
        if not target.is_relative_to(ROOT):
            return self.send_error(404)
        parts = ("", *target.relative_to(ROOT).parts)
        if len(parts) == 1:
            parts = ("", "")
            self.path = "/index.html"
        if target != ROOT and not target.is_file():
            return self.send_error(404)
        if any(part.startswith(".") for part in parts) or parts[1] not in (
            "", "images", "thumbs", "ai.html", "ai.js", "index.html", "library.js",
            "library.css", "auto-ui.js", "auto-ui.css", "resources.js",
            "data.js", "extra-data.js", "benif-data.js", "auto-data.js",
            "data.json", "extra-data.json", "benif-data.json", "auto-data.json",
            "discovery-data.js", "discovery-data.json", "sync-status.js", "sync-status.json",
        ):
            return self.send_error(404)
        return super().do_GET()

    def do_POST(self):
        if (self.path != "/api/ai" or self.headers.get("Host") != "127.0.0.1:8100"
                or self.headers.get("Origin") != ORIGIN):
            return self.reply(403, {"error": "请通过本机 AI 工作台使用模型。"})
        try:
            length = int(self.headers.get("Content-Length", "0"))
            if not 0 < length <= 3_000_000:
                raise ValueError()
            data = json.loads(self.rfile.read(length))
            prompt = PROMPTS[data["mode"]]
            message = {"role": "user", "content": str(data.get("text", ""))[:3000]}
            if data.get("image"):
                message["images"] = [data["image"]]
        except (ValueError, KeyError, TypeError, AttributeError):
            return self.reply(400, {"error": "请求内容无效或图片过大。"})
        payload = {
            "model": MODEL, "stream": False, "think": False, "format": "json",
            "options": {"num_predict": 450, "temperature": 0.2},
            "messages": [{"role": "system", "content": prompt
                          + ' Output JSON only: {"summary":"Chinese text","keywords":["term"]}.'}, message],
        }
        request = urllib.request.Request(OLLAMA + "/api/chat", json.dumps(payload).encode(),
                                         {"Content-Type": "application/json"})
        try:
            with urllib.request.urlopen(request, timeout=240) as response:
                result = json.loads(json.load(response)["message"]["content"])
            if not isinstance(result, dict):
                raise ValueError()
        except (OSError, ValueError, KeyError):
            return self.reply(502, {"error": "模型暂未返回可用结果，请确认 Ollama 和千问视觉模型正在运行。"})
        return self.reply(200, result)


if __name__ == "__main__":
    print(ORIGIN + "/ai.html", flush=True)
    ThreadingHTTPServer(("127.0.0.1", 8100), Handler).serve_forever()
