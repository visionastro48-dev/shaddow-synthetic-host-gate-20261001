import subprocess,select,time,os,sys
p=subprocess.Popen(['portable/run'],stdin=subprocess.PIPE,stdout=subprocess.PIPE,stderr=subprocess.STDOUT)
buf=b'';deadline=time.monotonic()+180
try:
 while b'GUEST_CONSOLE_READY' not in buf:
  assert time.monotonic()<deadline,'boot timeout'
  if select.select([p.stdout],[],[],1)[0]:
   s=os.read(p.stdout.fileno(),65536);assert s,'guest terminated';buf+=s;sys.stdout.buffer.write(s);sys.stdout.buffer.flush()
 assert b'REAL_LINUX_SYNTHETIC_GATE_PASS' in buf,'full synthetic gate failed'
 p.stdin.write(b'poweroff -f\n');p.stdin.flush()
 p.wait(timeout=15)
finally:
 if p.poll() is None:p.kill();p.wait()
