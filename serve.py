
#!/usr/bin/env python3
"""
One-step local preview.

Runs the tracker to build totals.json, then serves this folder over http:// so
tracker_page.html can fetch the JSON. (Opening the HTML directly as a file://
URL won't work — browsers block file pages from reading local files.)

    export FEC_API_KEY=your_key      # the key stays here, not in any file
    python serve.py

Then your browser opens to the live page. Ctrl+C to stop.
"""
import functools
import http.server
import os
import socketserver
import subprocess
import sys
import webbrowser

PORT = int(os.environ.get("PORT", "8000"))
PAGE = "tracker_page.html"


def build():
    if os.environ.get("FEC_API_KEY", "DEMO_KEY") == "DEMO_KEY":
        print("⚠  FEC_API_KEY not set — using the rate-limited DEMO_KEY.")
        print("   Set yours first:  export FEC_API_KEY=your_key\n")
    print("→ Running fec_tracker.py to build totals.json …")
    result = subprocess.run([sys.executable, "fec_tracker.py"])
    if result.returncode != 0:
        print("⚠  Tracker reported an error above; serving the page anyway "
              "(it will fall back to preview data if totals.json is missing).")
    print()


def serve():
    handler = functools.partial(http.server.SimpleHTTPRequestHandler, directory=".")
    with socketserver.TCPServer(("", PORT), handler) as httpd:
        url = f"http://localhost:{PORT}/{PAGE}"
        print(f"✓ Serving at {url}")
        print("  (Ctrl+C to stop)")
        try:
            webbrowser.open(url)
        except Exception:
            pass
        try:
            httpd.serve_forever()
        except KeyboardInterrupt:
            print("\nStopped.")


if __name__ == "__main__":
    build()
    serve()
