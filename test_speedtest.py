"""Тесты: поднимаем локальный HTTP-сервер и проверяем подсчёты."""

import contextlib
import http.server
import io
import threading
import unittest

import speedtest

PAYLOAD = b"x" * 250_000


class Handler(http.server.BaseHTTPRequestHandler):
    hits = 0

    def do_GET(self):
        if self.path == "/404":
            self.send_error(404)
            return
        Handler.hits += 1
        self.send_response(200)
        self.send_header("Content-Length", str(len(PAYLOAD)))
        self.end_headers()
        self.wfile.write(PAYLOAD)

    def log_message(self, *args):
        pass


class SpeedtestTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.server = http.server.ThreadingHTTPServer(("127.0.0.1", 0), Handler)
        cls.url = f"http://127.0.0.1:{cls.server.server_address[1]}"
        threading.Thread(target=cls.server.serve_forever, daemon=True).start()

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()

    def test_ten_requests_full_body(self):
        Handler.hits = 0
        with contextlib.redirect_stdout(io.StringIO()):
            results = speedtest.run(self.url + "/file", 10, 5)
        self.assertEqual(Handler.hits, 10)
        self.assertEqual([size for size, _ in results], [len(PAYLOAD)] * 10)

    def test_summarize(self):
        s = speedtest.summarize([(1_000_000, 1.0), (1_000_000, 3.0)])
        self.assertEqual(s["total_bytes"], 2_000_000)
        self.assertAlmostEqual(s["avg_time"], 2.0)
        self.assertAlmostEqual(s["speed_mbit"], 4.0)    # 16 Мбит / 4 с
        self.assertAlmostEqual(s["speed_mbyte"], 0.5)   # 2 MB / 4 с

    def test_main_ok_and_http_error(self):
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            self.assertEqual(speedtest.main([self.url + "/file", "-n", "3"]), 0)
        self.assertIn("Мбит/с", out.getvalue())
        with contextlib.redirect_stdout(io.StringIO()), \
                contextlib.redirect_stderr(io.StringIO()):
            self.assertEqual(speedtest.main([self.url + "/404"]), 1)


if __name__ == "__main__":
    unittest.main()
