<?php
require __DIR__.'/../package/web/inc/fan.inc.php';
function expect($ok,$message) {if(!$ok)throw new RuntimeException($message);}
function rejects($callback) {try {$callback();}catch(Exception $e){return;}throw new RuntimeException('Expected rejection');}
function fixture() {
    $devs=array();$stats=array();
    for($i=0;$i<3;$i++) {
        $devs[]=array('ASC'=>$i,'ID'=>$i,'Name'=>'BKLU','Temperature'=>40,'Status'=>'Alive','Enabled'=>'Y');
        $stats[]=array('ID'=>'BKLU'.$i,'Fan Mode'=>'auto','Fan Requested'=>25,'Fan Acknowledged'=>25,
            'Fan Acknowledged Valid'=>true,'Fan Pending'=>false,'Fan Fault'=>false,'Fan Telemetry Failsafe'=>false,
            'Fan Hottest'=>40,'Temperature Age'=>0,'Temperature Valid'=>true);
    }
    return array('devs'=>array('DEVS'=>$devs),'stats'=>array('STATS'=>$stats));
}
$state=fixture();$writes=array();
$service=new CoolingService(function($command,$parameter) use (&$state,&$writes) {
    if($command==='ascset') {$writes[]=$parameter;return array('STATUS'=>array(array('STATUS'=>'S')));}
    return $state[$command];
});
expect($service->status()['acknowledged']===25,'Acknowledged duty');
$service->apply(array('action'=>'manual','duty'=>40));
$service->apply(array('action'=>'auto'));
$service->apply(array('action'=>'full'));
expect($writes===array('0,fan,40','0,fan-auto,on','0,fan,100'),'Only fan commands');
foreach(array(0,9,101,25.5,'25','25,clock,490',true,null) as $value)
    rejects(function() use ($service,$value){$service->apply(array('action'=>'manual','duty'=>$value));});
rejects(function() use($service){$service->apply(array('action'=>'clock'));});
$state=fixture();foreach($state['stats']['STATS'] as &$r)$r['Fan Acknowledged Valid']=false;unset($r);
expect($service->status()['acknowledged']===null,'Unknown is not zero');
rejects(function() use($service){$service->apply(array('action'=>'manual','duty'=>25));});
$state=fixture();foreach($state['stats']['STATS'] as &$r)$r['Temperature Age']=15;unset($r);
expect(!$service->status()['healthy'],'Stale temperature');
rejects(function() use($service){$service->apply(array('action'=>'manual','duty'=>25));});
$state=fixture();foreach($state['stats']['STATS'] as &$r)$r['Fan Fault']=true;unset($r);
expect($service->status()['fault'],'Latched fault');
$service->apply(array('action'=>'reset'));
$state['stats']['STATS'][2]['Temperature Valid']=false;
rejects(function() use($service){$service->apply(array('action'=>'reset'));});
$state=fixture();$state['stats']['STATS'][1]['Fan Requested']=65;
rejects(function() use($service){$service->status();});
$state=fixture();array_pop($state['devs']['DEVS']);
rejects(function() use($service){$service->status();});
$state=fixture();unset($state['stats']['STATS'][0]['Fan Mode']);
rejects(function() use($service){$service->status();});
$dir=sys_get_temp_dir().'/cooling-test-'.bin2hex(openssl_random_pseudo_bytes(8));mkdir($dir,0700);
$path=$dir.'/fan-settings.json';$store=new CoolingStore($path);
expect($store->read()===null,'No preference');
$store->save(array('mode'=>'auto','duty'=>25));
expect($store->read()===array('version'=>1,'mode'=>'auto','duty'=>25),'Roundtrip preference');
expect((fileperms($path)&0777)===0600,'Private preference');
file_put_contents($path,'invalid');rejects(function()use($store){$store->read();});
unlink($path);unlink($path.'.lock');rmdir($dir);
echo "Backend validation, fan whitelist, telemetry and atomic preference tests passed\n";
