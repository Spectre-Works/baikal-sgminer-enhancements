<?php
session_start();
header('Content-Type: application/json');header('Cache-Control: no-store');
function cooling_reply($code,$data) {http_response_code($code);echo json_encode($data);exit;}
if (!isset($_SESSION['_logged_']) || $_SESSION['_logged_']!==true) cooling_reply(401,array('error'=>'Login required'));
require_once __DIR__.'/inc/fan.inc.php';
if (!isset($_SESSION['cooling_csrf'])) {
    $strong=false;$bytes=openssl_random_pseudo_bytes(32,$strong);
    if ($bytes===false || !$strong) cooling_reply(503,array('error'=>'Security token unavailable'));
    $_SESSION['cooling_csrf']=bin2hex($bytes);
}
$token=$_SESSION['cooling_csrf'];session_write_close();
$store=new CoolingStore('/opt/scripta/etc/cooling/fan-settings.json');
$service=new CoolingService('cooling_api');
try {
    if ($_SERVER['REQUEST_METHOD']==='GET') {
        $saved=null;$save_error=null;
        try {$saved=$store->read();} catch (RuntimeException $e) {$save_error=$e->getMessage();}
        cooling_reply(200,array('fan'=>$service->status(),'startup'=>$saved,'startup_error'=>$save_error,'csrf'=>$token));
    }
    if ($_SERVER['REQUEST_METHOD']!=='POST') cooling_reply(405,array('error'=>'POST required'));
    if (!isset($_SERVER['HTTP_X_COOLING_CSRF']) || !hash_equals($token,$_SERVER['HTTP_X_COOLING_CSRF']))
        cooling_reply(403,array('error'=>'Security token expired; refresh the page'));
    $body=file_get_contents('php://input',false,null,0,2049);
    if (strlen($body)>2048) cooling_reply(413,array('error'=>'Request too large'));
    $input=json_decode($body,true);
    if (!is_array($input) || !isset($input['action'])) throw new InvalidArgumentException('Invalid request');
    if ($input['action']==='save') {
        cooling_reply(200,array('saved'=>$store->save($input),'applied'=>false));
    }
    cooling_reply(202,$service->apply($input));
} catch (InvalidArgumentException $e) {cooling_reply(400,array('error'=>$e->getMessage()));}
catch (RuntimeException $e) {cooling_reply(503,array('error'=>$e->getMessage()));}
