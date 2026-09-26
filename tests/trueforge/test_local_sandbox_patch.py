import hashlib
import json
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).parents[2]
SCRIPT = ROOT / "scripts/patch_trueforge_local_sandbox.py"
INSTALLED_SCOPE = ROOT / "integration/node_modules/@truefoundry"


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _fixture(tmp_path: Path) -> tuple[Path, Path, Path]:
    scope = tmp_path / "node_modules/@truefoundry"
    main = scope / "trueforge/dist/main.js"
    core = scope / "trueforge-core/dist/core/sandbox/Sandbox.js"
    core_esm = core.with_suffix(".mjs")
    main.parent.mkdir(parents=True)
    core.parent.mkdir(parents=True)
    shutil.copyfile(INSTALLED_SCOPE / "trueforge/dist/main.js", main)
    shutil.copyfile(INSTALLED_SCOPE / "trueforge-core/dist/core/sandbox/Sandbox.js", core)
    shutil.copyfile(INSTALLED_SCOPE / "trueforge-core/dist/core/sandbox/Sandbox.mjs", core_esm)
    return main, core, core_esm


def _run(main: Path, *args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(SCRIPT), "--main-js", str(main), *args],
        cwd=ROOT,
        check=False,
        capture_output=True,
        text=True,
        timeout=20,
    )


def _js_function(source: str, name: str, next_name: str) -> str:
    start = source.index(f"function {name}(")
    end = source.index(f"function {next_name}(", start)
    return source[start:end]


def test_dry_run_checks_full_hashes_without_writing(tmp_path):
    main, core, core_esm = _fixture(tmp_path)
    before = (_sha256(main), _sha256(core), _sha256(core_esm))
    result = _run(main)
    assert result.returncode == 0, result.stderr
    output = json.loads(result.stdout)
    assert output["state"] == "NOT_RUN"
    assert output["applied"] is False
    assert output["approval_logic_changed"] is False
    assert output["network_policy_changed"] is False
    assert (_sha256(main), _sha256(core), _sha256(core_esm)) == before
    assert [item["baseline_sha256"] for item in output["targets"]] == list(before)


def test_apply_narrows_socket_read_and_requires_python_310(tmp_path):
    main, core, core_esm = _fixture(tmp_path)
    result = _run(main, "--apply")
    assert result.returncode == 0, result.stderr
    output = json.loads(result.stdout)
    assert output["state"] == "PATCHED_RESTART_REQUIRED"
    assert _sha256(main) == "f1721874969562f995142c5d87a2e3cc75c83d73fbfe061aaa0021d09e922ced"
    assert _sha256(core) == "325b72a1feb6efd7ef0c277320f02b706aefc70fb19160ad86dc98b0bbb80dbe"
    assert _sha256(core_esm) == "b7c20bc450d66f3cd3b91efaaf235d0877140907e0dfd3e5d2ea93a89530563d"

    main_text = main.read_text(encoding="utf-8")
    core_text = core.read_text(encoding="utf-8")
    core_esm_text = core_esm.read_text(encoding="utf-8")
    assert "...codeModeSocketAllow(params.codeModeSocketPath)" in main_text
    assert "allowRead: [...platformAllowRead(platform)]" in main_text
    assert "params.sandboxRootPath,\n      ...codeModeSocketParentAllow()" not in main_text
    assert "codeModeSocketParentAllow" not in main_text
    assert "codeModeSocketPath: env?.TFY_MCP_SOCK" in main_text
    assert "!lstatSync(socketPath).isSocket()" in main_text
    assert 'PYTHON_CANDIDATES = ["python3.12", "python3.11", "python3.10"' in main_text
    assert "sys.version_info >= (3, 10)" in main_text
    assert 'error: "Local sandbox command timed out"' in main_text
    for source in (core_text, core_esm_text):
        inject_start = source.index("function injectMCPClientEnv(")
        inject_end = source.index("var sandboxExecSchema", inject_start)
        schema_end = source.index("var SANDBOX_EXEC_DESCRIPTION", inject_end)
        assert "params.env" not in source[inject_start:inject_end]
        assert "Additional environment variables to set" not in source[inject_end:schema_end]
    for target in (main, core, core_esm):
        syntax = subprocess.run(
            ["node", "--check", str(target)],
            check=False,
            capture_output=True,
            text=True,
            timeout=20,
        )
        assert syntax.returncode == 0, syntax.stderr

    second = _run(main, "--apply")
    assert second.returncode == 0, second.stderr
    assert json.loads(second.stdout)["state"] == "PATCHED_RESTART_REQUIRED"


def test_refuses_any_unrecognized_vendor_bytes_without_partial_write(tmp_path):
    main, core, core_esm = _fixture(tmp_path)
    main.write_bytes(main.read_bytes() + b"\n// unreviewed mutation\n")
    before = (main.read_bytes(), core.read_bytes(), core_esm.read_bytes())
    result = _run(main, "--apply")
    assert result.returncode == 5
    assert json.loads(result.stdout) == {
        "ok": False,
        "state": "REFUSED",
        "error_code": "TRUEFORGE_MAIN_HASH_MISMATCH",
    }
    assert (main.read_bytes(), core.read_bytes(), core_esm.read_bytes()) == before


def test_actual_patched_policy_allows_only_current_canonical_socket(tmp_path):
    main, core, core_esm = _fixture(tmp_path)
    assert _run(main, "--apply").returncode == 0
    main_text = main.read_text(encoding="utf-8")
    core_text = core.read_text(encoding="utf-8")
    core_esm_text = core_esm.read_text(encoding="utf-8")
    socket_function = _js_function(main_text, "codeModeSocketAllow", "linuxNetworkSocketAllow")
    command_env_start = main_text.index("const LOCAL_SANDBOX_ALLOWED_EXTRA_ENV")
    policy_start = main_text.index("function filesystemPolicy(")
    policy_function = main_text[policy_start:command_env_start]
    command_env_end = main_text.index("function sessionFilesystem", command_env_start)
    command_env_functions = main_text[command_env_start:command_env_end]
    darwin_paths_function = _js_function(
        main_text, "darwinUnixSocketPaths", "syncDarwinUnixSockets"
    )
    session_config_start = main_text.index("function buildSessionConfig(")
    session_config_end = main_text.index("async function createSandbox", session_config_start)
    session_config_function = main_text[session_config_start:session_config_end]
    classifier_start = main_text.index(
        "if (session.protocolError !== void 0) {\n            return { success: false"
    )
    classifier_end = main_text.index("\n        } catch (error)", classifier_start)
    classifier = main_text[classifier_start:classifier_end]
    inject_start = core_text.index("function injectMCPClientEnv(")
    inject_end = core_text.index("var sandboxExecSchema", inject_start)
    inject_function = core_text[inject_start:inject_end]
    esm_inject_start = core_esm_text.index("function injectMCPClientEnv(")
    esm_inject_end = core_esm_text.index("var sandboxExecSchema", esm_inject_start)
    esm_inject_function = core_esm_text[esm_inject_start:esm_inject_end].replace(
        "function injectMCPClientEnv(", "function injectMCPClientEnvEsm(", 1
    )

    program = f"""
const assert = require('node:assert/strict');
const codeModeSocketParentPath = '/run/tfy-cm';
const isAbsolute2 = p => p.startsWith('/');
const dirname2 = p => p.slice(0, p.lastIndexOf('/'));
const realpathSync2 = p => p.includes('symlink') ? '/run/tfy-cm/real' : p;
const lstatSync = p => ({{ isSocket: () => !p.includes('regular') }});
const denySharedDefaultWritePaths = () => ['/tmp'];
const linuxNetworkSocketAllow = () => ['/run/srt-proxy'];
const platformAllowRead = () => ['/usr/bin'];
const join3 = (...parts) => parts.join('/');
const SANDBOX_VENV_DIR = '.venv';
const sandboxVenvPath = root => root + '/.venv';
const commandPath = () => '/usr/local/bin:/usr/bin:/bin';
{socket_function}
{policy_function}
{command_env_functions}
const own = '/run/tfy-cm/01CURRENT';
const policy = filesystemPolicy({{sandboxRootPath:'/sandbox/a', platform:'linux', codeModeSocketPath:own}});
assert(policy.allowRead.includes(own));
assert(!policy.allowRead.includes(codeModeSocketParentPath));
assert.throws(() => codeModeSocketAllow('/run/other/01CURRENT'));
assert.throws(() => codeModeSocketAllow('/run/tfy-cm/symlink'));
assert.throws(() => codeModeSocketAllow('/run/tfy-cm/regular'));
const trustedEnv = commandEnv({{sandboxRootPath:'/sandbox/a',platform:'linux',extra:{{TFY_MCP_SOCK:own,PYTHONPATH:'mcp-client'}}}});
assert.equal(trustedEnv.TFY_MCP_SOCK, own);
assert.equal(trustedEnv.PYTHONPATH, 'mcp-client');
for (const key of ['BASH_ENV','ENV','LD_PRELOAD','LD_LIBRARY_PATH','NODE_OPTIONS','PYTHONHOME']) {{
  assert.throws(
    () => commandEnv({{sandboxRootPath:'/sandbox/a',platform:'linux',extra:{{[key]:'/outside/marker'}}}}),
    /Local sandbox environment key is not permitted/
  );
}}

const darwinUnixSocketSandboxRoots = new Set();
const sessionNetwork = params => params;
const sessionFilesystem = platform => ({{platform}});
{darwin_paths_function}
{session_config_function}
const linuxSession = buildSessionConfig('linux');
assert.deepEqual(linuxSession.network.unixSockets, []);
assert.deepEqual(linuxSession.filesystem, {{platform:'linux'}});

const mcpClientLayout = () => undefined;
const injectTraceContextEnv = () => ({{}});
{inject_function}
{esm_inject_function}
const attackerEnv = {{TFY_MCP_SOCK:'/run/tfy-cm/attacker',BASH_ENV:'/outside/marker',LD_PRELOAD:'/outside/lib.so',NODE_OPTIONS:'--require=/outside/x'}};
const trusted = injectMCPClientEnv({{env:attackerEnv, codeModeEnv:{{TFY_MCP_SOCK:own}}, mcpServers:{{}}, mcpClientInstall:undefined}});
assert.equal(trusted.TFY_MCP_SOCK, own);
assert.equal(trusted.BASH_ENV, undefined);
assert.equal(trusted.LD_PRELOAD, undefined);
assert.equal(trusted.NODE_OPTIONS, undefined);
const absent = injectMCPClientEnv({{env:attackerEnv, codeModeEnv:undefined, mcpServers:{{}}, mcpClientInstall:undefined}});
assert.equal(absent.TFY_MCP_SOCK, undefined);
const esmTrusted = injectMCPClientEnvEsm({{env:attackerEnv, codeModeEnv:{{TFY_MCP_SOCK:own}}, mcpServers:{{}}, mcpClientInstall:undefined}});
assert.equal(esmTrusted.TFY_MCP_SOCK, own);
assert.equal(esmTrusted.BASH_ENV, undefined);
assert.equal(esmTrusted.LD_PRELOAD, undefined);
assert.equal(esmTrusted.NODE_OPTIONS, undefined);
const esmAbsent = injectMCPClientEnvEsm({{env:attackerEnv, codeModeEnv:undefined, mcpServers:{{}}, mcpClientInstall:undefined}});
assert.equal(esmAbsent.TFY_MCP_SOCK, undefined);

function classify(session) {{
{classifier}
}}
assert.deepEqual(classify({{protocolError:'oversized',timedOut:false,stdoutText:'',stderrText:'',exitCode:1}}), {{success:false,error:'oversized'}});
assert.deepEqual(classify({{protocolError:undefined,timedOut:true,stdoutText:'',stderrText:'',exitCode:1}}), {{success:false,error:'Local sandbox command timed out'}});
assert.deepEqual(classify({{protocolError:undefined,timedOut:false,stdoutText:'ok',stderrText:'',exitCode:0}}), {{success:true,response:{{exitCode:0,result:'ok'}}}});
"""
    result = subprocess.run(
        ["node", "-e", program],
        check=False,
        capture_output=True,
        text=True,
        timeout=20,
    )
    assert result.returncode == 0, result.stderr
