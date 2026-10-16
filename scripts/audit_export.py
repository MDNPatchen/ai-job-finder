"""Usage: python scripts/audit_export.py /path/to/export.csv"""
import sys,json
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from export_audit import audit_csv
if __name__=='__main__':
    if len(sys.argv)!=2: raise SystemExit('Provide one CSV path')
    result=audit_csv(sys.argv[1])
    print(json.dumps(result,indent=2))
    raise SystemExit(0 if result['passed'] else 1)
