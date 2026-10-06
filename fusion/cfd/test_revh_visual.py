"""Publication boundaries: preserve the prefix and exclude unfinished times."""
import hashlib
import json
from pathlib import Path
import tempfile
import unittest
from snapshot_revh_visual import snapshot


class SnapshotTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup)
        root=Path(self.temp.name);self.case=root/'case';self.page=root/'page'
        self.write(self.case/'run-status.json',dict(state='running',latest_physical_time_s=.12))
        self.write(self.case/'case_manifest.json',{})
        self.write(self.case/'quality-disposition.json',{})
        prefix=self.sample(self.case/'presentation',.1)
        self.write(self.page/'hour-18/progress.json',dict(last_time_s=.1,physical_times_s=[.1],source_sha256={'.1':None,'0.1':hashlib.sha256(prefix.read_bytes()).hexdigest()}))
        self.write(self.page/'checkpoint-03/progress.json',dict(visual_extension=dict(base_last_time_s=.1,video_frame_step_s=.01,new_frames=0)))

    def write(self,path,data):
        path.parent.mkdir(parents=True,exist_ok=True);path.write_text(json.dumps(data))

    def sample(self,case,t):
        path=case/'postProcessing/edge_sections'/str(t);path.mkdir(parents=True,exist_ok=True)
        for name in ['left_section','right_section']:(path/(name+'.vtp')).write_text(f'<VTKFile>{t}</VTKFile>')
        return path/'right_section.vtp'

    def test_snapshot_excludes_future_sample(self):
        for t in [.11,.12,.13]:self.sample(self.case,t)
        result=snapshot(self.case,self.page)
        self.assertEqual(result['complete_sample_frames'],3)
        self.assertEqual(result['visual_extension']['new_frames'],2)
        self.assertFalse((self.case/'presentation/postProcessing/edge_sections/0.13').exists())

    def test_missing_frame_rejected(self):
        self.sample(self.case,.12)
        with self.assertRaisesRegex(AssertionError,'Missing or mistimed'):snapshot(self.case,self.page)

    def test_modified_prefix_rejected(self):
        self.sample(self.case,.11)
        (self.case/'presentation/postProcessing/edge_sections/0.1/right_section.vtp').write_text('changed')
        with self.assertRaises(AssertionError):snapshot(self.case,self.page)


if __name__=='__main__':unittest.main()
