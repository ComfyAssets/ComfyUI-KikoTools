"""Token resolution: tokens come from the server, never from the workflow by default."""

import pytest

from kikotools.tools.model_downloader import tokens
from kikotools.tools.model_downloader.detector import URLDetector

TOKEN_VARS = (
    "CIVITAI_API_KEY",
    "CIVITAI_API_TOKEN",
    "CIVITAI_TOKEN",
    "HF_TOKEN",
    "HUGGING_FACE_HUB_TOKEN",
    "HF_TOKEN_PATH",
    "HF_HOME",
)


@pytest.fixture(autouse=True)
def clean_env(monkeypatch, tmp_path):
    for name in TOKEN_VARS:
        monkeypatch.delenv(name, raising=False)
    # No real `hf auth login` token leaks into the tests
    monkeypatch.setenv("HF_HOME", str(tmp_path / "hf"))


class TestResolveToken:
    def test_override_wins(self, monkeypatch):
        monkeypatch.setenv("CIVITAI_API_KEY", "env")
        assert tokens.resolve_token("civitai", "  typed  ") == "typed"

    @pytest.mark.parametrize(
        "name", ["CIVITAI_API_KEY", "CIVITAI_API_TOKEN", "CIVITAI_TOKEN"]
    )
    def test_civitai_env(self, monkeypatch, name):
        monkeypatch.setenv(name, " civ ")
        assert tokens.resolve_token("civitai", "") == "civ"

    @pytest.mark.parametrize("name", ["HF_TOKEN", "HUGGING_FACE_HUB_TOKEN"])
    def test_huggingface_env(self, monkeypatch, name):
        monkeypatch.setenv(name, "hf_x")
        assert tokens.resolve_token("huggingface", None) == "hf_x"

    def test_huggingface_login_file(self, tmp_path):
        (tmp_path / "hf").mkdir()
        (tmp_path / "hf" / "token").write_text("hf_saved\n")
        assert tokens.resolve_token("huggingface") == "hf_saved"

    def test_huggingface_token_path(self, monkeypatch, tmp_path):
        path = tmp_path / "elsewhere"
        path.write_text("hf_path")
        monkeypatch.setenv("HF_TOKEN_PATH", str(path))
        assert tokens.resolve_token("huggingface") == "hf_path"

    def test_providers_do_not_share_tokens(self, monkeypatch):
        monkeypatch.setenv("HF_TOKEN", "hf_x")
        assert tokens.resolve_token("civitai") is None
        monkeypatch.setenv("CIVITAI_API_KEY", "civ")
        monkeypatch.delenv("HF_TOKEN")
        assert tokens.resolve_token("huggingface") is None

    def test_unknown_provider_only_uses_override(self, monkeypatch):
        monkeypatch.setenv("HF_TOKEN", "hf_x")
        assert tokens.resolve_token("custom") is None
        assert tokens.resolve_token("custom", "t") == "t"


class TestDetectorTokens:
    def test_civitai_gets_env_token(self, monkeypatch):
        monkeypatch.setenv("CIVITAI_API_KEY", "civ")
        d = URLDetector().get_downloader("https://civitai.com/models/1")
        assert d.token == "civ"

    def test_huggingface_gets_env_token(self, monkeypatch):
        monkeypatch.setenv("HF_TOKEN", "hf_x")
        d = URLDetector().get_downloader("https://huggingface.co/a/b/resolve/main/c")
        assert d.token == "hf_x"

    def test_custom_host_never_gets_env_tokens(self, monkeypatch):
        monkeypatch.setenv("HF_TOKEN", "hf_x")
        monkeypatch.setenv("CIVITAI_API_KEY", "civ")
        d = URLDetector().get_downloader("https://example.com/model.safetensors")
        assert d.token is None
