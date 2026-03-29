import uuid
from dataclasses import dataclass, field


@dataclass
class Session:
    role: str
    disorder: dict
    session_id: str = field(default_factory=lambda: uuid.uuid4().hex)
    messages: list[dict] = field(default_factory=list)
    active: bool = True

    def add_message(self, role: str, content: str) -> None:
        self.messages.append({"role": role, "content": content})


class SessionManager:
    def __init__(self) -> None:
        self._sessions: dict[str, Session] = {}

    def create_session(self, role: str, disorder: dict) -> Session:
        session = Session(role=role, disorder=disorder)
        self._sessions[session.session_id] = session
        return session

    def get_session(self, session_id: str) -> Session | None:
        return self._sessions.get(session_id)

    def deactivate_session(self, session_id: str) -> None:
        session = self._sessions.get(session_id)
        if session:
            session.active = False
