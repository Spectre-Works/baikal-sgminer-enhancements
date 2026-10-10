#!/usr/bin/env python3
"""BK-B unified installer v0.3.2, for pinned fan-only payloads.

Offline, root-only BK-B/Scripta installer. Python 3.5+, GPL-3.0.

Default is a read-only preflight. No firmware access or automatic download.
"""
import argparse
import fcntl
import hashlib
import io
import json
import os
import platform
import pwd
import re
import shlex
import signal
import socket
import stat
import struct
import subprocess
import sys
import tarfile
import tempfile
import time

BIN_NAME = 'sgminer-baikal-bkb-fan-v0.3.0-armhf'
PANEL_NAME = 'bkb-cooling-panel-v0.3.2.tar.gz'
PINS = {BIN_NAME: '7ed2720baeba0bfccd7c48d9ba2ad57d760fbea22b28faf888694158f56c406e',
        PANEL_NAME: 'abd770cfe3cbe1b6c9f3df6a45a781bab922c154797c94f437d9b6be8475520c'}
MINER = '/opt/scripta/bin/sgminer'
CONFIG = '/opt/scripta/etc/miner.conf'
START = '/opt/scripta/startup/miner-start.sh'
PREF = '/opt/scripta/etc/cooling/fan-settings.json'
HELPER = '/usr/local/libexec/bkb-cooling-startup.py'
WEB = {'web/f_fan.php': '/var/www/f_fan.php',
       'web/inc/fan.inc.php': '/var/www/inc/fan.inc.php',
       'web/ng/cooling.js': '/var/www/ng/cooling.js',
       'web/partials/fan.html': '/var/www/partials/fan.html',
       'startup/bkb-cooling-startup.py': HELPER}
TARGETS = set(list(WEB.values()) + [MINER, START, PREF, '/var/www/index.php', '/var/www/partials/status.html'])
SECURE_DIRS = ['/opt/scripta', '/opt/scripta/startup', '/opt/scripta/bin']
NEW_DIRS = ['/usr/local/libexec', '/opt/scripta/etc/cooling']
LAUNCH = '/usr/bin/screen -dmS sgminer ' + MINER + ' -c ' + CONFIG + ' --api-listen'
HOOK = '/usr/bin/python /usr/local/libexec/bkb-cooling-startup.py --background'


def digest(data):
    return hashlib.sha256(data).hexdigest()


def read(path, limit=16777216):
    if os.path.islink(path) or not stat.S_ISREG(os.stat(path).st_mode):
        raise ValueError('Expected a regular, non-symlink file: ' + path)
    with open(path, 'rb') as f:
        data = f.read(limit + 1)
    if len(data) > limit:
        raise ValueError('File exceeds size limit: ' + path)
    return data


def preference(data):
    value = json.loads(data.decode('utf-8'))
    if not isinstance(value, dict) or type(value.get('version')) is not int or value['version'] != 1:
        raise ValueError('Invalid saved cooling preference; repair it before installation')
    if value.get('mode') not in ('auto', 'manual') or type(value.get('duty')) is not int or not 10 <= value['duty'] <= 100:
        raise ValueError('Invalid saved cooling preference; repair it before installation')
    return value


def artifacts(directory):
    manifest = {}
    for line in read(os.path.join(directory, 'SHA256SUMS'), 32768).decode('ascii').splitlines():
        fields = line.split()
        if len(fields) != 2 or len(fields[0]) != 64 or fields[1].startswith('*'):
            raise ValueError('Invalid SHA256SUMS')
        if fields[1] in manifest:
            raise ValueError('Duplicate checksum entry')
        manifest[fields[1]] = fields[0]
    files = {}
    for name, expected in PINS.items():
        if manifest.get(name) != expected:
            raise ValueError('Not the supported pinned release payload: ' + name)
        files[name] = read(os.path.join(directory, name))
        if digest(files[name]) != expected:
            raise ValueError('Release checksum mismatch: ' + name)
    # Read only explicitly selected source files, never extract archive paths.
    with tarfile.open(fileobj=io.BytesIO(files[PANEL_NAME]), mode='r:gz') as archive:
        members = archive.getmembers()
        for src in WEB:
            name = 'cooling-panel/package/' + src
            matches = [m for m in members if m.name == name]
            if len(matches) != 1 or not matches[0].isfile() or matches[0].size > 262144:
                raise ValueError('Invalid panel member: ' + name)
            files[src] = archive.extractfile(matches[0]).read()
    elf = files[BIN_NAME]
    if elf[:7] != b'\x7fELF\x01\x01\x01' or elf[18:20] != b'\x28\x00' or not struct.unpack('<I', elf[36:40])[0] & 0x400:
        raise ValueError('Expected ARM32 hard-float executable')
    return files


def integrate(data, anchor, addition):
    text = data.decode('utf-8').replace('\r\n', '\n')
    if text.count(anchor) != 1 or text.count(addition) > 1:
        raise ValueError('Unrecognized/customized Scripta integration; no files changed')
    if addition in text:
        return data
    text = text.replace(anchor, addition + '\n' + anchor)
    return text.replace('\n', '\r\n' if b'\r\n' in data else '\n').encode('utf-8')


def startup(data):
    text = data.decode('utf-8').replace('\r\n', '\n')
    lines = text.splitlines()
    launch = [line for line in lines if line.startswith('/usr/bin/screen ')]
    if len(launch) != 1 or launch[0] not in (LAUNCH, LAUNCH + ' --baikal-fan 100'):
        raise ValueError('Customized startup command; adapt manually before installation')
    old = 'cgminer=`ps -ef |grep sgminer |grep -v grep`'
    exact = 'cgminer=$(pgrep -x sgminer || true)'
    if sum(lines.count(v) for v in (old, exact)) != 1 or lines.count('fi') != 1:
        raise ValueError('Unrecognized startup script')
    # Accept only the inspected stock script and the documented fan additions.
    allowed = {'#!/bin/bash', old, exact, 'if [ "$cgminer" == "" ]', 'then', 'fi',
               'echo `date +"%Y-%m-%d %T"`" sgminer is not running, starting now..."',
               LAUNCH, LAUNCH + ' --baikal-fan 100', HOOK}
    if any(line.strip() and not line.strip().startswith('#') and line.strip() not in allowed for line in lines):
        raise ValueError('Additional startup logic detected; refusing to replace it')
    if lines.count(HOOK) > 1:
        raise ValueError('Duplicate startup helper')
    text = text.replace(old, exact).replace(launch[0], LAUNCH + ' --baikal-fan 100')
    if HOOK not in lines:
        text = text.rstrip() + '\n' + HOOK + '\n'
    return text.encode('utf-8'), shlex.split(launch[0])


def atomic(path, data, mode, uid, gid):
    fd, tmp = tempfile.mkstemp(prefix='.bkb-cooling-', dir=os.path.dirname(path))
    try:
        with os.fdopen(fd, 'wb') as f:
            f.write(data)
            f.flush()
            os.fsync(f.fileno())
            os.fchmod(f.fileno(), mode)
            os.fchown(f.fileno(), uid, gid)
        os.rename(tmp, path)
        directory = os.open(os.path.dirname(path), os.O_RDONLY)
        try:
            os.fsync(directory)
        finally:
            os.close(directory)
    finally:
        if os.path.exists(tmp):
            os.unlink(tmp)  # Only this call's private, generated temporary file.


class System:
    def path(self, name):
        return name

    def command(self, args, timeout=15):
        # Never print subprocess output: config/API diagnostics can contain credentials.
        environment = dict(os.environ, PATH='/usr/sbin:/usr/bin:/sbin:/bin', LC_ALL='C')
        p = subprocess.run(args, stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=timeout, env=environment)
        if p.returncode:
            raise RuntimeError('Command failed: ' + os.path.basename(args[0]))
        return p.stdout

    def api(self, command):
        with socket.create_connection(('127.0.0.1', 4028), 1) as s:
            s.settimeout(1.5)
            s.sendall(json.dumps({'command': command}).encode('ascii'))
            data = b''
            deadline = time.monotonic() + 3
            while b'\0' not in data and time.monotonic() < deadline:
                chunk = s.recv(8192)
                if not chunk:
                    break
                data += chunk
                if len(data) > 262144:
                    raise ValueError('API response too large')
        response = json.loads(data.rstrip(b'\0').decode('utf-8'))
        if response.get('STATUS', [{}])[0].get('STATUS') != 'S':
            raise ValueError('API unavailable/rejected')
        return response

    def identity(self):
        ids = self.command(['pgrep', '-x', 'sgminer']).decode('ascii').split()
        if len(ids) != 1 or os.readlink('/proc/' + ids[0] + '/exe') != MINER:
            raise ValueError('Expected one miner process using the installed executable')
        with open('/proc/' + ids[0] + '/stat') as f:
            data = f.read()
        return (int(ids[0]), data[data.rfind(')') + 2:].split()[19])

    def pause_watchdog(self):
        self.command(['service', 'cron', 'stop'])

    def resume_watchdog(self):
        self.command(['service', 'cron', 'start'])

    def stop(self, identity):
        if self.identity() != identity:
            raise ValueError('Miner process changed before shutdown')
        os.kill(identity[0], signal.SIGTERM)
        for _ in range(100):
            if not os.path.exists('/proc/' + str(identity[0])):
                return
            time.sleep(.2)
        raise RuntimeError('Miner did not stop cleanly; no forced kill attempted')

    def start(self, args):
        self.command(args)

    def verify_original(self):
        for _ in range(30):
            try:
                self.identity()
                boards = self.api('devs').get('DEVS', [])
                if len(boards) == 3 and all(b.get('Status') == 'Alive' for b in boards):
                    return
            except (ValueError, RuntimeError, OSError):
                pass
            time.sleep(2)
        raise RuntimeError('Original miner was launched but recovery readiness is unconfirmed')

    def verify(self):
        # Backend runs as the real web account; checks ASC permissions separately.
        code = ('require "/var/www/inc/fan.inc.php"; '
                '$s=(new CoolingService("cooling_api"))->status(); '
                '$c=cooling_api("check","ascset"); '
                'if(!$s["healthy"] || !$s["ack_valid"] || $s["pending"] || $s["fault"] || '
                '$c["CHECK"][0]["Access"]!=="Y")exit(1); echo json_encode($s);')
        for _ in range(60):
            try:
                self.identity()
                raw = self.command(['sudo', '-n', '-u', 'www-data', 'php', '-r', code])
                state = json.loads(raw.decode('utf-8'))
                if state['mode'] == 'manual' and state['acknowledged'] == 100:
                    break
            except (ValueError, RuntimeError, OSError, subprocess.TimeoutExpired):
                pass
            time.sleep(2)
        else:
            raise RuntimeError('Miner/web-account readiness failed')
        self.command(['/usr/bin/python', HELPER, '--worker'], timeout=150)
        state = json.loads(self.command(['sudo', '-n', '-u', 'www-data', 'php', '-r', code]).decode('utf-8'))
        pref = preference(read(PREF, 2048))
        if state['mode'] != pref['mode'] or (pref['mode'] == 'manual' and state['acknowledged'] != pref['duty']):
            raise RuntimeError('Startup preference was not acknowledged')


def no_symlinks(path):
    while path != '/':
        if os.path.islink(path):
            raise ValueError('Symlink in installation path: ' + path)
        path = os.path.dirname(path)


def plan(system, files, mode):
    result = {MINER: files[BIN_NAME]}
    for src, dst in WEB.items():
        result[dst] = files[src]
    index = '/var/www/index.php'
    text = read(system.path(index))
    # Insert after the controller script, preserving other stock content/line endings.
    normalized = text.decode('utf-8').replace('\r\n', '\n')
    anchor = '<script src="ng/filters.js">'
    if normalized.count('<script src="ng/controllers.js">') != 1:
        raise ValueError('Controller module include missing/ambiguous')
    if 'ng/cooling.js' in normalized and not (normalized.index('ng/controllers.js') < normalized.index('ng/cooling.js') < normalized.index('ng/filters.js')):
        raise ValueError('Unexpected Cooling controller load order')
    if normalized.count('ng/cooling.js') != normalized.count('<script src="ng/cooling.js"></script>'):
        raise ValueError('Customized Cooling script include; adapt manually')
    result[index] = integrate(text, anchor, '<script src="ng/cooling.js"></script>')
    status = '/var/www/partials/status.html'
    status_data = read(system.path(status))
    addition = '<div ng-include="\'partials/fan.html\'"></div>'
    if status_data.count(b'partials/fan.html') != status_data.count(addition.encode('utf-8')):
        raise ValueError('Customized Cooling card include; adapt manually')
    result[status] = integrate(status_data, '<h3 ng-show="status.devs">Devices</h3>', addition)
    result[START], previous_launch = startup(read(system.path(START)))
    existing = read(system.path(PREF), 2048) if os.path.exists(system.path(PREF)) else None
    if existing is not None:
        preference(existing)
    if mode == 'preserve' and existing is not None:
        result[PREF] = existing
    else:
        result[PREF] = (json.dumps({'version': 1, 'mode': 'manual' if mode == 'manual100' else 'auto',
                                   'duty': 100 if mode == 'manual100' else 25}) + '\n').encode('ascii')
    return result, previous_launch


def metadata(path):
    st = os.stat(path)
    return {'mode': stat.S_IMODE(st.st_mode), 'uid': st.st_uid, 'gid': st.st_gid}


def save_manifest(backup, manifest):
    atomic(backup + '/manifest.json', json.dumps(manifest, indent=2).encode('utf-8'), 0o600, os.getuid(), os.getgid())


def backup_files(system, desired, identity, previous_launch, owner):
    parent = system.path('/var/backups')
    backup = tempfile.mkdtemp(prefix='bkb-cooling-', dir=parent)
    manifest = {'version': 1, 'phase': 'prepared', 'files': {}, 'directories': {},
                'old_identity': identity, 'old_launch': previous_launch,
                'config_sha256': digest(read(system.path(CONFIG)))}
    for n, dst in enumerate(sorted(desired)):
        path = system.path(dst)
        entry = {'installed_sha256': digest(desired[dst]), 'existed': os.path.exists(path)}
        if entry['existed']:
            entry.update(metadata(path))
            data = read(path)
            entry['sha256'] = digest(data)
            entry['copy'] = 'original-' + str(n)
            atomic(backup + '/' + entry['copy'], data, 0o600, owner[0], owner[1])
        manifest['files'][dst] = entry
    # Private configuration recovery copy; installer never writes the live config.
    atomic(backup + '/miner.conf.private', read(system.path(CONFIG)), 0o600, owner[0], owner[1])
    for dst in SECURE_DIRS + NEW_DIRS:
        path = system.path(dst)
        manifest['directories'][dst] = metadata(path) if os.path.exists(path) else None
    save_manifest(backup, manifest)
    return backup, manifest


def restore_files(system, backup, manifest):
    # Only fixed application targets. Preserve displaced/new files for recovery.
    if set(manifest.get('files', {})) != TARGETS or set(manifest.get('directories', {})) != set(SECURE_DIRS + NEW_DIRS):
        raise ValueError('Unrecognized recovery manifest')
    originals = {}
    for n, dst in enumerate(sorted(TARGETS)):
        entry = manifest['files'][dst]
        if entry['existed']:
            if entry['copy'] != 'original-' + str(n):
                raise ValueError('Invalid backup member')
            originals[dst] = read(backup + '/' + entry['copy'])
            if digest(originals[dst]) != entry['sha256']:
                raise ValueError('Backup checksum mismatch; no recovery files changed')
    recovery = tempfile.mkdtemp(prefix='displaced-', dir=backup)
    for n, dst in enumerate(sorted(TARGETS)):
        entry = manifest['files'][dst]
        path = system.path(dst)
        if os.path.exists(path):
            os.rename(path, recovery + '/' + str(n))
        if entry['existed']:
            atomic(path, originals[dst], entry['mode'], entry['uid'], entry['gid'])
    for dst, entry in manifest['directories'].items():
        if entry is not None:
            os.chown(system.path(dst), entry['uid'], entry['gid'])
            os.chmod(system.path(dst), entry['mode'])
    # Newly created directories are retained; never recursively remove user data.
    return recovery


def resume_watchdog(system):
    try:
        system.resume_watchdog()
    except BaseException:
        raise RuntimeError('CRITICAL: cron restoration failed. Check the miner and run service cron start manually; retain the printed backup')


def install(system, desired, previous_launch, owner=(0, 0), web_owner=None):
    if web_owner is None:
        account = pwd.getpwnam('www-data')
        web_owner = (account.pw_uid, account.pw_gid)
    identity = system.identity()
    backup, manifest = backup_files(system, desired, identity, previous_launch, owner)
    print('Recovery backup: ' + backup, flush=True)
    paused = False
    stopped = False
    stop_requested = False
    changed = False
    try:
        paused = True
        system.pause_watchdog()
        stop_requested = True
        system.stop(identity)
        stopped = True
        manifest['phase'] = 'installing'
        save_manifest(backup, manifest)
        changed = True
        for dst in SECURE_DIRS + NEW_DIRS:
            path = system.path(dst)
            if not os.path.exists(path):
                os.mkdir(path, 0o755)
            os.chown(path, *(web_owner if dst == '/opt/scripta/etc/cooling' else owner))
            os.chmod(path, 0o700 if dst == '/opt/scripta/etc/cooling' else 0o755)
        for dst, data in desired.items():
            permissions = 0o600 if dst == PREF else (0o755 if dst in (MINER, START, HELPER) else 0o644)
            uid, gid = web_owner if dst == PREF else owner
            atomic(system.path(dst), data, permissions, uid, gid)
        if digest(read(system.path(CONFIG))) != manifest['config_sha256']:
            raise RuntimeError('Mining configuration changed during installation')
        system.start(shlex.split(LAUNCH + ' --baikal-fan 100'))
        system.verify()
        if digest(read(system.path(CONFIG))) != manifest['config_sha256']:
            raise RuntimeError('Mining configuration changed during validation')
        manifest['phase'] = 'validated'
        save_manifest(backup, manifest)
    except BaseException:
        # Do not let another terminal interrupt prevent recovery/watchdog restoration.
        for sig in (signal.SIGINT, signal.SIGTERM, signal.SIGHUP):
            signal.signal(sig, signal.SIG_IGN)
        if stop_requested:
            try:
                running = system.identity()
            except (ValueError, RuntimeError, OSError):
                running = None
            # A failed graceful stop must not lead to an unsafe file replacement.
            if not stopped and running == identity:
                raise
            if running is not None:
                system.stop(running)
            if changed:
                restore_files(system, backup, manifest)
            system.start(previous_launch if '--baikal-fan' in previous_launch else previous_launch + ['--baikal-fan', '100'])
            system.verify_original()
            manifest['phase'] = 'rolled-back'
            save_manifest(backup, manifest)
            print('Previous files restored and original miner launched.', flush=True)
        raise
    finally:
        if paused:
            resume_watchdog(system)
    return backup


def preflight(system, files):
    if platform.machine() != 'armv7l' or 'VERSION_ID="16.04"' not in read(os.path.realpath('/etc/os-release'), 16384).decode('ascii'):
        raise ValueError('Only the inspected ARMv7 Ubuntu 16.04 BK-B environment is supported')
    for dst in TARGETS | set(SECURE_DIRS + NEW_DIRS) | {CONFIG, '/var/backups'}:
        no_symlinks(dst)
    for dst in ('/var/backups', '/usr', '/usr/local', '/usr/local/libexec'):
        if os.path.exists(dst):
            value = metadata(dst)
            if value['uid'] != 0 or value['mode'] & 0o022:
                raise ValueError('Root-controlled backup/helper parent required: ' + dst)
    for dst in (MINER, CONFIG, START, '/var/www/index.php', '/var/www/partials/status.html'):
        read(dst)
    controllers = read('/var/www/ng/controllers.js').decode('utf-8')
    if not re.search(r'''angular\.module\(\s*['"]Scripta\.controllers['"]\s*,''', controllers):
        raise ValueError('Expected the stock Scripta controllers module')
    system.identity()
    devs = system.api('devs').get('DEVS', [])
    if len(devs) != 3 or any(d.get('Name') != 'BKLU' or d.get('Status') != 'Alive' or d.get('Enabled') != 'Y' or type(d.get('ID')) is not int or type(d.get('ASC')) is not int for d in devs) or set(d.get('ID') for d in devs) != {0, 1, 2}:
        raise ValueError('Expected exactly one healthy three-board BK-B controller')
    if any(not isinstance(d.get('Temperature'), (float, int)) or not 0 <= d['Temperature'] < 51 for d in devs):
        raise ValueError('Unsafe/unavailable board temperatures; cool or repair the miner first')
    system.command(['service', 'cron', 'status'])
    if not os.path.exists('/usr/bin/python'):
        raise ValueError('Legacy /usr/bin/python runtime required by the startup helper')
    json.loads(read(CONFIG).decode('utf-8'))
    with tempfile.TemporaryDirectory(prefix='bkb-preflight-') as tmp:
        binary = tmp + '/miner'
        atomic(binary, files[BIN_NAME], 0o755, 0, 0)
        if b'not found' in system.command(['ldd', binary]):
            raise ValueError('Release binary dependencies are missing')
        system.command([binary, '--version'])
        for src in WEB:
            path = tmp + '/' + os.path.basename(src)
            atomic(path, files[src], 0o644, 0, 0)
            if src.endswith('.php'):
                system.command(['php', '-l', path])
            elif src.endswith('.py'):
                compile(files[src], path, 'exec')
                system.command(['/usr/bin/python', '-c', 'compile(open(__import__("sys").argv[1]).read(), "helper", "exec")', path])


def rollback(system, backup):
    backup = os.path.abspath(backup)
    if os.path.dirname(backup) != system.path('/var/backups') or not os.path.basename(backup).startswith('bkb-cooling-'):
        raise ValueError('Rollback requires an installer backup under /var/backups')
    no_symlinks(backup)
    if os.stat(backup).st_uid != os.geteuid() or stat.S_IMODE(os.stat(backup).st_mode) != 0o700:
        raise ValueError('Recovery backup must be root-owned and private')
    manifest = json.loads(read(backup + '/manifest.json').decode('utf-8'))
    if manifest.get('version') != 1 or manifest.get('phase') != 'validated' or set(manifest.get('files', {})) != TARGETS or set(manifest.get('directories', {})) != set(SECURE_DIRS + NEW_DIRS):
        raise ValueError('Not a validated installer recovery backup; recover failed installs manually')
    if manifest['old_launch'] not in (shlex.split(LAUNCH), shlex.split(LAUNCH + ' --baikal-fan 100')):
        raise ValueError('Invalid original launch command')
    for dst, entry in manifest['files'].items():
        no_symlinks(system.path(dst))
        if dst != PREF and digest(read(system.path(dst))) != entry['installed_sha256']:
            raise ValueError('Installed file has changed; manual rollback required: ' + dst)
        if entry['existed']:
            if entry['copy'] != 'original-' + str(sorted(TARGETS).index(dst)) or digest(read(backup + '/' + entry['copy'])) != entry['sha256']:
                raise ValueError('Recovery checksum/member mismatch')
    identity = system.identity()
    paused = False
    try:
        # Once explicit rollback begins, do not allow a terminal interrupt to
        # strand it halfway through restoration. SIGKILL/power loss remain outside
        # this guarantee; the durable manifest/backup is the recovery path.
        for sig in (signal.SIGINT, signal.SIGTERM, signal.SIGHUP):
            signal.signal(sig, signal.SIG_IGN)
        paused = True
        system.pause_watchdog()
        system.stop(identity)
        restore_files(system, backup, manifest)
        launch = manifest['old_launch']
        system.start(launch if '--baikal-fan' in launch else launch + ['--baikal-fan', '100'])
        system.verify_original()
        manifest['phase'] = 'rolled-back'
        save_manifest(backup, manifest)
    finally:
        if paused:
            resume_watchdog(system)
    print('Rollback complete; original miner running at conservative startup duty. Backup retained.')


def already_installed(system, desired, owner=(0, 0), web_owner=None):
    if web_owner is None:
        account = pwd.getpwnam('www-data')
        web_owner = (account.pw_uid, account.pw_gid)
    for dst, data in desired.items():
        path = system.path(dst)
        if not os.path.exists(path) or read(path) != data:
            return False
        uid, gid = web_owner if dst == PREF else owner
        mode = 0o600 if dst == PREF else (0o755 if dst in (MINER, START, HELPER) else 0o644)
        if metadata(path) != {'uid': uid, 'gid': gid, 'mode': mode}:
            return False
    for dst in SECURE_DIRS + NEW_DIRS:
        if not os.path.exists(system.path(dst)):
            return False
        uid, gid = web_owner if dst == '/opt/scripta/etc/cooling' else owner
        if metadata(system.path(dst)) != {'uid': uid, 'gid': gid, 'mode': 0o700 if dst == '/opt/scripta/etc/cooling' else 0o755}:
            return False
    return True


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--version', action='version', version='BK-B unified installer v0.3.2 (v0.3.0 miner + v0.3.2 panel)')
    parser.add_argument('--assets', help='Directory with the pinned miner, panel and SHA256SUMS')
    action = parser.add_mutually_exclusive_group()
    action.add_argument('--check', action='store_true', help='Read-only compatibility checks (also the default)')
    action.add_argument('--install', action='store_true', help='Perform the backed-up installation (default is read-only checks)')
    action.add_argument('--rollback', metavar='BACKUP', help='Restore an unchanged installation from its private backup')
    parser.add_argument('--confirm-bkb', action='store_true', help='Operator confirms the physical model is BK-B')
    parser.add_argument('--allow-restart', action='store_true', help='Approve a mining stop/start and temporary cron pause')
    parser.add_argument('--startup-mode', choices=['preserve', 'auto', 'manual100'], default='preserve',
                        help='Preserve existing preference; first install defaults to Automatic')
    args = parser.parse_args()
    if os.geteuid() != 0:
        parser.error('Run as root so all preflight and backup paths can be verified')
    if not args.confirm_bkb or ((args.install or args.rollback) and not args.allow_restart):
        parser.error('--confirm-bkb is required; install/rollback also require --allow-restart')
    system = System()
    if args.rollback:
        fd = os.open('/run/bkb-cooling-install.lock', os.O_CREAT | os.O_RDWR | os.O_NOFOLLOW, 0o600)
        with os.fdopen(fd, 'a') as lock:
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
            rollback(system, args.rollback)
        return
    if not args.assets:
        parser.error('--assets is required for checks/install')
    files = artifacts(os.path.abspath(args.assets))
    preflight(system, files)
    desired, previous_launch = plan(system, files, args.startup_mode)
    with tempfile.TemporaryDirectory(prefix='bkb-shell-check-') as tmp:
        path = tmp + '/start.sh'
        atomic(path, desired[START], 0o644, 0, 0)
        system.command(['bash', '-n', path])
    print('Checks passed: pinned assets, platform, controller, temperatures, dependencies and integration.')
    print('Startup preference: ' + preference(desired[PREF])['mode'])
    print('Install includes a mining restart and a temporary cron pause; no firmware or pool edits.')
    print('Startup directories become root-controlled; recovery backups preserve their original permissions.')
    if not args.install:
        print('Read-only checks complete. No production files or settings changed.')
        return
    fd = os.open('/run/bkb-cooling-install.lock', os.O_CREAT | os.O_RDWR | os.O_NOFOLLOW, 0o600)
    with os.fdopen(fd, 'a') as lock:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        # Refresh state under the lock, rather than installing a stale preference
        # or plan prepared before another installer completed.
        preflight(system, files)
        desired, previous_launch = plan(system, files, args.startup_mode)
        if already_installed(system, desired):
            print('Already installed with this preference and permissions; no restart needed.')
            return
        def interrupted(signum, frame):
            raise KeyboardInterrupt('Installation interrupted')
        for sig in (signal.SIGINT, signal.SIGTERM, signal.SIGHUP):
            signal.signal(sig, interrupted)
        backup = install(system, desired, previous_launch)
    print('Installed and validated. Open Status and hard-refresh. Backup: ' + backup)


if __name__ == '__main__':
    try:
        main()
    except (Exception, KeyboardInterrupt) as error:
        print('STOP: ' + str(error) + '. Inspect the recovery backup/logs before retrying.', file=sys.stderr)
        sys.exit(1)
