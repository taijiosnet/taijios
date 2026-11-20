"""Keep mk's Tcl/Tk bundles current with the selected package sources."""

import hashlib
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import tomllib

ROOT = Path(__file__).resolve().parents[2]


def fingerprint(checkouts):
    digest = hashlib.sha256()

    def add(path, base):
        digest.update(str(path.relative_to(base)).encode() + b'\0')
        digest.update(hashlib.sha256(path.read_bytes()).digest())

    for name in ('ziran.toml', 'ziran.lock', 'ziran.local.toml'):
        path = ROOT / name
        if path.is_file():
            add(path, ROOT)
    add(Path(__file__).resolve(), ROOT)
    for directory in checkouts:
        checkout = Path(directory)
        manifest = checkout / 'ziran.toml'
        add(manifest, checkout)
        head = subprocess.run(['git', 'rev-parse', '--verify', 'HEAD'], cwd=checkout,
                              stdout=subprocess.PIPE, stderr=subprocess.DEVNULL)
        digest.update(head.stdout)
        package = tomllib.loads(manifest.read_text())['package']
        for source_root in package['module_roots']:
            for source in sorted((checkout / source_root).rglob('*.zi')):
                add(source, checkout)
    return digest.hexdigest()


def main():
    operation, profile, stamp, *_ = sys.argv[1:]
    path = Path(stamp)
    if operation == 'check':
        # mk runs P comparators without the recipe environment. Rehash the
        # resolved package inputs without invoking the package launcher.
        try:
            record = json.loads(path.read_text())
            return int(record['digest'] != fingerprint(record['checkouts']))
        except (OSError, ValueError, KeyError, TypeError):
            return 1
    if operation != 'write':
        raise ValueError(operation)
    packages = {'tcl': ['tcl'], 'tk': ['tcl', 'tk']}[profile]
    resolved = subprocess.check_output(['ziran', 'pkg', 'paths', *packages], cwd=ROOT)
    checkouts = [record['path'] for record in json.loads(resolved)]
    record = {'checkouts': checkouts, 'digest': fingerprint(checkouts)}
    path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(mode='w', dir=path.parent, delete=False) as staged:
        json.dump(record, staged)
        staging_path = Path(staged.name)
    staging_path.replace(path)
    return 0


if __name__ == '__main__':
    sys.exit(main())
