import pytest
from fastapi.testclient import TestClient


@pytest.fixture
def client(tmp_path, monkeypatch):
    monkeypatch.setenv("DB_PATH", str(tmp_path / "test.db"))
    monkeypatch.setenv("LLM_MOCK", "true")
    monkeypatch.delenv("MASSIVE_API_KEY", raising=False)
    monkeypatch.setenv("STATIC_DIR", str(tmp_path / "static"))
    (tmp_path / "static").mkdir()
    (tmp_path / "static" / "index.html").write_text("<html>INDEX</html>")
    (tmp_path / "static" / "app.js").write_text("console.log(1)")
    from app.main import create_app

    with TestClient(create_app()) as c:
        yield c
