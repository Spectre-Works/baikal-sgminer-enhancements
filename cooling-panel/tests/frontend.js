const assert=require('assert'),fs=require('fs'),vm=require('vm');
// Identification remains visible even when miner telemetry is unavailable.
const template=fs.readFileSync(__dirname+'/../package/web/partials/fan.html','utf8');
const identity=template.match(/<div class="panel-footer">([\s\S]*?)<\/div>/);
assert(identity,'Visible modification identification footer is required');
assert(identity[1].includes('Modified software:'));
assert(identity[1].includes('Baikal sgminer enhancements'));
assert(identity[1].includes('<span>v0.3.2</span>'));
assert(identity[1].includes('Live fan control + Cooling panel'));
assert(identity[1].includes('href="https://github.com/Spectre-Works/baikal-sgminer-enhancements"'));
assert(identity[1].includes('target="_blank" rel="noopener noreferrer"'));
assert(!/ng-(?:show|if|hide)|\{\{/.test(identity[0]),'Identification must not depend on API status');
let controller;
const angular={module:()=>({controller:(name,fn)=>{controller=fn;}})};
vm.runInNewContext(fs.readFileSync(__dirname+'/../package/web/ng/cooling.js','utf8'),{angular,Date,Math});
let reads=[],writes=[],timers=[],destroy;
function response(store){let chain={success(fn){chain.ok=fn;return chain;},error(fn){chain.fail=fn;return chain;},then(fn){chain.done=fn;return chain;}};store.push(chain);return chain;}
let http={get:()=>response(reads),post:(url,input,options)=>{let chain=response(writes);chain.input=input;chain.options=options;return chain;}};
let scope={$on:(event,fn)=>{destroy=fn;}};
let timeout=fn=>{timers.push(fn);return fn;};timeout.cancel=fn=>{timers=timers.filter(x=>x!==fn);};
controller(scope,http,timeout);
function state(extra={}){return {fan:Object.assign({mode:'auto',ack_valid:true,acknowledged:25,pending:false,fault:false,healthy:true},extra),csrf:'token',startup:null};}
let first=reads.shift();first.ok(state());first.done();scope.cooling.duty=40;
scope.coolingApply();assert.equal(writes.length,1);assert.equal(writes[0].options.headers['X-Cooling-CSRF'],'token');
writes[0].ok({queued:true});assert(scope.cooling.busy);
// Status polls never perform a write and preserve unsaved form edits.
timers.shift()();let poll=reads.shift();poll.ok(state({pending:true}));poll.done();
assert(scope.cooling.busy);assert.equal(scope.cooling.duty,40);assert.equal(writes.length,1);
timers.shift()();poll=reads.shift();poll.ok(state());poll.done();
assert(!scope.cooling.busy);assert.equal(writes.length,1);
scope.cooling.mode='manual';scope.cooling.duty=33;scope.coolingApply();
assert.equal(writes[1].input.duty,33);
writes[1].fail({error:'Uncertain result'},503);assert(!scope.cooling.fresh);assert(!scope.cooling.busy);
scope.coolingApply();assert.equal(writes.length,2); // no retry before fresh status
timers.shift()();poll=reads.shift();poll.ok(state());poll.done();
scope.coolingSave();assert.equal(writes[2].input.action,'save');
writes[2].ok({saved:{mode:'manual',duty:33}});assert.equal(scope.cooling.startup.duty,33);
destroy();assert.equal(timers.length,0);
console.log('Frontend token, pending/ack lifecycle, saved preference, preserved edits and uncertain-write tests passed');
