import pytest

from hr_rag.config import Settings
from hr_rag.models import InvalidInputError


def test_settings_read_validated_environment(monkeypatch, tmp_path):
    monkeypatch.setenv("HR_RAG_CORPUS_DIR", str(tmp_path / "policies"))
    monkeypatch.setenv("HR_RAG_INDEX_DIR", str(tmp_path / "index"))
    monkeypatch.setenv("HR_RAG_TOP_K", "7")
    monkeypatch.setenv("HR_RAG_CHUNK_TOKENS", "100")
    monkeypatch.setenv("HR_RAG_CHUNK_OVERLAP", "10")
    monkeypatch.setenv("HR_RAG_EMBEDDING_MODEL", "local-model")
    monkeypatch.setenv("GROQ_MODEL", "test-generation-model")
    settings = Settings.from_environment()
    assert settings.corpus_dir == tmp_path / "policies"
    assert settings.index_dir == tmp_path / "index"
    assert settings.top_k == 7
    assert settings.chunking.max_tokens == 100
    assert settings.chunking.overlap_tokens == 10
    assert settings.embedding_model == "local-model"
    assert settings.answer_model == "test-generation-model"


def test_invalid_numeric_environment_is_reported(monkeypatch):
    monkeypatch.setenv("HR_RAG_TOP_K", "five")
    with pytest.raises(InvalidInputError, match="must be integers"):
        Settings.from_environment()
