"""Regression test for issue #1: modes under active/, reactive/, and emergency/
must import when the platform provides only the legacy volttron.platform API,
with neither the volttron nor volttron-core distribution installed (the shape
der-control-fastlib's compatibility shim presents).

Runs in a subprocess with a fresh interpreter: this scenario's stubs would
otherwise collide with conftest.py's volttron-10-style stubs that the rest of
the suite relies on.
"""
import subprocess
import sys
import textwrap

_PROBE = textwrap.dedent("""
    import sys
    import types
    import importlib.metadata as metadata

    # No volttron / volttron-core distribution metadata is present.
    def _not_found(name):
        raise metadata.PackageNotFoundError(name)
    metadata.version = _not_found
    metadata.distribution = _not_found

    # Only the legacy volttron.platform.* API is present.
    agent_utils = types.ModuleType('volttron.platform.agent.utils')
    agent_utils.setup_logging = lambda *a, **k: None
    agent_utils.get_aware_utc_now = lambda: None
    agent_utils.parse_timestamp_string = lambda s: s
    for name in ('volttron', 'volttron.platform', 'volttron.platform.agent'):
        sys.modules.setdefault(name, types.ModuleType(name))
    sys.modules['volttron.platform.agent.utils'] = agent_utils

    if 'gevent' not in sys.modules:
        gevent = types.ModuleType('gevent')
        gevent.Timeout = type('Timeout', (Exception,), {})
        sys.modules['gevent'] = gevent

    import rt_control.modes.active
    import rt_control.modes.reactive
    import rt_control.modes.emergency
    print('IMPORT_OK')
""")


def _run_probe():
    return subprocess.run([sys.executable, '-c', _PROBE], capture_output=True, text=True)


def test_modes_import_without_volttron_distribution():
    result = _run_probe()
    assert result.returncode == 0, result.stderr
    assert 'IMPORT_OK' in result.stdout
