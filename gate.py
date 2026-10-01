import os,sys,pathlib,subprocess,ctypes,json,hashlib,time,select,shutil,re
B=pathlib.Path('/tmp/shaddow-gate'); ROOT=B/'rootfs'; P=B/'parent'; OWNER=45000
def demote():
 os.setgroups([]);os.setresgid(OWNER,OWNER,OWNER);os.setresuid(OWNER,OWNER,OWNER)
def digest(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def snapshot(p):
 s=p.stat();return [digest(p),s.st_uid,s.st_gid,s.st_mode,s.st_size,s.st_mtime_ns,s.st_ctime_ns]
def maps(pid,kind):return [list(map(int,l.split())) for l in pathlib.Path(f'/proc/{pid}/{kind}_map').read_text().splitlines()]
def getstatus(pid):
 return dict(l.split(':',1) for l in pathlib.Path(f'/proc/{pid}/status').read_text().splitlines() if ':' in l)
def waitread(fd):
 assert select.select([fd],[],[],20)[0],'worker timeout';return os.read(fd,8192)
assert os.geteuid()==0
for h in ('newuidmap','newgidmap'):
 p=pathlib.Path(shutil.which(h));assert p.stat().st_mode&0o4000
 subprocess.run([str(p)],stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
if B.exists():shutil.rmtree(B)
ROOT.mkdir(parents=True);P.mkdir();(ROOT/'private').mkdir()
for folder in (B,ROOT,P,ROOT/'private'):os.chown(folder,OWNER,OWNER)
B.chmod(0o755);ROOT.chmod(0o555);P.chmod(0o700);(ROOT/'private').chmod(0o700)
for d in (P,ROOT/'private'):
 for name,content in [('secret',b'SYNTHETIC-PARENT-SECRET-ONLY'),('state',b'SYNTHETIC-IMMUTABLE-STATE')]:
  f=d/name;f.write_bytes(content);os.chown(f,OWNER,OWNER);f.chmod(0o600)
shutil.copyfile('worker',ROOT/'worker');(ROOT/'worker').chmod(0o555)
shutil.copyfile('launcher',B/'launcher');(B/'launcher').chmod(0o555)
protected=[P/'secret',P/'state',ROOT/'private/secret',ROOT/'private/state']
before={str(f):snapshot(f) for f in protected}
baseline={str(p) for p in B.rglob('*')}
runs=[]
for identity in (50000,54321,59999):
 ready_r,ready_w=os.pipe();go_r,go_w=os.pipe();out_r,out_w=os.pipe();in_r,in_w=os.pipe()
 pid=os.fork()
 if pid==0:
  try:
   for fd in (ready_r,go_w,out_r,in_w):os.close(fd)
   demote();libc=ctypes.CDLL(None,use_errno=True)
   if libc.unshare(0x10000000):raise OSError(ctypes.get_errno(),'user namespace')
   os.write(ready_w,b'U');assert os.read(go_r,1)==b'M'
   if libc.unshare(0x40000000|0x00020000):raise OSError(ctypes.get_errno(),'network/mount namespace')
   os.dup2(in_r,0);os.dup2(out_w,1);os.dup2(out_w,2)
   os.execve(str(B/'launcher'),['launcher',str(ROOT),str(identity)],{'PATH':'/usr/bin:/bin'})
  except BaseException as e:
   os.write(out_w,('CHILD_ERROR '+str(e)+'\n').encode());os._exit(72)
 for fd in (ready_w,go_r,out_w,in_r):os.close(fd)
 try:
  assert waitread(ready_r)==b'U','namespace startup'
  pathlib.Path(f'/proc/{pid}/setgroups').write_text('deny')
  for kind in ('uid','gid'):
   subprocess.run([f'new{kind}map',str(pid),'0',str(OWNER),'1','50000','50000','10000'],preexec_fn=demote,check=True)
  um,gm=maps(pid,'uid'),maps(pid,'gid')
  assert um==gm==[[0,OWNER,1],[50000,50000,10000]]
  os.write(go_w,b'M');startup=waitread(out_r);assert startup==b'READY\n',('worker ready',startup)
  st=getstatus(pid);ids=lambda k:list(map(int,st[k].split()))
  live={k:st[k].strip() for k in ('Uid','Gid','Groups','CapEff','CapPrm','CapBnd','CapAmb','NoNewPrivs','Seccomp')}
  assert ids('Uid')==ids('Gid')==[identity]*4
  assert not st['Groups'].strip()
  assert all(int(st[k],16)==0 for k in ('CapEff','CapPrm','CapBnd','CapAmb'))
  assert st['NoNewPrivs'].strip()=='1' and st['Seccomp'].strip()=='2'
  assert os.readlink(f'/proc/{pid}/root')==str(ROOT)
  net_inode=os.readlink(f'/proc/{pid}/ns/net');assert net_inode!=os.readlink('/proc/self/ns/net')
  links=pathlib.Path(f'/proc/{pid}/net/dev').read_text().splitlines()[2:]
  assert len(links)==1 and links[0].strip().startswith('lo:')
  assert not pathlib.Path(f'/proc/{pid}/net/route').read_text().splitlines()[1:]
  fdpaths={x.name:os.readlink(x) for x in pathlib.Path(f'/proc/{pid}/fd').iterdir()}
  assert set(fdpaths)=={'0','1','2'} and all(v.startswith('pipe:[') for v in fdpaths.values())
  tracepath=B/f'trace-{identity}.txt'
  tracer=subprocess.Popen(['strace','-qq','-e','trace=openat,socket,unshare,setuid,ptrace','-o',str(tracepath),'-p',str(pid)],stdout=subprocess.DEVNULL,stderr=subprocess.PIPE)
  deadline=time.monotonic()+10
  while getstatus(pid)['TracerPid'].strip()=='0':
   assert time.monotonic()<deadline,'independent tracer attach timeout'
   time.sleep(0.02)
  os.write(in_w,b'X');data=waitread(out_r);result=json.loads(data)
  _,exitstatus=os.waitpid(pid,0);assert exitstatus==0
  assert tracer.wait(timeout=10)==0
  trace=tracepath.read_text()
  patterns=[r'openat\(.*"/private/secret", O_RDONLY\)\s+= -1 EACCES',r'openat\(.*"/private/state", O_WRONLY\)\s+= -1 EACCES',r'socket\(AF_INET, SOCK_STREAM, IPPROTO_IP\)\s+= -1 EPERM',r'socket\(AF_INET6, SOCK_STREAM, IPPROTO_IP\)\s+= -1 EPERM',r'unshare\(CLONE_NEWNET\)\s+= -1 EPERM',r'setuid\(0\)\s+= -1 EPERM']
  for pattern in patterns:assert re.search(pattern,trace),(pattern,trace)
  tracepath.unlink()
  assert result['uid']==result['gid']==[identity]*3 and result['groups']==0 and result['sum']==sum([6,7,29])
  for key in ('read_errno','write_errno','durable_errno'):assert result[key]==13,(key,result)
  for key in ('host_read_errno','host_write_errno','tmp_errno'):assert result[key]==2,(key,result)
  for key in ('inet_errno','inet6_errno','unix_errno','unshare_errno','setuid_errno','ptrace_errno'):assert result[key]==1,(key,result)
  assert before=={str(f):snapshot(f) for f in protected}
  assert baseline=={str(p) for p in B.rglob('*')}
  assert not pathlib.Path(f'/proc/{pid}').exists()
  runs.append({'identity':identity,'uid_map':um,'gid_map':gm,'live':live,'fdpaths':fdpaths,'network_namespace':net_inode,'worker_result':result,'independent_syscall_trace':trace,'independent_checks_pass':True})
 finally:
  for fd in (ready_r,go_w,out_r,in_w):os.close(fd)
  try:os.kill(pid,9);os.waitpid(pid,0)
  except ProcessLookupError:pass
assert before=={str(f):snapshot(f) for f in protected}
report={'format':'SHADDOW_SYNTHETIC_HOST_GATE_V2','synthetic_only':True,'canonical_material_used':False,'all_checks_pass':True,'parent_euid':os.geteuid(),'source_sha256':{n:digest(pathlib.Path(n)) for n in ('probe.c','launcher.c','gate.py')},'worker_sha256':digest(pathlib.Path('worker')),'runs':runs,'protected_state_unchanged':True,'no_unauthorized_durable_authority':True,'provider':'GitHub standard hosted VM ubuntu-24.04','execution':{k:os.environ[k] for k in ('GITHUB_SHA','GITHUB_RUN_ID','GITHUB_RUN_ATTEMPT') if k in os.environ}}
shutil.rmtree(B);assert not B.exists();report['synthetic_fixture_removed']=True
subprocess.run(['userdel','shaddowprobe'],check=True)
assert all(not line.startswith('shaddowprobe:') for f in ('/etc/subuid','/etc/subgid','/etc/passwd') for line in pathlib.Path(f).read_text().splitlines())
report['parent_test_account_and_subordinate_ranges_removed']=True
print('SHADDOW_GATE_REPORT='+json.dumps(report,sort_keys=True))
