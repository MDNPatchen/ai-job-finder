"""Synthetic acceptance benchmark. Not a measure of real-world ranking accuracy."""
import json,sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from qualification_matcher import compile_resume_profile
cases=json.loads(Path(__file__).resolve().parents[1].joinpath('evaluation/resume_evidence_cases.json').read_text())
false_positive=[];false_negative=[]
for case in cases:
    actual=case['area'] in compile_resume_profile(case['text'],())['evidence']
    if actual and not case['supported']:false_positive.append(case['id'])
    if not actual and case['supported']:false_negative.append(case['id'])
print(json.dumps({'kind':'synthetic acceptance cases; not independently human validated',
    'cases':len(cases),'false_positives':false_positive,'false_negatives':false_negative},indent=2))
sys.exit(bool(false_positive or false_negative))
