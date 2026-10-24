#!/usr/bin/env python3
"""Fail when release identities drift; run from any working directory."""
from pathlib import Path
import re
root = Path(__file__).resolve().parent.parent
version = (root / 'VERSION').read_text().strip()
assert re.fullmatch(r'[0-9]+\.[0-9]+\.[0-9]+', version), 'Invalid VERSION'
patch = (root / 'patches/0002-automatic-baikal-fan-control.patch').read_text()
assert '+#define SPECTRE_WORKS_VERSION "' + version + '"' in patch
assert '"-spectreworks-v" SPECTRE_WORKS_VERSION' in patch
assert '"Enhancement Version", SPECTRE_WORKS_VERSION' in patch
panel = (root / 'cooling-panel/package/web/partials/fan.html').read_text()
assert '<span>Panel v' + version + '</span>' in panel
assert 'cooling.state.miner_version' in panel
installer = (root / 'cooling-panel/install-bkb-cooling.py').read_text()
assert "RELEASE_VERSION = '" + version + "'" in installer
assert "BIN_NAME = 'sgminer-baikal-bkb-fan-v" + version + "-armhf'" in installer
assert "PANEL_NAME = 'bkb-cooling-panel-v" + version + ".tar.gz'" in installer
assert 'BK-B unified installer v' + version in installer
assert '(v' + version + ' miner + v' + version + ' panel)' in installer
assert (root / ('docs/release-v' + version + '.md')).exists()
assert 'v' + version in (root / 'README.md').read_text()
print('Release version consistency passed: v' + version)
