'use strict';
angular.module('Scripta.controllers').controller('CtrlCooling', function($scope, $http, $timeout) {
  var timer, destroyed=false, inFlight=false, token=null, initialized=false, target=null, deadline=0;
  $scope.cooling={state:null, mode:'auto', duty:25, busy:false, saving:false, error:null, message:null, fresh:false, startup:null};
  var c=$scope.cooling;
  function matches(s) {
    if (!s.ack_valid || s.pending || s.fault) return false;
    if (target.action==='reset') return s.healthy;
    if (target.action==='auto') return s.mode==='auto';
    return s.mode==='manual' && s.acknowledged===target.duty;
  }
  function schedule(delay) {if (!destroyed) timer=$timeout(poll,delay);}
  function poll() {
    if (destroyed || inFlight) return;
    inFlight=true;
    $http.get('f_fan.php',{timeout:6000}).success(function(data) {
      if (!data || !data.fan || !data.csrf) {c.error='Invalid cooling response';c.fresh=false;return;}
      c.state=data.fan;c.fresh=true;token=data.csrf;c.startup=data.startup;c.startupError=data.startup_error;
      c.error=null;c.updated=new Date();
      if (!initialized) {c.mode=c.state.mode;c.duty=c.state.ack_valid ? Math.max(10,c.state.acknowledged):100;initialized=true;}
      if (target) {
        if (matches(c.state)) {c.message='Cooling setting acknowledged';c.busy=false;target=null;}
        else if (c.state.fault || Date.now()>deadline) {c.error='Setting not confirmed. Check the cooling status.';c.busy=false;target=null;}
      }
    }).error(function(data,status) {
      c.fresh=false;c.error=status===401?'Session expired. Log in again.':(data && data.error || 'Cooling status unavailable');
      if (target && Date.now()>deadline) {c.busy=false;target=null;}
    }).then(function() {inFlight=false;schedule(target?1000:5000);});
  }
  function refreshSoon() {if(timer) $timeout.cancel(timer);if(!inFlight) schedule(100);}
  function post(input,save) {
    if (!token || !c.fresh || c.busy || c.saving) return;
    c.error=null;c.message=null;
    if(save) c.saving=true;else c.busy=true;
    $http.post('f_fan.php',input,{timeout:6000,headers:{'X-Cooling-CSRF':token}}).success(function(data) {
      if(save) {c.saving=false;c.startup=data.saved;c.message='Startup preference saved; running mode unchanged';}
      else {target={action:input.action,duty:input.action==='full'?100:input.duty};deadline=Date.now()+12000;c.message='Request queued; waiting for acknowledgement';}
      refreshSoon();
    }).error(function(data,status) {
      c.busy=false;c.saving=false;c.fresh=false;
      c.error=status===401?'Session expired. Log in again.':(data && data.error || 'Request failed or timed out. Refresh status before retrying.');
      refreshSoon();
    });
  }
  $scope.coolingApply=function() {post({action:c.mode==='auto'?'auto':'manual',duty:c.duty},false);};
  $scope.coolingAction=function(action) {post({action:action},false);};
  $scope.coolingSave=function() {post({action:'save',mode:c.mode,duty:c.duty},true);};
  $scope.coolingRefresh=refreshSoon;
  $scope.$on('$destroy',function(){destroyed=true;if(timer) $timeout.cancel(timer);});
  poll();
});
