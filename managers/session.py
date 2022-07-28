import asyncio
from enum import Enum
from uuid import uuid4
from time import time
import logging


class SessionType(Enum):
    SELECT_USER = 1
    CONFIRM_REQUEST = 2


class SessionException(Exception):
    pass


class SessionTypeException(Exception):
    pass


logger = logging.getLogger(__name__)

class SessionManager:
    def __init__(self, session_ttls):
        self.storage = {}
        self.users_sessions = {}
        self.session_ttls = session_ttls

    def _get_session_ttl(self, session_type):
        if session_type not in SessionType:
            raise SessionTypeException(f"Invalid session type provided: {session_type}")
        
        if session_type not in self.session_ttls:
            raise SessionTypeException(f"TTL for session type {session_type} is not set")
        
        return self.session_ttls[session_type]

    def _log_active_sessions(self):
        logger.info(f"Session storage: {self.storage.keys()}")
        logger.info(f"Users sessions storage: {self.users_sessions}")

    async def _expired_callback(self, id, session_ttl, expired_callback):
        logger.info(f"Expired callback was registered (session_id={id}, session_ttl={session_ttl})")
        
        await asyncio.sleep(session_ttl)

        logger.info(f"Executing registered callback (session_id={id})")
        try:
            await expired_callback(self.storage[id])
        except Exception as err:
            logger.error(f"Error executing registered callback (session_id={id}): {err}")

        logger.warning(f"Session will be deleted (session_id={id})")
        self.delete_session(id, cancel_task=False)

    def create_session(
        self,
        type,
        user,
        expired_callback,
        data,
        id = uuid4()
    ):
        if id in self.storage:
            raise SessionException(f"Session with id={id} already exists")

        session_ttl = self._get_session_ttl(type)
        expire_time = time() + session_ttl
        expire_task = asyncio.create_task(self._expired_callback(id, session_ttl, expired_callback))

        self.storage[id] = {
            "id": id,
            "type": type,
            "user": user,
            "expire_time": expire_time,
            "expire_task": expire_task,
            "data": data
        }

        if user.id not in self.users_sessions:
            self.users_sessions[user.id] = set()
        self.users_sessions[user.id].add(id)

        logger.info(f"Session was created (session_id={id})")
        self._log_active_sessions()

        return id

    def delete_session(self, id, cancel_task=True):
        if id not in self.storage:
            raise SessionException(f"Session with id={id} does not exist")

        if cancel_task:
            self.storage[id]["expire_task"].cancel()
            logger.info(f"Expire task was canceled (session_id={id})")

        session = self.storage.pop(id)

        self.users_sessions[session["user"].id].remove(session["id"])
        if len(self.users_sessions[session["user"].id]) == 0:
            del self.users_sessions[session["user"].id]

        logger.info(f"Session was deleted (session_id={session['id']})")
        self._log_active_sessions()

    def session_is_expired(self, session):
        return time() > session["expire_time"]

    def get_session(self, id):
        if id not in self.storage:
            raise SessionException(f"Session with id={id} does not exist")

        return self.storage[id]

    def user_has_session(self, user_id, filter_by_type = None):
        if user_id not in self.users_sessions:
            return False

        if filter_by_type:
            sessions = list(self.users_sessions[user_id])
            sessions_of_type = list(filter(lambda session_id: self.storage[session_id]["type"] == filter_by_type, sessions))
            return len(sessions_of_type) > 0
        
        return len(self.users_sessions[user_id]) > 0
