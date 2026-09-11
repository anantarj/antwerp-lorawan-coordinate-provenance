#!/usr/bin/env python3
"""Check exact delivered files and anonymous PDF metadata; no estimator or bootstrap run."""
from pathlib import Path
import argparse,json,hashlib
import fitz
ROOT=Path(__file__).resolve().parents[1]
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def check_entry(entry):
 p=(ROOT/entry['path']).resolve()
 if not p.is_relative_to(ROOT):raise ValueError('Manifest path escapes package')
 return p.is_file() and p.stat().st_size==entry['size'] and sha(p)==entry['sha256']
def main():
 a=argparse.ArgumentParser();a.add_argument('--out',type=Path,required=True);a=a.parse_args();out=a.out.resolve()
 if out.exists() or out.is_relative_to(ROOT):raise ValueError('Output must be new and outside package')
 checks=[]
 def ck(name,value,detail=None):
  checks.append({'name':name,'pass':bool(value),'detail':detail})
  if not value:raise AssertionError(name+': '+str(detail))
 for name in ['MANIFEST.json','EVIDENCE_MANIFEST.json']:
  rows=json.loads((ROOT/name).read_text())['files'];bad=[x['path'] for x in rows if not check_entry(x)]
  ck(name+'_all_entries',not bad,{'files':len(rows),'mismatches':bad})
 binding=json.loads((ROOT/'REVIEW_BINDING.json').read_text())
 ck('evidence_manifest_binding',sha(ROOT/'EVIDENCE_MANIFEST.json')==binding['evidence_manifest_sha256'])
 for entry in binding['documents']:
  ck(entry['path']+'_identity',check_entry(entry))
  with fitz.open(ROOT/entry['path']) as doc:
   ck(entry['path']+'_author_metadata_empty',not doc.metadata.get('author'))
   ck(entry['path']+'_no_embedded_attachments',doc.embfile_count()==0)
 ai=(ROOT/'AI_DECLARATION.txt').read_text().strip()
 text=(ROOT/'manuscript/Manuscript_without_author_details.md').read_text()
 ck('exact_AI_declaration_once_and_before_references',text.count(ai)==1 and text.index(ai)<text.index('# References'))
 ck('funding_exact','No funding was received for this work.' in text and 'no external funding' not in text.lower())
 out.mkdir(parents=True)
 (out/'CHECKS.json').write_text(json.dumps({'all_pass':True,'checks':checks,'scope':'Delivery and declaration checks only. No new coordinate fitting, localization or resampling.'},indent=2)+'\n')
 print('PASS',len(checks),'submission checks')
if __name__=='__main__':main()
