#!/usr/bin/python3
"""Fixed Chromium-only network sandbox; not a general connected tool launcher."""
import json,os,stat,sys
from pathlib import Path
from yohaku_browser_runtime import binding,load
import yohaku_tools as tools

def main():
 path=Path(os.environ['YOHAKU_BROWSER_RUNTIME_CONFIG']);st=path.lstat()
 if not stat.S_ISREG(st.st_mode) or st.st_uid!=os.getuid() or st.st_mode&0o077:raise ValueError('Private browser config required')
 config=load(path);ready,_,endpoint=binding(config['world'])
 if ready['host']['pid']!=config['candidate_pid'] or ready['host']['start']!=config['candidate_start'] or str(endpoint)!=config['candidate_socket']:raise ValueError('Browser owner changed; restore browser under the current candidate')
 scratch=Path(config['scratch']);entry={'id':'browser','name':'Chromium private network sandbox','program':'/usr/bin/true','args':[],'wayland':True}
 tools.check(scratch) # Verify the unchanged offline base before this explicit browser exception.
 argv=tools.command(scratch,entry,str(endpoint));cut=argv.index('--');prefix=argv[:cut]
 # Host network only for this browser. No host home, credentials, world documents
 # or general host filesystem is mounted. This bwrap lacks --preserve-fds;
 # carry Playwright pipes over stdio, restore fd 3/4 in a fixed inner shim.
 prefix+=['--share-net','--ro-bind',config['browser_bundle'],'/opt/browser']
 for p in ('/etc/resolv.conf','/etc/hosts','/etc/nsswitch.conf','/etc/ssl/certs','/etc/ca-certificates'):
  if Path(p).exists():prefix+=['--ro-bind',p,p]
 for key in ('profile','spool'):
  source=Path(config[key]);current=Path(source.anchor)
  for part in source.parts[1:-1]:current/=part;prefix+=['--dir',str(current)]
  prefix+=['--bind',str(source),str(source)]
 if config.get('library_dir'):prefix+=['--ro-bind',config['library_dir'],'/opt/browser-libs','--setenv','LD_LIBRARY_PATH','/opt/browser-libs']
 prefix+=['--setenv','NO_AT_BRIDGE','1','--setenv','GTK_USE_PORTAL','0']
 executable='/opt/browser/'+Path(config['chromium_executable']).name
 read_pipe=os.dup(3);write_pipe=os.dup(4);os.dup2(read_pipe,0);os.dup2(write_pipe,1);os.close(read_pipe);os.close(write_pipe)
 bridge='import os,sys;os.dup2(0,3);os.dup2(1,4);os.execv(sys.argv[1],sys.argv[1:])'
 os.execv(prefix[0],[*prefix,'--','/usr/bin/python3','-c',bridge,executable,*sys.argv[1:]])
if __name__=='__main__':main()
