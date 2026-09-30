import subprocess
import sys

import pytest

# Each snippet is the *first* thing a fresh interpreter imports -- the way a script or a
# shell would start -- which is exactly where unresolved cross-feature relationships bite.
ENTRY_POINTS = [
    "import app.features.geographies.models",
    "import app.features.profiles.service",
    "import app.features.businesses.models",
    "import scripts.seed",
    "import scripts.create_admin",
]


@pytest.mark.parametrize("first_import", ENTRY_POINTS)
def test_mappers_configure_from_any_entry_point(first_import):
    result = subprocess.run(
        [sys.executable, "-c", f"{first_import}\nfrom sqlalchemy.orm import configure_mappers\nconfigure_mappers()"],
        capture_output=True, text=True, timeout=60,
    )
    assert result.returncode == 0, result.stderr[-1500:]
