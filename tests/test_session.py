import pytest


def test_session_creation():
    from neurosim.session import Session

    disorder = {"name": "Test Disorder", "symptoms": "...", "brain_region": "...", "how_to_test": "...", "category": "Test"}
    session = Session(role="clinician", disorder=disorder)
    assert session.session_id  # non-empty string
    assert session.role == "clinician"
    assert session.disorder == disorder
    assert session.messages == []
    assert session.active is True


def test_session_add_message():
    from neurosim.session import Session

    disorder = {"name": "Test", "symptoms": "...", "brain_region": "...", "how_to_test": "...", "category": "Test"}
    session = Session(role="clinician", disorder=disorder)
    session.add_message("user", "Hello doctor")
    session.add_message("assistant", "Hello, what brings you in?")
    assert len(session.messages) == 2
    assert session.messages[0] == {"role": "user", "content": "Hello doctor"}
    assert session.messages[1] == {"role": "assistant", "content": "Hello, what brings you in?"}


def test_session_manager_create_and_get():
    from neurosim.session import SessionManager

    manager = SessionManager()
    disorder = {"name": "Test", "symptoms": "...", "brain_region": "...", "how_to_test": "...", "category": "Test"}
    session = manager.create_session(role="clinician", disorder=disorder)
    retrieved = manager.get_session(session.session_id)
    assert retrieved is session


def test_session_manager_get_nonexistent():
    from neurosim.session import SessionManager

    manager = SessionManager()
    assert manager.get_session("nonexistent") is None


def test_session_manager_deactivate():
    from neurosim.session import SessionManager

    manager = SessionManager()
    disorder = {"name": "Test", "symptoms": "...", "brain_region": "...", "how_to_test": "...", "category": "Test"}
    session = manager.create_session(role="patient", disorder=disorder)
    manager.deactivate_session(session.session_id)
    retrieved = manager.get_session(session.session_id)
    assert retrieved.active is False
