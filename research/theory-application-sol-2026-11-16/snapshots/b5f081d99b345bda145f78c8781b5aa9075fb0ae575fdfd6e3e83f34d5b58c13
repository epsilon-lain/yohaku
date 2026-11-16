"""Check both submission lines, save every intermediate state, run official CLI."""
import argparse,json,os,subprocess,sys
from pathlib import Path
from refine import HERE,configure,source_arguments,dump

def main():
    p=argparse.ArgumentParser(description=__doc__);source_arguments(p)
    p.add_argument('--submission',type=Path,default=HERE/'submission.txt')
    p.add_argument('--output',type=Path,default=HERE/'witness_verification.json')
    p.add_argument('--cli-output',type=Path,default=HERE/'official_cli_receipt.json')
    args=p.parse_args();provenance=configure(args.official_root,args.baseline_root)
    from verifier import core,stable_core
    manifest_path=args.official_root/'competition/tools/verifier/data/manifest.json'
    manifest=json.loads(manifest_path.read_text());byid={c['challenge_id']:c for c in manifest['challenges']}
    results=[]
    for line in args.submission.read_text().splitlines():
        if not line.strip():continue
        cid,raw=line.split(':',1);moves=json.loads(raw);c=byid[cid]
        module=core if c['move_spec_version']=='ac-r2-v1' else stable_core
        verdict=module.verify(c,moves,c['move_spec_version'],manifest['limits']);assert verdict['ok']
        state=tuple(map(tuple,c['initial_relators']));states=[state]
        for move in moves:
            if module is core:state=module.apply_move(state,move)
            else:
                state,error=module.apply_move(state,move);assert error is None
            states.append(state)
        lens=[sum(map(len,s)) for s in states]
        cumulative=[];work=0
        for total in lens:work+=total;cumulative.append(work)
        assert max(lens)==verdict['peak_total_relator_length'] and work==verdict['work']
        results.append({'challenge_id':cid,'instance_hash':c['instance_hash'],'move_spec_version':c['move_spec_version'],'moves':moves,'expanded_move_count':len(moves),'official_verification':verdict,'states':states,'intermediate_total_lengths':lens,'cumulative_work':cumulative})
    env=dict(os.environ,PYTHONPATH=str(args.official_root/'competition/tools'))
    command=[sys.executable,'-m','verifier','--manifest',str(manifest_path),'--submission',str(args.submission),'--pretty']
    cli=subprocess.run(command,env=env,capture_output=True,text=True,check=True)
    receipt=json.loads(cli.stdout);assert receipt['accepted'] and all(r['ok'] for r in receipt['results'])
    args.cli_output.write_text(cli.stdout)
    dump(args.output,{'version':'application-witness-verification-v1','provenance':provenance,'results':results,'official_cli_accepted':receipt['accepted'],'scope':'Local pinned official verification only; no platform upload. Ordinary AC exact-distance claim is separate; Stable AC path is an upper bound.'})
    print(json.dumps({'accepted':receipt['accepted'],'results':[{k:r[k] for k in ['challenge_id','expanded_move_count','official_verification']} for r in results]}))
if __name__=='__main__':main()
