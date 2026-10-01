import pathlib,shutil,subprocess,os,re,json,hashlib
R=pathlib.Path('guest-root'); O=pathlib.Path('portable');R.mkdir();O.mkdir()
def copy(p,root):
 p=pathlib.Path(p);d=root/str(p).lstrip('/');d.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(p.resolve(),d);return d
def deps(p):
 s=subprocess.run(['ldd',str(p)],capture_output=True,text=True).stdout
 return [pathlib.Path(x) for x in re.findall(r'(/[^\s()]+)',s) if pathlib.Path(x).is_file()]
def binary(p):
 copy(p,R)
 for x in deps(p):copy(x,R)
for folder in ('proc','sys','dev','tmp','etc','lab','bin','usr/bin','usr/sbin','run'):(R/folder).mkdir(parents=True,exist_ok=True)
for p in ('/bin/busybox','/bin/bash','/usr/bin/python3.10','/usr/bin/ldd','/usr/bin/newuidmap','/usr/bin/newgidmap','/usr/bin/strace','/usr/sbin/userdel'):binary(p)
shutil.copytree('/usr/lib/python3.10',R/'usr/lib/python3.10',symlinks=True)
for p in (R/'usr/lib/python3.10').rglob('*.so'):
 for x in deps(p):copy(x,R)
for app in ('sh','mount','umount','mkdir','cat','echo','ls','sleep','poweroff','tar','chmod','chown','stty','setsid','cp'):
 (R/'bin'/app).symlink_to('busybox')
(R/'usr/bin/python3').symlink_to('python3.10')
(R/'etc/passwd').write_text('root:x:0:0:root:/root:/bin/sh\nshaddowprobe:x:45000:45000:synthetic:/nonexistent:/bin/sh\n')
(R/'etc/group').write_text('root:x:0:\nshaddowprobe:x:45000:\n')
for n in ('subuid','subgid'):(R/'etc'/n).write_text('shaddowprobe:50000:10000\n')
for n in ('shadow','gshadow'):(R/'etc'/n).write_text('')
for n in ('login.defs','nsswitch.conf'):
 if pathlib.Path('/etc/'+n).exists():copy('/etc/'+n,R)
for n in ('probe.c','launcher.c','gate.py','worker','launcher'):shutil.copy2(n,R/'lab'/n)
for x in deps('launcher'):copy(x,R)
(R/'init').write_text('''#!/bin/sh
mount -t proc proc /proc
mount -t sysfs sysfs /sys
mount -t devtmpfs devtmpfs /dev
mount -t tmpfs tmpfs /tmp
export PATH=/usr/sbin:/usr/bin:/sbin:/bin
cd /lab
python3 gate.py
rc=$?
echo GUEST_GATE_EXIT=$rc
if [ "$rc" = 0 ]; then echo REAL_LINUX_SYNTHETIC_GATE_PASS; fi
echo GUEST_CONSOLE_READY
exec /bin/sh
''');(R/'init').chmod(0o755)
os.chmod(R/'usr/bin/newuidmap',0o4755);os.chmod(R/'usr/bin/newgidmap',0o4755)
subprocess.run('cd guest-root && find . -print0 | cpio --null -o --format=newc | gzip -1 > ../portable/initramfs.gz',shell=True,check=True)
k=sorted(pathlib.Path('/boot').glob('vmlinuz-*-generic'))[-1];shutil.copy2(k,O/'vmlinuz');(O/'vmlinuz').chmod(0o644)
(O/'lib').mkdir();(O/'bin').mkdir()
q=pathlib.Path('/usr/bin/qemu-system-x86_64');shutil.copy2(q,O/'bin/qemu-system-x86_64')
for p in deps(q):shutil.copy2(p.resolve(),O/'lib'/p.name)
(O/'modules').mkdir()
tcg=pathlib.Path('/usr/lib/x86_64-linux-gnu/qemu/accel-tcg-x86_64.so')
assert tcg.is_file()
shutil.copy2(tcg,O/'modules'/tcg.name)
for p in deps(tcg):shutil.copy2(p.resolve(),O/'lib'/p.name)
for p in ('/usr/share/qemu','/usr/share/seabios'):
 if pathlib.Path(p).exists():shutil.copytree(p,O/pathlib.Path(p).name,symlinks=False,ignore_dangling_symlinks=True)
(O/'run').write_text('''#!/bin/sh
set -eu
HERE=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
export QEMU_MODULE_DIR="$HERE/modules"
exec "$HERE/lib/ld-linux-x86-64.so.2" --library-path "$HERE/lib" "$HERE/bin/qemu-system-x86_64" -L "$HERE/qemu" -machine pc -accel tcg -m 768 -smp 2 -nodefaults -no-reboot -nographic -serial mon:stdio -nic none -kernel "$HERE/vmlinuz" -initrd "$HERE/initramfs.gz" -append 'console=ttyS0 rdinit=/init panic=-1' "$@"
''');(O/'run').chmod(0o755)
# Materialize firmware symlinks to avoid dependence on runner directories.
for p in O.rglob('*'):
 if p.is_symlink():
  target=p.resolve();p.unlink();shutil.copy2(target,p)
manifest={str(p.relative_to(O)):hashlib.sha256(p.read_bytes()).hexdigest() for p in O.rglob('*') if p.is_file()}
(O/'SHA256_MANIFEST.json').write_text(json.dumps(manifest,sort_keys=True,indent=2))
