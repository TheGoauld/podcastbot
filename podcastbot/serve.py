#!/usr/bin/env python3
"""
HTTP server for podcast RSS feed and episodes.
"""

import sys
from http.server import HTTPServer, SimpleHTTPRequestHandler
from functools import partial

from podcastbot.config import PODCAST_DIR

PORT = 8085


class PodcastHandler(SimpleHTTPRequestHandler):
    def end_headers(self):
        self.send_header("Access-Control-Allow-Origin", "*")
        if self.path.endswith(".xml"):
            self.send_header("Content-Type", "application/rss+xml; charset=utf-8")
        super().end_headers()

    def log_message(self, format, *args):
        pass


def main():
    PODCAST_DIR.mkdir(parents=True, exist_ok=True)
    handler = partial(PodcastHandler, directory=str(PODCAST_DIR))
    server = HTTPServer(("0.0.0.0", PORT), handler)
    print(f"Podcast server on port {PORT}, serving {PODCAST_DIR}", file=sys.stderr)
    server.serve_forever()


if __name__ == "__main__":
    main()
