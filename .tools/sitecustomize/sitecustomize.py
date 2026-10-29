# Sandbox workaround for this machine (Windows + DSH restricted token).
#
# Python and pip create temp dirs with mode 0o700 and sometimes chmod them back to
# 0o700; the DSH sandbox token cannot write inside such dirs, so pip/venv/sdist
# builds fail with `PermissionError: [Errno 13]` or `WinError 5`.
#
# tools/dev_env.ps1 puts this directory on PYTHONPATH so every interpreter we run
# imports the shims below. Nothing here touches application code.

import os as _os

_orig_mkdir = _os.mkdir


def _mkdir(path, mode=0o777, *args, **kwargs):
    # Always create world-writable dirs: the sandbox token needs write access.
    return _orig_mkdir(path, 0o777, *args, **kwargs)


def _chmod(path, mode, *args, **kwargs):
    # No-op on purpose: chmod on Windows only toggles the read-only bit, and
    # tightening the ACL back to 0o700 is exactly what breaks the token.
    return None


_os.mkdir = _mkdir
_os.chmod = _chmod
