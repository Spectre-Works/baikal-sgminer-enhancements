<?php
// Test-only server router. Never install this file in the production web root.
if (parse_url($_SERVER['REQUEST_URI'],PHP_URL_PATH)==='/test-login') {
    session_start();$_SESSION['_logged_']=true;echo 'test session';return true;
}
return false;
