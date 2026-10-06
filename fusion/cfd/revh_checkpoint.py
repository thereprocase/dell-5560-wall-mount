"""Verify native transient checkpoints, including backward-scheme history."""
from datetime import datetime, timezone
import hashlib
import gzip
from pathlib import Path
import re

NATIVE_FIELDS=['U','U_0','p','phi','phi_0','k','k_0','omega','omega_0','nut']


def sha(path):
    result=hashlib.sha256()
    with path.open('rb') as stream:
        for chunk in iter(lambda:stream.read(1024*1024),b''):result.update(chunk)
    return result.hexdigest()


def field_path(folder,name):
    plain=folder/name;compressed=folder/(name+'.gz')
    assert not (plain.exists() and compressed.exists()),'Ambiguous compressed and plain field: '+name
    path=plain if plain.exists() else compressed
    assert path.is_file(),f'Missing checkpoint field {path}'
    return path


def uncompressed_sha(path):
    result=hashlib.sha256()
    opener=gzip.open if path.suffix=='.gz' else open
    with opener(path,'rb') as stream:
        for chunk in iter(lambda:stream.read(1024*1024),b''):result.update(chunk)
    return result.hexdigest()


def describe(case,ranks):
    case=Path(case).resolve();times=[]
    for rank in range(ranks):
        candidates=[]
        for folder in (case/f'processor{rank}').iterdir():
            if folder.is_dir():
                try:candidates.append((float(folder.name),folder.name))
                except ValueError:pass
        assert candidates,'No saved processor time'
        times.append(max(candidates)[1])
    assert len(set(times))==1,'Processor checkpoint times differ'
    saved=times[0];hashes={};time_hashes=[];metadata=None
    for rank in range(ranks):
        folder=case/f'processor{rank}'/saved
        for name in NATIVE_FIELDS+['uniform/time']:
            source=field_path(folder,name)
            assert source.is_file() and source.stat().st_size>16,f'Missing checkpoint field {source}'
            hashes[source.relative_to(case).as_posix()]=uncompressed_sha(source)
        time_file=field_path(folder,'uniform/time')
        time_hashes.append(uncompressed_sha(time_file))
        if metadata is None:
            raw=(gzip.open(time_file,'rt').read() if time_file.suffix=='.gz' else time_file.read_text())
            metadata={key:re.search(r'^'+key+r'\s+([^;]+);',raw,re.M)[1].strip()
                      for key in ['value','name','index','deltaT','deltaT0']}
            assert abs(float(metadata['value'])-float(saved))<1e-9*max(float(saved),1e-6)
    assert len(set(time_hashes))==1,'Native time metadata differs between ranks'
    mesh={name:sha(case/'constant/polyMesh'/name)
          for name in ['points','faces','owner','neighbour','boundary','cellZones']}
    return {'verified_utc':datetime.now(timezone.utc).isoformat(),'case':case.name,
            'mpi_ranks':ranks,'time_folder':saved,'physical_time_s':float(saved),
            'native_time_metadata':metadata,'native_previous_step_fields_preserved':True,
            'field_sha256':hashes,'mesh_sha256':mesh,
            'field_hash_basis':'SHA-256 of exact uncompressed bytes; compressed streams are read fully and their gzip integrity is checked.',
            'restart_method':'Use the same mesh and processor count, startFrom latestTime, preserve uniform/time and all old-step fields. Never reset the physical clock.'}
