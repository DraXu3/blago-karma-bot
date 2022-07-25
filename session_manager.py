import asyncio
import logging

class SessionManager:
    def __init__(self, session_ttl):
        self.storage = {}
        self.session_ttl = session_ttl

    def create(
        self,
        id,
        create_time,
        command_message,
        requesting_user,
        voted_user,
        vote_type,
        vote_reason,
        on_expired
    ):
        if id in self.storage:
            logging.warn(f"Session with id = {id} already exists. Will be overriden")

        async def _on_expired_callback():
            await asyncio.sleep(self.session_ttl)
            await on_expired()

        callback_task = asyncio.create_task(_on_expired_callback())

        self.storage[id] = {
            "id": id,
            "create_time": create_time,
            "expired": create_time + self.session_ttl,
            "command_message": command_message,
            "requesting_user": requesting_user,
            "voted_user": voted_user,
            "vote_type": vote_type,
            "vote_reason": vote_reason,
            "callback_task": callback_task
        }

    def delete(self, id):
        if id not in self.storage:
            logging.warn(f"Session with id = {id} does not exist. Nothing to delete")
            return

        self.storage[id]["callback_task"].cancel()
        self.storage.pop(id)

    def get(self, id):
        if id not in self.storage:
            logging.warn(f"Session with id = {id} does not exist")
            return None

        return self.storage[id]
