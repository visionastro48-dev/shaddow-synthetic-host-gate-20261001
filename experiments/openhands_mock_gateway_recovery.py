#!/usr/bin/env python3
"""Synthetic OpenHands -> local mock Gateway custody/restart test.
No ANGELS-issued token, canonical worker identity or production authority.
"""
import hashlib, json, os, secrets, subprocess, sys, tempfile, threading
from pathlib import Path
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.error import HTTPError
from urllib.parse import parse_qs, urlsplit
from urllib.request import Request, urlopen

AGENT='synthetic_openhands_01'
PROJECT='synthetic_isolated'
TOPIC='angels.agent.isolated-code.v1'
GOOD=b'#!/usr/bin/env bash\necho OPENHANDS_ANGELS_TASK_OK\n'
EXPECTED=hashlib.sha256(GOOD).hexdigest()

def call(url, token=None, method='GET', payload=None):
    headers={'Content-Type':'application/json'}
    if token is not None: headers['Authorization']='Bearer '+token
    data=None if payload is None else json.dumps(payload).encode()
    try:
        with urlopen(Request(url,data=data,method=method,headers=headers),timeout=6) as res:
            return res.status,json.load(res)
    except HTTPError as err:
        return err.code,json.loads(err.read().decode())

def persist(path,data):
    path.parent.mkdir(parents=True,exist_ok=True)
    tmp=path.with_name(path.name+'.'+secrets.token_hex(8)+'.pending')
    with open(tmp,'x',encoding='utf8') as f:
        json.dump(data,f,sort_keys=True)
        f.flush();os.fsync(f.fileno())
    os.replace(tmp,path)
    fd=os.open(str(path.parent),os.O_RDONLY)
    try:os.fsync(fd)
    finally:os.close(fd)

def worker(base,token,journal,artifact):
    status,_=call(base+'/participants/heartbeat',token,'POST',{'agent_id':AGENT})
    if status!=200:return 11
    status,data=call(base+'/messages?to_agent_id='+AGENT+'&project_id='+PROJECT,token)
    if status!=200:return 12
    for item in data['messages']:
        if item.get('status')=='acknowledged':continue
        if item.get('topic')!=TOPIC or item.get('to_agent_id')!=AGENT or item.get('project_id')!=PROJECT:return 13
        body=item['body'];mid=item['message_id'];mission=body['mission_id']
        if body.get('authority')!='no-production-authority' or body.get('schema')!='angels.agent.isolated-code/v1' or body.get('expected_sha256')!=EXPECTED:return 14
        receipt=journal/(mission+'.json')
        old=json.loads(receipt.read_text()) if receipt.exists() else None
        if old and (old.get('message_id')!=mid or old.get('expected_sha256')!=EXPECTED):return 15
        if old and old['status']=='ACKED':continue
        content=artifact.read_bytes() if artifact.exists() else b''
        actual=hashlib.sha256(content).hexdigest()
        if actual!=EXPECTED or content!=GOOD:
            persist(receipt,{'status':'FAILED_WAITING_RECONCILIATION','message_id':mid,'expected_sha256':EXPECTED,'observed_sha256':actual,'execution_count':(old or {}).get('execution_count',0)})
            return 16
        if old and old['status']=='FAILED_WAITING_RECONCILIATION':return 17
        record=old or {'status':'VERIFIED_WAITING_ACK','message_id':mid,'expected_sha256':EXPECTED,'execution_count':1}
        if not old:persist(receipt,record)
        status,_=call(base+'/messages/'+mid+'/ack',token,'POST',{})
        if status!=200:return 18
        record['status']='ACKED'
        persist(receipt,record)
    return 0

def main():
    output=Path(os.environ.get('ANGELS_SYNTHETIC_OPENHANDS_OUTPUT','/tmp/angels-openhands-disposable/task/hello_angels.sh'))
    assert output.exists() and output.read_bytes()==GOOD,'EXACT_OPENHANDS_OUTPUT_NOT_FOUND'
    scoped_token=secrets.token_hex(32)
    state={'active':'msg_001','messages':{},'heartbeats':0,'denied':0,'ack_attempts':0,'ack_ok':0}
    def message(mid):
        return {'message_id':mid,'to_agent_id':AGENT,'project_id':PROJECT,'topic':TOPIC,
                'status':'acknowledged' if state['messages'].get(mid)=='ACKED' else 'queued',
                'body':{'schema':'angels.agent.isolated-code/v1','authority':'no-production-authority',
                        'mission_id':'mission_'+mid,'task':'Independently verify synthetic artifact','expected_sha256':EXPECTED}}
    class Handler(BaseHTTPRequestHandler):
        def log_message(self,*args):pass
        def reply(self,status,obj):
            b=json.dumps(obj).encode()
            self.send_response(status);self.send_header('Content-Type','application/json')
            self.send_header('Content-Length',str(len(b)));self.end_headers();self.wfile.write(b)
        def authorized(self):
            if self.headers.get('Authorization')!='Bearer '+scoped_token:
                state['denied']+=1;self.reply(401,{'error':'unauthorized'});return False
            return True
        def do_GET(self):
            if not self.authorized():return
            u=urlsplit(self.path)
            if u.path!='/messages':self.reply(404,{'error':'not_found'});return
            q=parse_qs(u.query)
            if q.get('to_agent_id')!=[AGENT] or q.get('project_id')!=[PROJECT]:self.reply(403,{'error':'scope_denied'});return
            self.reply(200,{'messages':[message(state['active'])]})
        def do_POST(self):
            if not self.authorized():return
            n=int(self.headers.get('Content-Length','0'))
            data=json.loads(self.rfile.read(n) or b'{}')
            if self.path=='/participants/heartbeat':
                if data.get('agent_id')!=AGENT:self.reply(403,{'error':'scope_denied'});return
                state['heartbeats']+=1;self.reply(200,{'ok':True});return
            if self.path=='/messages/'+state['active']+'/ack':
                state['ack_attempts']+=1
                if state['active']=='msg_001' and state['ack_attempts']==1:
                    self.reply(503,{'error':'transient_failure'});return
                if state['messages'].get(state['active'])=='ACKED':
                    self.reply(409,{'error':'duplicate_ack'});return
                state['messages'][state['active']]='ACKED';state['ack_ok']+=1;self.reply(200,{'ok':True});return
            self.reply(404,{'error':'not_found'})
    server=ThreadingHTTPServer(('127.0.0.1',0),Handler)
    threading.Thread(target=server.serve_forever,daemon=True).start()
    base='http://127.0.0.1:'+str(server.server_port)
    try:
        with tempfile.TemporaryDirectory(prefix='angels-synthetic-acceptance-') as td:
            journal=Path(td)/'journal'
            argv=[sys.executable,__file__,'--worker',base,scoped_token,str(journal),str(output)]
            assert call(base+'/messages')[0]==401,'MISSING_TOKEN_ALLOWED'
            assert call(base+'/messages','wrong-token')[0]==401,'INVALID_TOKEN_ALLOWED'
            assert call(base+'/messages?to_agent_id=other&project_id='+PROJECT,scoped_token)[0]==403,'CROSS_AGENT_ACCESS_ALLOWED'
            assert subprocess.run(argv,capture_output=True,timeout=15).returncode==18,'INTERRUPTED_ACK_NOT_WITNESSED'
            proof=json.loads((journal/'mission_msg_001.json').read_text())
            assert proof['status']=='VERIFIED_WAITING_ACK' and proof['execution_count']==1
            assert subprocess.run(argv,capture_output=True,timeout=15).returncode==0,'FIRST_RESTART_FAILED'
            assert subprocess.run(argv,capture_output=True,timeout=15).returncode==0,'SECOND_RESTART_FAILED'
            proof=json.loads((journal/'mission_msg_001.json').read_text())
            assert proof['status']=='ACKED' and proof['execution_count']==1
            assert state['ack_attempts']==2 and state['ack_ok']==1,'DUPLICATE_ACK_OR_LOST_RECEIPT'
            state['active']='msg_002'
            bad=Path(td)/'tampered.sh';bad.write_bytes(GOOD+b'#tamper\n')
            assert subprocess.run(argv[:-1]+[str(bad)],capture_output=True,timeout=15).returncode==16,'TAMPERED_OUTPUT_ACCEPTED'
            assert state['ack_ok']==1,'TAMPERED_OUTPUT_ACKED'
            assert json.loads((journal/'mission_msg_002.json').read_text())['status']=='FAILED_WAITING_RECONCILIATION'
            print('LOCAL_MOCK_GATEWAY_SCOPED_AUTH=PASS')
            print('ORIGINAL_OPENHANDS_ARTIFACT_SHA256='+EXPECTED)
            print('LOCAL_MOCK_GATEWAY_ACK_RESTARTS=2')
            print('LOCAL_MOCK_GATEWAY_SUCCESSFUL_ACKS=1')
            print('LOCAL_MOCK_GATEWAY_REPLAYED_EXECUTIONS=0')
            print('LOCAL_MOCK_GATEWAY_TAMPER_DENIAL=PASS')
            print('ORIGINAL_ANGELS_ISSUED_IDENTITY=NOT_VERIFIED')
    finally:server.shutdown();server.server_close()

if __name__=='__main__':
    if len(sys.argv)>1 and sys.argv[1]=='--worker':
        sys.exit(worker(sys.argv[2],sys.argv[3],Path(sys.argv[4]),Path(sys.argv[5])))
    main()
