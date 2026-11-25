from types import SimpleNamespace

from app.assets import fetch, fetch_all


def test_fetch_downloads_once(tmp_path):
    src = tmp_path / "src.bin"
    src.write_bytes(b"weights")
    dest = tmp_path / "out" / "best.pt"
    assert fetch(src.as_uri(), dest).read_bytes() == b"weights"
    src.write_bytes(b"changed")
    assert fetch(src.as_uri(), dest).read_bytes() == b"weights"  # existing file is kept
    assert not dest.with_name("best.pt.part").exists()


def test_fetch_all_skips_without_urls(tmp_path):
    fetch_all(SimpleNamespace(weights_url="", weights=str(tmp_path / "w.pt"),
                              camera_source_url="", camera_source="0"))
    assert not (tmp_path / "w.pt").exists()
