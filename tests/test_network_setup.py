import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

import pytest


@pytest.mark.skipif(not shutil.which("powershell.exe"), reason="Windows PowerShell required")
def test_certificate_preparation_with_windows_powershell(tmp_path):
    data = tmp_path / "Alice data with spaces"
    data.mkdir()
    # The preparation helper only checks that administrator setup has occurred.
    (data / "network-auth.json").write_text("{}")
    environment = {**os.environ, "ALICE_HOME": str(data)}
    executable = sys.executable.replace("'", "''")
    command = (
        f"$detailsJson = & '{executable}' -m alice_os.network_setup --hostname Aliceos.local; "
        "if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }; "
        "$details = $detailsJson | ConvertFrom-Json; "
        "$details | ConvertTo-Json -Compress"
    )
    result = subprocess.run(
        ["powershell.exe", "-NoProfile", "-NonInteractive", "-Command", command],
        cwd=Path(__file__).resolve().parents[1], env=environment,
        capture_output=True, text=True, timeout=30,
    )
    assert result.returncode == 0, result.stderr
    details = json.loads(result.stdout)
    assert Path(details["ca_path"]) == data / "tls" / "alice-local-ca.crt"
    assert Path(details["ca_path"]).is_file()
    assert Path(details["runtime_python"]).is_file()
