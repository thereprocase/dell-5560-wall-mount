"""Restore the included CFD evidence without replacing existing local results."""
from pathlib import Path
import zipfile
from io import BytesIO
ROOT=Path(__file__).resolve().parent/'cfd'
archives=sorted(ROOT.glob('*/raw_evidence.zip'))+sorted(ROOT.glob('*/raw_evidence.zip.001'))
for archive in archives:
    source=archive
    if archive.suffix=='.001':
        pieces=sorted(archive.parent.glob('raw_evidence.zip.[0-9]*'))
        source=BytesIO(b''.join(p.read_bytes() for p in pieces))
    with zipfile.ZipFile(source) as z:
        assert z.testzip() is None, archive
        for member in z.infolist():
            target=(archive.parent/member.filename).resolve()
            if not target.is_relative_to(archive.parent.resolve()):
                raise ValueError(f'Unsafe archive path: {member.filename}')
            if member.is_dir():
                target.mkdir(parents=True,exist_ok=True)
                continue
            data=z.read(member)
            if target.exists():
                if target.read_bytes()!=data:
                    raise FileExistsError(f'Refusing to replace differing evidence: {target}')
                continue
            target.parent.mkdir(parents=True,exist_ok=True)
            target.write_bytes(data)
    print(f'Restored {archive.parent.name}')
