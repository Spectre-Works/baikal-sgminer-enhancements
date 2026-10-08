#!/usr/bin/env python
"""Apply a saved fan-only preference once per miner process. Python2/3 compatible."""
from __future__ import print_function
import fcntl, json, os, socket, subprocess, sys, syslog, time
PREFERENCE='/opt/scripta/etc/cooling/fan-settings.json'
STATE='/run/bkb-cooling-applied.json'
LOCK='/run/bkb-cooling-startup.lock'

def preference(data):
    if not isinstance(data,dict) or data.get('version')!=1 or isinstance(data.get('version'),bool):
        raise ValueError('Invalid preference version')
    duty=data.get('duty')
    if data.get('mode') not in ('auto','manual') or isinstance(duty,bool) or not isinstance(duty,int) or not 10<=duty<=100:
        raise ValueError('Invalid fan preference')
    return {'version':1,'mode':data['mode'],'duty':duty}

def api(command,parameter=None):
    payload={'command':command}
    if parameter is not None:payload['parameter']=parameter
    s=socket.create_connection(('127.0.0.1',4028),1);s.settimeout(1.5)
    try:
        s.sendall(json.dumps(payload).encode('ascii'));data=b'';deadline=time.time()+2
        while True:
            chunk=s.recv(8192)
            if not chunk:break
            data+=chunk
            if len(data)>262144:raise ValueError('API response too large')
            if b'\x00' in chunk:break
            if time.time()>deadline:raise ValueError('API deadline exceeded')
        result=json.loads(data.rstrip(b'\x00').decode('utf-8'))
        if result.get('STATUS',[{}])[0].get('STATUS')!='S':raise ValueError('API rejected request')
        return result
    finally:s.close()

def identity():
    try:
        pids=subprocess.check_output(['pgrep','-x','sgminer']).decode('ascii').split()
        if len(pids)!=1:return None
        pid=int(pids[0])
        if os.path.realpath('/proc/%d/exe'%pid)!='/opt/scripta/bin/sgminer':return None
        with open('/proc/%d/stat'%pid) as f:stat=f.read()
        # Fields after the parenthesized comm begin at field3; starttime=22.
        return '%d:%s'%(pid,stat[stat.rfind(')')+2:].split()[19])
    except (IOError,OSError,subprocess.CalledProcessError):return None

def rows(result,waiting=False):
    values=[row for row in result.get('STATS',[]) if row.get('ID') in ('BKLU0','BKLU1','BKLU2')]
    if len(values)!=3 or len(set(row.get('ID') for row in values))!=3:raise ValueError('Unsupported controller')
    for row in values:
        if row.get('Temperature Valid') is not True or isinstance(row.get('Temperature Age'),bool) or not isinstance(row.get('Temperature Age'),int) or not 0<=row['Temperature Age']<15:
            raise ValueError('Temperature telemetry not ready')
        if row.get('Fan Fault') is not False or (not waiting and (row.get('Fan Acknowledged Valid') is not True or row.get('Fan Pending') is not False)):
            raise ValueError('Cooling not healthy')
    return values

def asc_selection(devs):
    selected=[row for row in devs.get('DEVS',[]) if row.get('Name')=='BKLU']
    if len(selected)!=3 or set(row.get('ID') for row in selected)!=set((0,1,2)):
        raise ValueError('Ambiguous controller')
    first=[row for row in selected if row.get('ID')==0][0]
    asc=first.get('ASC')
    if isinstance(asc,bool) or not isinstance(asc,int) or asc<0:raise ValueError('Invalid ASC')
    if any(row.get('Status')!='Alive' or row.get('Enabled')!='Y' for row in selected):raise ValueError('Boards not ready')
    return asc

def run_once(key,load,read_state,write_state,transport,process_identity,clock=time.time,pause=time.sleep):
    if read_state()==key:return 'already-handled'
    try:saved=load()
    except (ValueError,IOError):saved='invalid'
    if saved is None:
        write_state(key);return 'no-preference'
    try:pref=preference(saved)
    except ValueError:saved='invalid';pref=None
    deadline=clock()+120;asc=None;attempted=False
    while clock()<deadline and process_identity()==key:
        try:
            asc=asc_selection(transport('devs'))
            state=rows(transport('stats'))
            if saved=='invalid':raise ValueError('Invalid saved preference')
            parameter=str(asc)+(','+'fan-auto,on' if pref['mode']=='auto' else ',fan,'+str(pref['duty']))
            attempted=True
            transport('ascset',parameter)
            # A response only queues the request. Never retry a lower duty.
            confirm_until=min(deadline,clock()+20)
            while clock()<confirm_until and process_identity()==key:
                current=rows(transport('stats'),waiting=True)
                if all(r.get('Fan Acknowledged Valid') is True and r.get('Fan Pending') is False and r.get('Fan Mode')==pref['mode'] and (pref['mode']=='auto' or r.get('Fan Acknowledged')==pref['duty']) for r in current):
                    write_state(key);return 'acknowledged'
                pause(1)
            break
        except (ValueError,IOError,socket.error):
            if saved=='invalid' or attempted:break
            pause(2)
    # On uncertainty, try full cooling only. Do not clear a fault or retry
    # the saved lower setting on every scheduled startup invocation.
    fallback=False
    if asc is not None and process_identity()==key:
        fallback=True
        try:transport('ascset',str(asc)+',fan,100')
        except (ValueError,IOError,socket.error):pass
    write_state(key)
    return 'unconfirmed-full-cooling-requested' if fallback else 'unavailable-safe-startup-retained'

def worker():
    lock=open(LOCK,'a+');os.chmod(LOCK,0o600)
    try:fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
    except IOError:lock.close();return
    try:
        key=identity()
        if key is None:return
        def load():
            if not os.path.exists(PREFERENCE):return None
            with open(PREFERENCE) as f:data=f.read(2049)
            if len(data)>2048:raise ValueError('Preference too large')
            return preference(json.loads(data))
        def read_state():
            try:
                with open(STATE) as f:return json.load(f).get('identity')
            except (IOError,ValueError):return None
        def write_state(value):
            # /run is root-owned; only this worker writes this fixed state.
            with open(STATE,'w') as f:json.dump({'identity':value},f)
            os.chmod(STATE,0o600)
        result=run_once(key,load,read_state,write_state,api,identity)
        if result!='already-handled':syslog.syslog(syslog.LOG_NOTICE,'BK-B cooling startup: '+result)
    finally:lock.close()

if __name__=='__main__':
    if os.geteuid()!=0:raise SystemExit('Startup helper must run as root')
    if sys.argv[1:]==['--background']:
        with open(os.devnull,'w') as sink:
            subprocess.Popen([sys.executable,os.path.realpath(__file__),'--worker'],stdin=sink,stdout=sink,stderr=sink,close_fds=True,preexec_fn=os.setsid)
    elif sys.argv[1:]==['--worker']:worker()
    else:raise SystemExit('Use --background or --worker')
