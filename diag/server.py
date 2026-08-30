import http.server, sys, os, time
D=os.path.dirname(os.path.abspath(__file__))
class H(http.server.BaseHTTPRequestHandler):
    def do_POST(self):
        n=int(self.headers.get('Content-Length','0')); body=self.rfile.read(n)
        fn=os.path.join(D, f"dump-{int(time.time())}-{self.path.strip('/').replace('/','_')}.bin")
        open(fn,'wb').write(body); open(fn+'.hdr','w').write(str(self.headers))
        self.send_response(200); self.send_header('Content-Type','text/plain'); self.end_headers(); self.wfile.write(b'ok')
    def log_message(self,*a): pass
http.server.HTTPServer(('127.0.0.1',8771),H).serve_forever()
