from time import time


class UserVoiceConnection:
    "Stores user-related data to calculate voice activity XP"
    def __init__(self):
        self.connection_time = time()
        self.last_xp_time: float | None = None

    def time_since_connection(self) -> float:
        "Returns the time since the user connected to the voice channel"
        return time() - self.connection_time

    def time_since_last_xp(self) -> float | None:
        "Returns the time since the user received XP"
        if self.last_xp_time is None:
            return None
        return time() - self.last_xp_time
