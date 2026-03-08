"""
Matrix client — sends messages, polls for commands, manages sync state.
"""

import json
import sys
import time

import requests

from podcastbot.config import SYNC_TOKEN_FILE


def log(msg: str):
    print(f"[podcastbot] {msg}", file=sys.stderr, flush=True)


class MatrixClient:
    def __init__(self, homeserver: str, access_token: str, user_id: str):
        self.homeserver = homeserver.rstrip("/")
        self.access_token = access_token
        self.user_id = user_id
        self._session = requests.Session()
        self._session.headers["Authorization"] = f"Bearer {access_token}"

    def send_message(self, room_id: str, text: str, retries: int = 3) -> bool:
        url = (f"{self.homeserver}/_matrix/client/r0/rooms/{room_id}"
               f"/send/m.room.message/{int(time.time() * 1000)}")
        payload = {"msgtype": "m.text", "body": text}
        for attempt in range(1, retries + 1):
            try:
                r = self._session.put(url, json=payload, timeout=10)
                if r.status_code in (200, 201):
                    return True
                log(f"send attempt {attempt}/{retries} failed {r.status_code}: {r.text}")
            except Exception as e:
                log(f"send attempt {attempt}/{retries} error: {e}")
            if attempt < retries:
                time.sleep(2)
        return False

    def get_sync_token(self) -> str:
        if SYNC_TOKEN_FILE.exists():
            token = SYNC_TOKEN_FILE.read_text().strip()
            if token:
                return token
        url = f"{self.homeserver}/_matrix/client/r0/sync"
        params = {
            "filter": json.dumps({"room": {"timeline": {"limit": 0}}}),
            "timeout": "0",
        }
        try:
            r = self._session.get(url, params=params, timeout=30)
            if r.status_code == 200:
                token = r.json().get("next_batch", "")
                if token:
                    self.save_sync_token(token)
                    return token
        except Exception as e:
            log(f"initial sync error: {e}")
        return ""

    def save_sync_token(self, token: str):
        if token:
            SYNC_TOKEN_FILE.parent.mkdir(parents=True, exist_ok=True)
            SYNC_TOKEN_FILE.write_text(token)

    def poll_messages(self, room_id: str, since: str,
                      poll_interval: int = 3) -> tuple[list[dict], str]:
        url = f"{self.homeserver}/_matrix/client/r0/sync"
        room_filter = json.dumps({
            "room": {
                "rooms": [room_id],
                "timeline": {"limit": 10},
            }
        })
        params = {
            "since": since,
            "timeout": str(poll_interval * 1000),
            "filter": room_filter,
        }
        try:
            r = self._session.get(url, params=params, timeout=poll_interval + 10)
            if r.status_code == 200:
                data = r.json()
                new_token = data.get("next_batch", since)
                messages = []
                rooms = data.get("rooms", {}).get("join", {})
                if room_id in rooms:
                    events = rooms[room_id].get("timeline", {}).get("events", [])
                    for event in events:
                        if (event.get("type") == "m.room.message"
                                and event.get("sender") != self.user_id):
                            body = event.get("content", {}).get("body", "").strip()
                            if body:
                                messages.append({
                                    "body": body,
                                    "sender": event.get("sender", ""),
                                })
                return messages, new_token
        except Exception as e:
            log(f"sync error: {e}")
        return [], since

    def drain_old_messages(self):
        token = self.get_sync_token()
        if not token:
            log("Warning: could not get sync token")
            return
        _, new_token = self.poll_messages("", token)
        self.save_sync_token(new_token)
        log("Sync token advanced, ready for new messages")
