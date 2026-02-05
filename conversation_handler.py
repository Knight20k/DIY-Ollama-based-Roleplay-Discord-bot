import json
import os
import base64
from cryptography.fernet import Fernet
from typing import Dict, List
import time


class ConversationHandler:
    """
    Handles ALL persistent state:
    - Conversation history
    - User moods
    - Channel moods
    - Channel activation flags
    - Encryption / disk storage

    This file NEVER talks to Discord.
    """

    # ===============================
    # INIT / LOAD / SAVE
    # ===============================

    def __init__(self, memory_file: str, encryption_key: bytes):
        self.memory_file = memory_file
        self.fernet = Fernet(base64.urlsafe_b64encode(encryption_key[:32]))

        # Main memory structure
        self.memory = {
            "guilds": {},
            "dms": {}
        }

        # Channel-level mood toggle + state
        self.channel_mood_enabled: Dict[str, bool] = {}
        self.channel_moods: Dict[str, Dict] = {}

        self.load()

        self.memory.setdefault("bot_reply_counters", {})


    # ===============================
    # FILE IO
    # ===============================

    def load(self):
        if not os.path.exists(self.memory_file):
            return

        try:
            with open(self.memory_file, "rb") as f:
                decrypted = self.fernet.decrypt(f.read())
                data = json.loads(decrypted.decode("utf-8"))

                self.memory = data.get("memory", self.memory)
                self.channel_mood_enabled = data.get("channel_mood_enabled", {})
                self.channel_moods = data.get("channel_moods", {})

        except Exception as e:
            print(f"[WARN] Failed to load memory: {e}")

    def save(self):
        try:
            payload = {
                "memory": self.memory,
                "channel_mood_enabled": self.channel_mood_enabled,
                "channel_moods": self.channel_moods
            }

            encrypted = self.fernet.encrypt(
                json.dumps(payload).encode("utf-8")
            )

            with open(self.memory_file, "wb") as f:
                f.write(encrypted)

        except Exception as e:
            print(f"[ERROR] Failed to save memory: {e}")

    # ===============================
    # HELPERS
    # ===============================

    def _default_mood(self):
        return {
            "confidence": 0.5,
            "patience": 0.5,
            "affection": 0.5,
            "last_interaction": time.time()
        }

    def _get_storage(self, channel_id: str):
        channel_id = str(channel_id)

        if channel_id.startswith("dm-"):
            return self.memory["dms"]
        else:
            return self.memory["guilds"]


    def get_bot_reply_count(self, channel_id):
        return self.memory.get("bot_reply_counters", {}).get(channel_id, 0)

    def increment_bot_reply_count(self, channel_id):
        self.memory.setdefault("bot_reply_counters", {})
        self.memory["bot_reply_counters"][channel_id] = (
            self.memory["bot_reply_counters"].get(channel_id, 0) + 1
        )

    def reset_bot_reply_count(self, channel_id):
        self.memory.setdefault("bot_reply_counters", {})
        self.memory["bot_reply_counters"][channel_id] = 0


    # ===============================
    # CONVERSATION HISTORY
    # ===============================

    def add_message(self, channel_id, role, content, user_id):
        storage = self._get_storage(channel_id)

        storage.setdefault(channel_id, {})
        storage[channel_id].setdefault(user_id, {
            "history": [],
            "mood": self._default_mood()
        })

        storage[channel_id][user_id]["history"].append({
            "role": role,
            "content": content
        })

        self.save()

    def get_history(self, channel_id, user_id) -> List[Dict]:
        storage = self._get_storage(channel_id)
        return storage.get(channel_id, {}).get(user_id, {}).get("history", [])

    def reset_channel_user(self, channel_id, user_id):
        storage = self._get_storage(channel_id)
        if channel_id in storage and user_id in storage[channel_id]:
            del storage[channel_id][user_id]
            self.save()

    # ===============================
    # USER MOODS
    # ===============================

    def get_mood(self, channel_id, user_id):
        storage = self._get_storage(channel_id)
        storage.setdefault(channel_id, {})
        storage[channel_id].setdefault(user_id, {
            "history": [],
            "mood": self._default_mood()
        })
        return storage[channel_id][user_id]["mood"]

    def update_mood(self, channel_id, user_id, delta: dict):
        mood = self.get_mood(channel_id, user_id)
        for k, v in delta.items():
            mood[k] = max(0.0, min(1.0, mood[k] + v))
        mood["last_interaction"] = time.time()
        self.save()

    # ===============================
    # CHANNEL MOODS
    # ===============================

    def is_channel_mood_enabled(self, channel_id):
        return bool(self.channel_mood_enabled.get(channel_id, False))

    def toggle_channel_mood(self, channel_id):
        state = not self.channel_mood_enabled.get(channel_id, False)
        self.channel_mood_enabled[channel_id] = state
        self.save()
        return state

    def get_channel_mood(self, channel_id):
        self.channel_moods.setdefault(channel_id, self._default_mood())
        return self.channel_moods[channel_id]

    def update_channel_mood(self, channel_id, delta: dict):
        mood = self.get_channel_mood(channel_id)
        for k, v in delta.items():
            mood[k] = max(0.0, min(1.0, mood[k] + v))
        mood["last_interaction"] = time.time()
        self.save()

    def apply_cooldown_recovery(self, mood: dict):

        #Gradually restores patience over time if the user stops provoking.

        now = time.time()
        last = mood.get("last_interaction", now)

        elapsed = now - last  # seconds since last message

        # Only recover if at least 30 seconds passed
        if elapsed < 30:
            return

        # Recovery rate: patience per minute
        recovery = (elapsed / 60) * 0.04  # tune this

        mood["patience"] = min(1.0, mood["patience"] + recovery)

        # Update timestamp
        mood["last_interaction"] = now


    # ===============================
    # CHANNEL ACTIVATION
    # ===============================

    def activate_channel(self, guild_id, channel_id):
        self.memory.setdefault("active_channels", {})
        self.memory["active_channels"].setdefault(guild_id, [])

        if channel_id not in self.memory["active_channels"][guild_id]:
            self.memory["active_channels"][guild_id].append(channel_id)

        self.save()

    def deactivate_channel(self, guild_id, channel_id):
        if channel_id in self.memory["active_channels"].get(guild_id, []):
            self.memory["active_channels"][guild_id].remove(channel_id)

        self.save()

    def is_channel_active(self, guild_id, channel_id):
        return channel_id in self.memory.get("active_channels", {}).get(guild_id, [])
