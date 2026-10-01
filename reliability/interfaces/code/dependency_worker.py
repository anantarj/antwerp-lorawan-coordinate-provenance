"""Run pure checks after receiving JSON and disabling file/socket access hooks.
This tests the information boundary of these functions, not OS sandbox security.
"""
import sys,json,io,os,builtins,socket
from claim_contract import validate_dependencies,conventional_reference
payload=json.load(sys.stdin)
# The worker input has only cases with trusted/received records. No oracle verdicts.
if set(payload)!={'cases'}:raise ValueError('Unexpected worker input')
for c in payload['cases']:
    if set(c)!={'case','trusted','received'}:raise ValueError('Unexpected case input')
def forbidden(*args,**kwargs):raise RuntimeError('File/network operation prohibited in pure check')
builtins.open=forbidden;io.open=forbidden;os.open=forbidden
socket.socket=forbidden;socket.create_connection=forbidden
out=[]
for c in payload['cases']:
    a=validate_dependencies(c['trusted'],c['received'])
    b=conventional_reference(c['trusted'],c['received'])
    out.append({'case':c['case'],'integrated':a,'conventional':b,'equal':a==b})
json.dump({'cases':out,'labels_received':False,'file_network_hooks_disabled_during_checks':True},sys.stdout)
