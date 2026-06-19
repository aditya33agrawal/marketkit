import pytest

from marketkit import cache, config


@pytest.fixture(autouse=True)
def isolated_cache_dir(tmp_path, monkeypatch):
    cache_dir = tmp_path / "marketkit-cache"
    monkeypatch.setattr(config, "CACHE_DIR", cache_dir)
    monkeypatch.setattr(cache, "CACHE_DIR", cache_dir)
    yield
