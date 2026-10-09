import json
import logging
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

from chat import answer

HOST = "127.0.0.1"
PORT = 8000
MAX_BODY_SIZE = 16_384

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class ChatHandler(BaseHTTPRequestHandler):
    def _send_json(self, status: int, payload: dict[str, str]) -> None:
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self) -> None:
        if self.path == "/api/health":
            self._send_json(200, {"status": "ok"})
            return
        self._send_json(404, {"error": "Endpoint bulunamadı."})

    def do_POST(self) -> None:
        if self.path != "/api/chat":
            self._send_json(404, {"error": "Endpoint bulunamadı."})
            return

        try:
            content_length = int(self.headers.get("Content-Length", "0"))
        except ValueError:
            self._send_json(400, {"error": "Geçersiz istek boyutu."})
            return

        if content_length <= 0 or content_length > MAX_BODY_SIZE:
            self._send_json(400, {"error": "İstek boş veya izin verilen boyutu aşıyor."})
            return

        try:
            payload = json.loads(self.rfile.read(content_length))
        except (json.JSONDecodeError, UnicodeDecodeError):
            self._send_json(400, {"error": "İstek gövdesi geçerli JSON olmalıdır."})
            return

        soru = payload.get("question") if isinstance(payload, dict) else None
        if not isinstance(soru, str) or not soru.strip():
            self._send_json(400, {"error": "Soru alanı boş olmayan bir metin olmalıdır."})
            return

        try:
            response = answer(soru.strip())
        except Exception:
            logger.exception("Chat yanıtı oluşturulamadı")
            self._send_json(500, {"error": "Yanıt oluşturulurken bir hata oluştu."})
            return

        self._send_json(200, {"answer": response})

    def log_message(self, format: str, *args: object) -> None:
        logger.info("%s - %s", self.address_string(), format % args)


if __name__ == "__main__":
    server = ThreadingHTTPServer((HOST, PORT), ChatHandler)
    logger.info("Chat API http://%s:%s adresinde çalışıyor", HOST, PORT)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        logger.info("Chat API kapatılıyor")
    finally:
        server.server_close()
