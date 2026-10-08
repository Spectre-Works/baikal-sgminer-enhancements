<?php
/* PHP5.6-compatible, fan-only localhost bridge. No shell or generic API proxy. */
function cooling_api($command, $parameter = null) {
    $request = array('command'=>$command);
    if ($parameter !== null) $request['parameter']=$parameter;
    $socket=@stream_socket_client('tcp://127.0.0.1:4028', $errno, $error, 1);
    if (!$socket) throw new RuntimeException('Miner API unavailable');
    stream_set_timeout($socket,1,500000);
    $deadline=microtime(true)+1.5;
    try {
        $wire=json_encode($request); $sent=0;
        while ($sent<strlen($wire)) {
            $n=@fwrite($socket,substr($wire,$sent));
            if (!$n || microtime(true)>$deadline) throw new RuntimeException('Miner API timeout');
            $sent+=$n;
        }
        $data='';
        while (!feof($socket)) {
            $chunk=@fread($socket,8192);
            if ($chunk===false) throw new RuntimeException('Miner API read failed');
            $data.=$chunk;
            if (strlen($data)>262144) throw new RuntimeException('Miner API response too large');
            if (strpos($data,"\0")!==false) break;
            $meta=stream_get_meta_data($socket);
            if ($meta['timed_out'] || microtime(true)>$deadline || $chunk==='')
                throw new RuntimeException('Miner API timeout');
        }
    } finally { fclose($socket); }
    $result=json_decode(rtrim($data,"\0"),true);
    if (!is_array($result) || !isset($result['STATUS'][0]['STATUS']) || $result['STATUS'][0]['STATUS']!=='S')
        throw new RuntimeException('Miner rejected request or returned invalid data');
    return $result;
}

function cooling_preference($input) {
    if (!is_array($input) || !isset($input['mode']) || !in_array($input['mode'],array('auto','manual'),true))
        throw new InvalidArgumentException('Choose Automatic or Manual');
    $duty=isset($input['duty']) ? $input['duty'] : null;
    if (!is_int($duty) || $duty<10 || $duty>100) throw new InvalidArgumentException('Duty must be a whole number from 10 to 100');
    return array('version'=>1,'mode'=>$input['mode'],'duty'=>$duty);
}

class CoolingStore {
    private $path;
    function __construct($path) {$this->path=$path;}
    function read() {
        if (!file_exists($this->path)) return null;
        $size=@filesize($this->path);
        if ($size===false || $size>2048) throw new RuntimeException('Saved preference unavailable');
        $data=json_decode(@file_get_contents($this->path),true);
        if (!isset($data['version']) || $data['version']!==1) throw new RuntimeException('Saved preference invalid');
        try {return cooling_preference($data);} catch (InvalidArgumentException $e) {throw new RuntimeException('Saved preference invalid');}
    }
    function save($input) {
        $value=cooling_preference($input);
        $lock=@fopen($this->path.'.lock','c');
        if (!$lock) throw new RuntimeException('Cannot lock startup preference');
        if (!flock($lock,LOCK_EX)) {fclose($lock);throw new RuntimeException('Cannot lock startup preference');}
        $tmp=false;
        try {
            $tmp=@tempnam(dirname($this->path),'.cooling-');
            if ($tmp===false || dirname($tmp)!==dirname($this->path) || !@chmod($tmp,0600))
                throw new RuntimeException('Cannot save startup preference');
            $json=json_encode($value)."\n";
            if (@file_put_contents($tmp,$json)!==strlen($json) || !@rename($tmp,$this->path))
                throw new RuntimeException('Cannot save startup preference');
            $tmp=false;
        } finally {
            if ($tmp!==false) @unlink($tmp);
            flock($lock,LOCK_UN);fclose($lock);
        }
        return $value;
    }
}

class CoolingService {
    private $transport;
    function __construct($transport) {$this->transport=$transport;}
    private function api($command,$parameter=null) {return call_user_func($this->transport,$command,$parameter);}
    function status() {
        $devs=$this->api('devs');$stats=$this->api('stats');
        if (!isset($devs['DEVS'],$stats['STATS']) || !is_array($devs['DEVS']) || !is_array($stats['STATS']))
            throw new RuntimeException('Fan telemetry unavailable');
        $boards=array();$seen=array();
        foreach ($devs['DEVS'] as $dev) {
            if (!isset($dev['Name']) || $dev['Name']!=='BKLU') continue;
            if (!isset($dev['ASC'],$dev['ID']) || !is_int($dev['ASC']) || !is_int($dev['ID']) ||
                $dev['ASC']<0 || $dev['ID']<0 || $dev['ID']>2 || isset($seen[$dev['ID']]))
                throw new RuntimeException('Unsupported or ambiguous fan controller');
            $seen[$dev['ID']]=true;$matched=array();
            foreach ($stats['STATS'] as $row)
                if (isset($row['ID']) && $row['ID']==='BKLU'.$dev['ID']) $matched[]=$row;
            if (count($matched)!==1) throw new RuntimeException('Incomplete fan telemetry');
            $row=$matched[0];
            foreach (array('Fan Mode','Fan Requested','Fan Acknowledged','Fan Acknowledged Valid',
                           'Fan Pending','Fan Fault','Fan Telemetry Failsafe','Fan Hottest','Temperature Age','Temperature Valid') as $key)
                if (!array_key_exists($key,$row)) throw new RuntimeException('Compatible fan build required');
            foreach (array('Fan Acknowledged Valid','Fan Pending','Fan Fault','Fan Telemetry Failsafe','Temperature Valid') as $key)
                if (!is_bool($row[$key])) throw new RuntimeException('Invalid fan telemetry');
            foreach (array('Fan Requested','Fan Acknowledged') as $key)
                if (!is_int($row[$key]) || $row[$key]<0 || $row[$key]>100) throw new RuntimeException('Invalid duty telemetry');
            if (!in_array($row['Fan Mode'],array('auto','manual'),true) || !is_int($row['Temperature Age']) || $row['Temperature Age']<0 ||
                !is_int($row['Fan Hottest']) || $row['Fan Hottest'] < -1 || $row['Fan Hottest']>150)
                throw new RuntimeException('Invalid fan telemetry');
            $boards[]=array('asc'=>$dev['ASC'],'id'=>$dev['ID'],'temperature'=>isset($dev['Temperature']) ? $dev['Temperature']:null,
                'valid'=>$row['Temperature Valid'] && $row['Temperature Age']<15 && isset($dev['Status'],$dev['Enabled']) && $dev['Status']==='Alive' && $dev['Enabled']==='Y',
                'age'=>$row['Temperature Age'],'row'=>$row);
        }
        if (count($boards)!==3 || count($seen)!==3) throw new RuntimeException('Exactly one supported three-board controller required');
        usort($boards,function($a,$b){return $a['id']-$b['id'];});
        $first=$boards[0]['row'];$healthy=true;$output=array();
        foreach ($boards as $board) {
            foreach (array('Fan Mode','Fan Requested','Fan Acknowledged','Fan Acknowledged Valid','Fan Pending','Fan Fault','Fan Telemetry Failsafe','Fan Hottest') as $key)
                if ($board['row'][$key]!==$first[$key]) throw new RuntimeException('Fan controller telemetry disagrees');
            $healthy=$healthy && $board['valid'];unset($board['row']);$output[]=$board;
        }
        return array('supported'=>true,'asc'=>$boards[0]['asc'],'mode'=>$first['Fan Mode'],
            'requested'=>$first['Fan Requested'],'acknowledged'=>$first['Fan Acknowledged Valid'] ? $first['Fan Acknowledged']:null,
            'ack_valid'=>$first['Fan Acknowledged Valid'],'pending'=>$first['Fan Pending'],'fault'=>$first['Fan Fault'],
            'failsafe'=>$first['Fan Telemetry Failsafe'],'hottest'=>$first['Fan Hottest']<0 ? null:$first['Fan Hottest'],
            'healthy'=>$healthy,'boards'=>$output,'time'=>time());
    }
    function apply($input) {
        if (!is_array($input) || !isset($input['action']) || !is_string($input['action'])) throw new InvalidArgumentException('Invalid action');
        $action=$input['action'];
        if (!in_array($action,array('auto','manual','full','reset'),true)) throw new InvalidArgumentException('Unsupported action');
        $duty=null;
        if ($action==='manual') $duty=cooling_preference(array('mode'=>'manual','duty'=>isset($input['duty'])?$input['duty']:null))['duty'];
        $state=$this->status();
        if ($action==='manual' && (!$state['healthy'] || $state['fault'] || $state['pending'] || !$state['ack_valid']))
            throw new RuntimeException('Manual control requires healthy acknowledged telemetry; use Automatic or Full Cooling');
        if ($action==='reset' && (!$state['fault'] || !$state['healthy'] || !$state['ack_valid'] || $state['pending']))
            throw new RuntimeException('Fault reset requires recovered telemetry and acknowledged cooling');
        $parameter=$state['asc'].',';
        if ($action==='auto') $parameter.='fan-auto,on';
        elseif ($action==='reset') $parameter.='fan-reset,yes';
        else $parameter.='fan,'.($action==='full'?100:$duty);
        $this->api('ascset',$parameter);
        return array('queued'=>true,'action'=>$action,'duty'=>$action==='full'?100:$duty);
    }
}
