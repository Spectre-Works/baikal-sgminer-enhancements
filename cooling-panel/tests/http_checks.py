from __future__ import print_function
import json, os, socket, subprocess, tempfile, time, shutil
try:from urllib.request import build_opener, HTTPCookieProcessor, Request
except ImportError:from urllib2 import build_opener, HTTPCookieProcessor, Request
try:from http.cookiejar import CookieJar
except ImportError:from cookielib import CookieJar
ROOT=os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sessions=tempfile.mkdtemp(prefix='cooling-http-sessions-')
s=socket.socket();s.bind(('127.0.0.1',0));port=s.getsockname()[1];s.close()
base='http://127.0.0.1:'+str(port)
sink=open(os.devnull,'w')
server=subprocess.Popen(['php','-d','session.save_path='+sessions,'-S','127.0.0.1:'+str(port),'-t',ROOT+'/package/web',ROOT+'/tests/router.php'],stdout=sink,stderr=sink)
client=build_opener(HTTPCookieProcessor(CookieJar()))
def call(path='/f_fan.php',data=None,token=None,method=None):
    req=Request(base+path,data=data)
    if token is not None:req.add_header('X-Cooling-CSRF',token)
    if data is not None:req.add_header('Content-Type','application/json')
    if method:req.get_method=lambda:method
    try:
        response=client.open(req,timeout=7);return response.getcode(),response.read()
    except Exception as exc:
        if hasattr(exc,'code'):return exc.code,exc.read()
        raise
try:
    for i in range(20):
        try:code,body=call();break
        except Exception:time.sleep(.1)
    assert code==401
    call('/test-login')
    code,body=call();assert code==200,(code,body)
    status=json.loads(body.decode('utf-8'));token=status['csrf'];assert status['fan']['supported']
    # All authenticated writes below are invalid and must never reach ascset.
    assert call(data=b'{"action":"full"}')[0]==403
    assert call(data=b'{"action":"full"}',token='wrong')[0]==403
    assert call(data=b'{"action":"clock"}',token=token)[0]==400
    assert call(data=b'{"action":"manual","duty":25.5}',token=token)[0]==400
    assert call(data=b'{"action":"save","mode":"manual","duty":0}',token=token)[0]==400
    assert call(data=b'invalid',token=token)[0]==400
    assert call(data=b'x'*2049,token=token)[0]==413
    assert call(data=b'{}',token=token,method='PUT')[0]==405
    code,body=call('/f_fan.php?action=full');assert code==200
    assert json.loads(body.decode('utf-8'))['fan']['mode']==status['fan']['mode']
    print('Isolated HTTP auth, CSRF, invalid mutations, method and size tests passed; no fan writes issued')
finally:
    server.terminate();server.wait();sink.close();shutil.rmtree(sessions)
