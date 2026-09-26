/** Deterministic Linux canaries using the installed native LocalSandboxProvider.
 * The operator prepares a read-only runtime helper from the guarded vendor bundle.
 * No AWS call, model call, real credential read or cloud cleanup occurs here.
 */
import assert from 'node:assert/strict';
import crypto from 'node:crypto';
import fs from 'node:fs/promises';
import net from 'node:net';
import os from 'node:os';
import path from 'node:path';
import {pathToFileURL} from 'node:url';

const [helperPath, vendorPath, expectedHash, optCanary] = process.argv.slice(2);
assert.equal(process.platform, 'linux');
assert.ok(expectedHash && /^[a-f0-9]{64}$/.test(expectedHash));
const vendor = await fs.readFile(vendorPath, 'utf8');
assert.equal(crypto.createHash('sha256').update(vendor).digest('hex'), expectedHash);
const marker = 'try {\n  const logger = createServerLogger({';
const index = vendor.lastIndexOf(marker);
assert.ok(index > 0);
const helper = vendor.slice(0, index) + '\ninit_LocalSandboxProvider();\nexport { LocalSandboxProvider, resetSrt };\n';
assert.equal(await fs.readFile(helperPath, 'utf8'), helper);
const {LocalSandboxProvider, resetSrt} = await import(pathToFileURL(helperPath));
const nonce = crypto.randomBytes(8).toString('hex');
const parent = `/var/lib/preflight-user/local-sandbox-probe-${nonce}`;
const bridgeParent = '/tmp/tf_cms';
const aPath = `${bridgeParent}/pf-a-${nonce}`;
const bPath = `${bridgeParent}/pf-b-${nonce}`;
const files = [
  `/var/lib/preflight/pf-canary-${nonce}`,
  `/var/lib/preflight-trueforge/pf-canary-${nonce}`,
  optCanary,
];
const privateHost = Object.values(os.networkInterfaces()).flat().find(a => a && a.family === 'IPv4' && !a.internal)?.address;
assert.ok(privateHost);
const servers = [];
let provider;
let a;
let b;
const summary = {kind: 'NATIVE_LOCAL_LINUX_CANARIES', vendor_sha256: expectedHash};
const logger = {child() { return this; }, info() {}, warn() {}, error() {}, debug() {}};

async function listen(socketPath, response) {
  const server = net.createServer({allowHalfOpen: true}, socket => {
    socket.on('error', () => {});
    socket.on('data', () => {});
    socket.on('end', () => socket.end(JSON.stringify({nonce: response})));
  });
  await new Promise((resolve, reject) => {
    server.once('error', reject);
    server.listen(socketPath, resolve);
  });
  await fs.chmod(socketPath, 0o600);
  servers.push(server);
}

async function reachable(host, port) {
  return await new Promise(resolve => {
    const socket = net.createConnection({host, port});
    const finish = value => { socket.destroy(); resolve(value); };
    socket.setTimeout(1000, () => finish(false));
    socket.once('connect', () => finish(true));
    socket.once('error', () => finish(false));
  });
}

function python(code) {
  return `python -c '${code.replaceAll("'", "'\\''")}'`;
}

async function run(code, env = {}) {
  const result = await provider.exec({sandboxId: a.sandboxId, command: python(code), env,
    timeoutSeconds: 10});
  assert.equal(result.success, true, 'native execution must succeed');
  assert.equal(result.response.exitCode, 0, 'canary process must finish successfully');
  return JSON.parse(result.response.result.trim());
}

try {
  await fs.mkdir(parent, {mode: 0o700});
  for (const file of files.slice(0, 2)) await fs.writeFile(file, nonce, {flag: 'wx', mode: 0o600});
  assert.equal((await fs.stat(optCanary)).isFile(), true);
  await listen(aPath, 'own');
  await listen(bPath, 'foreign');
  const tcp = net.createServer(socket => socket.end('inert-canary'));
  await new Promise((resolve, reject) => {
    tcp.once('error', reject);
    tcp.listen(0, '0.0.0.0', resolve);
  });
  servers.push(tcp);
  const tcpPort = tcp.address().port;
  summary.host_positive_controls = {
    loopback_listener: await reachable('127.0.0.1', tcpPort),
    private_listener: await reachable(privateHost, tcpPort),
    imds_tcp: await reachable('169.254.169.254', 80),
  };
  assert.ok(Object.values(summary.host_positive_controls).every(v => v === true));
  const support = await LocalSandboxProvider.isSupported({codeModeSocketParentPath: bridgeParent});
  assert.equal(support.supported, true, 'native support probe required');
  assert.ok(/python3\.(?:1[0-9])$/.test(support.python), 'Python 3.10+ required');
  summary.python = path.basename(support.python);
  provider = new LocalSandboxProvider({sandboxRootPathParent: parent,
    codeModeSocketParentPath: bridgeParent, support, logger});
  a = await provider.createSandbox();
  b = await provider.createSandbox();
  const sibling = path.join(b.sandboxId, 'sibling-canary');
  await fs.writeFile(sibling, nonce, {flag: 'wx', mode: 0o600});
  process.env.PREFLIGHT_HOST_CANARY = nonce;
  const code = `import os,json,socket
targets=${JSON.stringify([...files, sibling])}
checks={}
for i,p in enumerate(targets):
 for mode in ('rb','ab'):
  try:
   f=open(p,mode); f.close(); allowed=True
  except OSError: allowed=False
  checks[str(i)+'_'+mode+'_denied']=not allowed
link='private-link'
os.symlink(targets[0],link)
try:
 f=open(link,'rb'); f.close(); allowed=True
except OSError: allowed=False
checks['symlink_denied']=not allowed
checks['host_env_absent']='PREFLIGHT_HOST_CANARY' not in os.environ
checks['host_proc_absent']=not os.path.exists('/proc/${process.pid}')
for label,host,port in [('loopback','127.0.0.1',${tcpPort}),('private',${JSON.stringify(privateHost)},${tcpPort}),('imds','169.254.169.254',80)]:
 s=socket.socket();s.settimeout(0.5)
 try: s.connect((host,port)); allowed=True
 except OSError: allowed=False
 finally: s.close()
 checks[label+'_tcp_denied']=not allowed
import http.client,urllib.parse,base64
proxy=os.environ.get('HTTP_PROXY') or os.environ.get('http_proxy')
checks['proxy_present']=bool(proxy)
parsed=urllib.parse.urlsplit(proxy)
headers={}
if parsed.username is not None:
 auth=urllib.parse.unquote(parsed.username)+':'+urllib.parse.unquote(parsed.password or '')
 headers['Proxy-Authorization']='Basic '+base64.b64encode(auth.encode()).decode()
for label,host,port in [('loopback','127.0.0.1',${tcpPort}),('private',${JSON.stringify(privateHost)},${tcpPort}),('imds','169.254.169.254',80)]:
 conn=http.client.HTTPConnection(parsed.hostname,parsed.port,timeout=2)
 try:
  conn.request('GET','http://'+host+':'+str(port)+'/preflight-inert-canary',headers=headers)
  response=conn.getresponse();denied=response.status==403;response.close()
 except OSError: denied=False
 finally: conn.close()
 checks[label+'_proxy_policy_denied']=denied
for label,p,expected in [('own',${JSON.stringify(aPath)},'own'),('foreign',${JSON.stringify(bPath)},'foreign')]:
 s=socket.socket(socket.AF_UNIX);s.settimeout(1)
 try:
  s.connect(p);s.sendall(b'{}');s.shutdown(socket.SHUT_WR);value=json.loads(s.recv(256))
  allowed=value.get('nonce')==expected
 except OSError: allowed=False
 finally:s.close()
 checks[label+'_bridge_'+('allowed' if label=='own' else 'denied')]=allowed if label=='own' else not allowed
print(json.dumps(checks))`;
  summary.checks = await run(code, {TFY_MCP_SOCK: aPath});
  assert.ok(Object.values(summary.checks).every(value => value === true), 'all isolation canaries required');
  for (const file of files.slice(0, 2)) assert.equal(await fs.readFile(file, 'utf8'), nonce);
  assert.equal(await fs.readFile(sibling, 'utf8'), nonce);
  const escaped = path.join(parent, 'launcher-escaped-marker');
  const startup = path.join(a.sandboxId, 'inert-startup.sh');
  await fs.writeFile(startup, `printf inert > '${escaped}'\n`, {flag: 'wx', mode: 0o600});
  const refused = await provider.exec({sandboxId: a.sandboxId, command: 'true',
    env: {BASH_ENV: startup}, timeoutSeconds: 2});
  assert.equal(refused.success, false);
  assert.equal(refused.error, 'Local sandbox environment key is not permitted');
  summary.launcher_environment_refused = await fs.stat(escaped).then(() => false, () => true);
  assert.equal(summary.launcher_environment_refused, true);
  const delayed = path.join(a.sandboxId, 'delayed-child-marker');
  const childReady = path.join(a.sandboxId, 'child-ready');
  const parentReady = path.join(a.sandboxId, 'parent-ready');
  const childCode = `import time,pathlib;pathlib.Path(${JSON.stringify(childReady)}).write_text("ready");time.sleep(3);pathlib.Path(${JSON.stringify(delayed)}).write_text("marker")`;
  const timeoutCode = `import subprocess,time,pathlib
subprocess.Popen(["python","-c",${JSON.stringify(childCode)}])
while not pathlib.Path(${JSON.stringify(childReady)}).exists(): time.sleep(0.01)
pathlib.Path(${JSON.stringify(parentReady)}).write_text("ready")
time.sleep(30)`;
  const start = performance.now();
  const timed = await provider.exec({sandboxId: a.sandboxId, command: python(timeoutCode), timeoutSeconds: 1});
  summary.timeout_elapsed_ms = Math.ceil(performance.now() - start);
  assert.ok(summary.timeout_elapsed_ms >= 800 && summary.timeout_elapsed_ms < 3000);
  assert.equal(await fs.readFile(childReady, 'utf8'), 'ready');
  assert.equal(await fs.readFile(parentReady, 'utf8'), 'ready');
  assert.equal(timed.success, false);
  assert.equal(timed.error, 'Local sandbox command timed out');
  await new Promise(resolve => setTimeout(resolve, 3500));
  summary.timed_child_marker_absent = await fs.stat(delayed).then(() => false, () => true);
  assert.equal(summary.timed_child_marker_absent, true);
  summary.timeout_tool_success = timed.success;
  summary.accepted = true;
  console.log(JSON.stringify(summary));
} finally {
  delete process.env.PREFLIGHT_HOST_CANARY;
  await resetSrt();
  for (const server of servers) await new Promise(resolve => server.close(resolve));
  for (const socketPath of [aPath,bPath]) await fs.unlink(socketPath).catch(() => {});
  for (const file of files.slice(0,2)) await fs.unlink(file).catch(() => {});
  assert.ok(parent.startsWith('/var/lib/preflight-user/local-sandbox-probe-'));
  await fs.rm(parent, {recursive:true,force:true});
}
