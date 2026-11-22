from hashlib import sha256
from io import BytesIO
from unittest.mock import Mock

import pytest
from flyflip import data

@pytest.mark.parametrize('corrupt', [False, True])
def test_download_checks_bytes_before_publishing(tmp_path, monkeypatch, corrupt):
    expected = b'csv\n1\n'
    monkeypatch.setattr(data, 'SOURCES', {'sample.csv': ('owner/repo', 'abc123', sha256(expected).hexdigest())})
    opener = Mock(return_value=BytesIO(b'bad' if corrupt else expected))
    monkeypatch.setattr(data, 'urlopen', opener)
    if corrupt:
        with pytest.raises(ValueError, match='SHA-256 mismatch'):
            data.fetch(tmp_path)
        assert not (tmp_path / 'sample.csv').exists()
        assert not (tmp_path / 'sample.partial').exists()
    else:
        data.fetch(tmp_path)
        assert (tmp_path / 'sample.csv').read_bytes() == expected
        data.fetch(tmp_path)
        assert opener.call_count == 1
    request = opener.call_args.args[0]
    assert request.full_url == 'https://raw.githubusercontent.com/owner/repo/abc123/data/sample.csv'
