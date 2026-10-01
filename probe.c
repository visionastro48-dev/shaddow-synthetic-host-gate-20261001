#define _GNU_SOURCE
#include <unistd.h>
#include <stdio.h>
#include <stdlib.h>
#include <errno.h>
#include <fcntl.h>
#include <sys/socket.h>
#include <sys/syscall.h>
#include <sched.h>
static int op(const char *p,int flags){errno=0;int f=open(p,flags,0600);int r=f<0?errno:0;if(f>=0)close(f);return r;}
static int sock(int family){errno=0;int f=socket(family,SOCK_STREAM,0);int r=f<0?errno:0;if(f>=0)close(f);return r;}
int main(void){
 puts("READY");fflush(stdout);char c;if(read(0,&c,1)!=1)return 71;
 uid_t a,b,d;gid_t x,y,z;getresuid(&a,&b,&d);getresgid(&x,&y,&z);
 int groups=getgroups(0,NULL),v4=sock(AF_INET),v6=sock(AF_INET6),local=sock(AF_UNIX);
 errno=0;int u=unshare(CLONE_NEWNET);int ue=u<0?errno:0;
 errno=0;int s=setuid(0);int se=s<0?errno:0;
 errno=0;int ptr=syscall(SYS_ptrace,16,1,0,0);int pe=ptr<0?errno:0;
 int r=op("/private/secret",O_RDONLY),w=op("/private/state",O_WRONLY),h=op("/tmp/shaddow-gate/parent/secret",O_RDONLY),hw=op("/tmp/shaddow-gate/parent/state",O_WRONLY);
 int persist=op("/escape",O_WRONLY|O_CREAT),tmp=op("/tmp/escape",O_WRONLY|O_CREAT);
 printf("{\"uid\":[%u,%u,%u],\"gid\":[%u,%u,%u],\"groups\":%d,\"read_errno\":%d,\"write_errno\":%d,\"host_read_errno\":%d,\"host_write_errno\":%d,\"inet_errno\":%d,\"inet6_errno\":%d,\"unix_errno\":%d,\"unshare_errno\":%d,\"setuid_errno\":%d,\"ptrace_errno\":%d,\"durable_errno\":%d,\"tmp_errno\":%d,\"sum\":42}\n",a,b,d,x,y,z,groups,r,w,h,hw,v4,v6,local,ue,se,pe,persist,tmp);return 0;
}
