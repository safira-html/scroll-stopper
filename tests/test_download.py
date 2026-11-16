import importlib.util
import time

import pytest

from ss_lib.download import FAILURE_MESSAGE, DownloadError, download

requires_yt_dlp = pytest.mark.skipif(importlib.util.find_spec("yt_dlp") is None,
                                     reason="yt_dlp ausente neste venv (use ~/.cache/scroll-stopper/venv)")

EXPECTED = ("Não consegui baixar esse link. Envie o arquivo do vídeo, ou confira se ele é público "
            "e se você tem direito de usar esse conteúdo.")


def test_failure_message_is_exact():
    assert FAILURE_MESSAGE == EXPECTED


@requires_yt_dlp
@pytest.mark.parametrize("url", ["notaurl", "http://127.0.0.1:9/video.mp4"])
def test_download_failure_message(url, tmp_path):
    # sem rede: texto que nao e link e porta local fechada falham na hora
    started = time.monotonic()
    with pytest.raises(DownloadError) as info:
        download(url, tmp_path / "video" / "source.mp4")
    assert str(info.value) == EXPECTED
    assert time.monotonic() - started < 30
    assert not (tmp_path / "video" / "source.mp4").exists()
