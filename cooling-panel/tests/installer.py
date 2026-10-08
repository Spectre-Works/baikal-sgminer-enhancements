"""Offline installer checks; fake services/API, temporary filesystem only."""
import importlib.util
import json
import os
from pathlib import Path
import shlex
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parent.parent
spec = importlib.util.spec_from_file_location('installer', str(ROOT / 'install-bkb-cooling.py'))
m = importlib.util.module_from_spec(spec)
spec.loader.exec_module(m)
STOCK = ('#!/bin/bash\ncgminer=`ps -ef |grep sgminer |grep -v grep`\n'
         'if [ "$cgminer" == "" ]\n        then\n'
         '        echo `date +"%Y-%m-%d %T"`" sgminer is not running, starting now..."\n'
         + m.LAUNCH + '\nfi\n').encode()


class FakeSystem:
    def __init__(self, root, fail=None):
        self.root, self.fail = root, fail
        self.events = []
        self.running = True
        self.started = 0

    def path(self, name):
        return self.root + name

    def identity(self):
        if not self.running:
            raise ValueError('No running miner')
        return (123 + self.started, '42')

    def pause_watchdog(self):
        self.events.append('pause')
        if self.fail == 'pause':
            raise RuntimeError('Pause failure')

    def resume_watchdog(self):
        self.events.append('resume')

    def stop(self, identity):
        self.events.append('stop')
        if self.fail == 'stop':
            raise RuntimeError('Stop failure')
        self.running = False

    def start(self, args):
        self.events.append(('start', args))
        self.running = True
        self.started += 1

    def verify(self):
        self.events.append('verify')
        if self.fail == 'verify':
            raise RuntimeError('Readiness failure')
        if self.fail == 'config':
            with open(self.path(m.CONFIG), 'wb') as f:
                f.write(b'{"operator_changed_config": true}')

    def verify_original(self):
        self.events.append('original-ready')
        assert self.running


class InstallerTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(prefix='installer-test-')
        self.s = FakeSystem(self.tmp.name)
        for p in ['/var/backups', '/var/www/inc', '/var/www/ng', '/var/www/partials',
                  '/opt/scripta/bin', '/opt/scripta/startup', '/opt/scripta/etc', '/usr/local']:
            os.makedirs(self.s.path(p), exist_ok=True)
        self.originals = {m.MINER: b'original binary', m.START: STOCK, m.CONFIG: b'{"pools":[]}',
                          '/var/www/index.php': b'<script src="ng/controllers.js">\r\n</script>\r\n<script src="ng/filters.js">\r\n',
                          '/var/www/partials/status.html': b'<h3 ng-show="status.devs">Devices</h3>\n'}
        for p, data in self.originals.items():
            with open(self.s.path(p), 'wb') as f:
                f.write(data)
        self.files = {m.BIN_NAME: b'release binary'}
        for src in m.WEB:
            self.files[src] = (ROOT / 'package' / src).read_bytes()
        self.owner = (os.getuid(), os.getgid())
        self.signals = patch.object(m.signal, 'signal')
        self.signals.start()

    def tearDown(self):
        self.signals.stop()
        self.tmp.cleanup()

    def install(self):
        desired, launch = m.plan(self.s, self.files, 'preserve')
        return m.install(self.s, desired, launch, self.owner, self.owner)

    def assert_originals(self):
        for p, data in self.originals.items():
            self.assertEqual(m.read(self.s.path(p)), data)
        for p in m.TARGETS - set(self.originals):
            self.assertFalse(os.path.exists(self.s.path(p)), p)

    def test_success(self):
        backup = self.install()
        manifest = json.loads(m.read(backup + '/manifest.json'))
        self.assertEqual(manifest['phase'], 'validated')
        self.assertEqual(self.s.events[0], 'pause')
        self.assertEqual(self.s.events[-1], 'resume')
        self.assertEqual(m.read(self.s.path(m.MINER)), b'release binary')
        self.assertEqual(m.preference(m.read(self.s.path(m.PREF)))['mode'], 'auto')
        self.assertEqual(os.stat(self.s.path(m.PREF)).st_mode & 0o777, 0o600)
        self.assertEqual(m.read(self.s.path(m.CONFIG)), self.originals[m.CONFIG])

    def test_failed_validation_restores_and_restarts(self):
        self.s.fail = 'verify'
        with self.assertRaises(RuntimeError):
            self.install()
        self.assert_originals()
        self.assertTrue(self.s.running)
        self.assertEqual(self.s.events[-1], 'resume')
        self.assertIn('original-ready', self.s.events)
        starts = [e for e in self.s.events if isinstance(e, tuple)]
        self.assertEqual(starts[-1][1][-2:], ['--baikal-fan', '100'])

    def test_failed_stop_does_not_replace_files(self):
        self.s.fail = 'stop'
        with self.assertRaises(RuntimeError):
            self.install()
        self.assert_originals()
        self.assertEqual(self.s.events, ['pause', 'stop', 'resume'])

    def test_failed_watchdog_pause_no_mutation(self):
        self.s.fail = 'pause'
        with self.assertRaises(RuntimeError):
            self.install()
        self.assert_originals()
        self.assertTrue(self.s.running)
        self.assertEqual(self.s.events, ['pause', 'resume'])

    def test_partial_write_failure_restores_every_original(self):
        original_atomic = m.atomic
        failed = [False]
        def failure(path, data, *args):
            if path == self.s.path(m.MINER) and data == b'release binary' and not failed[0]:
                failed[0] = True
                raise OSError('Simulated disk failure')
            return original_atomic(path, data, *args)
        with patch.object(m, 'atomic', side_effect=failure):
            with self.assertRaises(OSError):
                self.install()
        self.assert_originals()
        self.assertTrue(self.s.running)
        self.assertEqual(self.s.events[-1], 'resume')

    def test_interruption_after_stop_still_restarts_original(self):
        def interrupted(identity):
            self.s.running = False
            raise KeyboardInterrupt('Interrupted after miner exit')
        with patch.object(self.s, 'stop', side_effect=interrupted):
            with self.assertRaises(KeyboardInterrupt):
                self.install()
        self.assert_originals()
        self.assertTrue(self.s.running)
        self.assertIn('original-ready', self.s.events)

    def test_config_change_not_overwritten_during_recovery(self):
        self.s.fail = 'config'
        with self.assertRaises(RuntimeError):
            self.install()
        self.assertEqual(m.read(self.s.path(m.MINER)), self.originals[m.MINER])
        self.assertEqual(m.read(self.s.path(m.CONFIG)), b'{"operator_changed_config": true}')
        self.assertTrue(self.s.running)

    def test_noop_requires_correct_permissions(self):
        self.install()
        desired, _ = m.plan(self.s, self.files, 'preserve')
        self.assertTrue(m.already_installed(self.s, desired, self.owner, self.owner))
        os.chmod(self.s.path(m.PREF), 0o644)
        self.assertFalse(m.already_installed(self.s, desired, self.owner, self.owner))

    def test_watchdog_recovery_failure_is_explicit(self):
        with patch.object(self.s, 'resume_watchdog', side_effect=RuntimeError('Service error')):
            with self.assertRaisesRegex(RuntimeError, 'CRITICAL: cron restoration failed'):
                self.install()

    def test_preserve_preference_and_idempotent_integration(self):
        os.makedirs(self.s.path('/opt/scripta/etc/cooling'))
        value = b'{"version":1,"mode":"manual","duty":33}'
        with open(self.s.path(m.PREF), 'wb') as f:
            f.write(value)
        desired, _ = m.plan(self.s, self.files, 'preserve')
        self.assertEqual(desired[m.PREF], value)
        for p in (m.START, '/var/www/index.php', '/var/www/partials/status.html'):
            with open(self.s.path(p), 'wb') as f:
                f.write(desired[p])
        again, _ = m.plan(self.s, self.files, 'preserve')
        self.assertEqual(desired, again)
        self.assertIn(b'\r\n', desired['/var/www/index.php'])
        self.assertIn(b'pgrep -x sgminer', desired[m.START])

    def test_invalid_preference_fails_before_stop(self):
        for duty in [True, 9, 101, '25', 25.5]:
            with self.assertRaises(ValueError):
                m.preference(json.dumps({'version': 1, 'mode': 'manual', 'duty': duty}).encode())

    def test_custom_startup_rejected(self):
        for bad in [STOCK + b'curl https://example.com\n', STOCK.replace(b'--api-listen', b'--api-listen --other'),
                    STOCK + (m.LAUNCH + '\n').encode()]:
            with self.assertRaises(ValueError):
                m.startup(bad)

    def test_ambiguous_web_hooks_rejected(self):
        anchor = '<h3 ng-show="status.devs">Devices</h3>'
        for text in ['', anchor + anchor]:
            with self.assertRaises(ValueError):
                m.integrate(text.encode(), anchor, 'hook')

    def test_custom_web_include_rejected(self):
        with open(self.s.path('/var/www/index.php'), 'ab') as f:
            f.write(b'<script src="ng/cooling.js" defer></script>')
        with self.assertRaises(ValueError):
            m.plan(self.s, self.files, 'preserve')

    def test_corrupt_backup_rejected_without_displacing_files(self):
        backup = self.install()
        manifest = json.loads(m.read(backup + '/manifest.json'))
        entry = manifest['files'][m.MINER]
        with open(backup + '/' + entry['copy'], 'wb') as f:
            f.write(b'corrupted backup')
        current = {p: m.read(self.s.path(p)) for p in m.TARGETS}
        with self.assertRaises(ValueError):
            m.restore_files(self.s, backup, manifest)
        self.assertEqual(current, {p: m.read(self.s.path(p)) for p in m.TARGETS})

    def test_explicit_rollback_preserves_displaced_files(self):
        backup = self.install()
        m.rollback(self.s, backup)
        self.assert_originals()
        self.assertTrue(self.s.running)
        self.assertTrue(any(name.startswith('displaced-') for name in os.listdir(backup)))

    def test_modified_installation_blocks_rollback(self):
        backup = self.install()
        with open(self.s.path('/var/www/f_fan.php'), 'ab') as f:
            f.write(b'operator edit')
        events = self.s.events[:]
        with self.assertRaises(ValueError):
            m.rollback(self.s, backup)
        self.assertEqual(events, self.s.events)

    def test_unknown_manifest_target_rejected(self):
        backup = self.install()
        manifest = json.loads(m.read(backup + '/manifest.json'))
        manifest['files']['/etc/passwd'] = {}
        with self.assertRaises(ValueError):
            m.restore_files(self.s, backup, manifest)

    def test_release_asset_pins(self):
        with tempfile.TemporaryDirectory(prefix='bad-assets-') as tmp:
            with open(tmp + '/SHA256SUMS', 'w') as f:
                f.write('0' * 64 + '  ' + m.BIN_NAME + '\n')
            with self.assertRaises(ValueError):
                m.artifacts(tmp)

    @unittest.skipUnless(os.environ.get('BKB_RELEASE_ASSETS'), 'Provide BKB_RELEASE_ASSETS for actual pinned release assets')
    def test_actual_release_install_and_rollback_offline(self):
        self.files = m.artifacts(os.environ['BKB_RELEASE_ASSETS'])
        backup = self.install()
        self.assertEqual(m.digest(m.read(self.s.path(m.MINER))), m.PINS[m.BIN_NAME])
        for src, dst in m.WEB.items():
            self.assertEqual(m.read(self.s.path(dst)), self.files[src])
        m.rollback(self.s, backup)
        self.assert_originals()


if __name__ == '__main__':
    unittest.main()
