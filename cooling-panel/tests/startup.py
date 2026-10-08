import importlib.util, json, unittest
from pathlib import Path
spec=importlib.util.spec_from_file_location('startup',Path(__file__).resolve().parent.parent/'package/startup/bkb-cooling-startup.py')
m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
class StartupTests(unittest.TestCase):
    def execute(self,kind='auto',fail=False,pending=False,invalid=False):
        clock=[0];writes=[];record=[];sent=[False];ticks=[0]
        def transport(command,parameter=None):
            if command=='devs':return {'DEVS':[{'Name':'BKLU','ID':i,'ASC':i,'Status':'Alive','Enabled':'Y'} for i in range(3)]}
            if command=='ascset':
                writes.append(parameter);sent[0]=True
                if fail:raise ValueError('Lost reply')
                return {}
            ticks[0]+=1
            return {'STATS':[{'ID':'BKLU'+str(i),'Temperature Valid':True,'Temperature Age':0,
                'Fan Fault':False,'Fan Acknowledged Valid':True,'Fan Pending':pending and sent[0] and ticks[0]<4,
                'Fan Mode':kind if sent[0] else 'manual','Fan Acknowledged':25} for i in range(3)]}
        def pause(seconds):clock[0]+=seconds
        result=m.run_once('1:2',lambda: {'version':1,'mode':kind,'duty':25} if not invalid else {'bad':True},lambda:None,record.append,transport,lambda:'1:2',lambda:clock[0],pause)
        return result,writes,record
    def test_auto_and_manual(self):
        for mode,param in [('auto','0,fan-auto,on'),('manual','0,fan,25')]:
            result,writes,record=self.execute(mode);self.assertEqual(result,'acknowledged');self.assertEqual(writes,[param]);self.assertEqual(record,['1:2'])
    def test_pending_does_not_retry_write(self):
        result,writes,_=self.execute(pending=True);self.assertEqual(result,'acknowledged');self.assertEqual(writes,['0,fan-auto,on'])
    def test_lost_reply_only_full_cooling(self):
        result,writes,_=self.execute(kind='manual',fail=True);self.assertEqual(writes,['0,fan,25','0,fan,100']);self.assertEqual(result,'unconfirmed-full-cooling-requested')
    def test_invalid_preference_no_lowering(self):
        result,writes,_=self.execute(invalid=True);self.assertEqual(writes,['0,fan,100'])
    def test_same_process_no_reapply(self):
        result=m.run_once('1:2',lambda: self.fail(),lambda:'1:2',lambda x:self.fail(),lambda *a:self.fail(),lambda:'1:2');self.assertEqual(result,'already-handled')
    def test_missing_preference_no_command(self):
        record=[];result=m.run_once('1:2',lambda:None,lambda:None,record.append,lambda *a:self.fail(),lambda:'1:2');self.assertEqual(result,'no-preference')
    def test_types_and_ranges(self):
        for duty in [0,9,101,25.5,'25',True,None]:
            with self.assertRaises(ValueError):m.preference({'version':1,'mode':'manual','duty':duty})
    def test_stale_rows_rejected(self):
        with self.assertRaises(ValueError):m.rows({'STATS':[{'ID':'BKLU'+str(i),'Temperature Valid':True,'Temperature Age':15} for i in range(3)]})
unittest.main()
