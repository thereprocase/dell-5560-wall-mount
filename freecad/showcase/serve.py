from http.server import ThreadingHTTPServer,SimpleHTTPRequestHandler
from functools import partial
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]/'docs'
class Handler(SimpleHTTPRequestHandler):
 def end_headers(self):
  self.send_header('X-Content-Type-Options','nosniff')
  self.send_header('Referrer-Policy','same-origin')
  super().end_headers()
 def list_directory(self,path):
  self.send_error(404);return None
class Server(ThreadingHTTPServer):
 request_queue_size=128

Server(('127.0.0.1',8876),partial(Handler,directory=str(ROOT))).serve_forever()
