#define _GNU_SOURCE
#include <unistd.h>
#include <stdlib.h>
#include <stdio.h>
#include <sys/prctl.h>
#include <sys/syscall.h>
#include <linux/capability.h>
#include <seccomp.h>
#include <errno.h>
static void must(int v,const char *s){if(v<0){perror(s);exit(70);}}
int main(int argc,char **argv){
 if(argc!=3)return 70;
 int id=atoi(argv[2]);if(id<50000||id>59999)return 70;
 must(chdir(argv[1]),"chdir");must(chroot("."),"chroot");must(chdir("/"),"chdir root");
 must(syscall(SYS_close_range,3,~0U,0),"close_range");
 for(int c=0;c<=CAP_LAST_CAP;c++)must(prctl(PR_CAPBSET_DROP,c,0,0,0),"drop bounding");
 must(setresgid(id,id,id),"gid");must(setresuid(id,id,id),"uid");
 struct __user_cap_header_struct h={_LINUX_CAPABILITY_VERSION_3,0};
 struct __user_cap_data_struct d[2]={{0},{0}};must(syscall(SYS_capset,&h,d),"capset");
 must(prctl(PR_SET_NO_NEW_PRIVS,1,0,0,0),"nnp");
 scmp_filter_ctx f=seccomp_init(SCMP_ACT_ALLOW);if(!f)return 70;
 const char *deny[]={"socket","socketpair","connect","bind","listen","accept","accept4","sendto","sendmsg","sendmmsg","recvmsg","recvmmsg","unshare","setns","mount","umount2","pivot_root","chroot","ptrace","process_vm_readv","process_vm_writev","pidfd_getfd","bpf","userfaultfd","io_uring_setup","io_uring_enter","io_uring_register","open_by_handle_at","name_to_handle_at","keyctl","add_key","request_key","setuid","setgid","setresuid","setresgid","setreuid","setregid","setfsuid","setfsgid","setgroups","capset","prctl","clone","clone3","fork","vfork","execveat"};
 for(unsigned i=0;i<sizeof(deny)/sizeof(*deny);i++){int n=seccomp_syscall_resolve_name(deny[i]);if(n!=__NR_SCMP_ERROR)must(seccomp_rule_add(f,SCMP_ACT_ERRNO(EPERM),n,0),deny[i]);}
 must(seccomp_load(f),"seccomp");seccomp_release(f);
 char *a[]={"/worker",NULL};char *e[]={"PATH=/",NULL};execve(a[0],a,e);perror("exec worker");return 70;
}
