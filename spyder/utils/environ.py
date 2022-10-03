# -*- coding: utf-8 -*-
#
# Copyright © Spyder Project Contributors
# Licensed under the terms of the MIT License
# (see spyder/__init__.py for details)

"""
Environment variable utilities.
"""

# Standard library imports
import os

# Third party imports
from qtpy.QtWidgets import QMessageBox
try:
    import winreg
except Exception:
    pass

# Local imports
from spyder.config.base import _
from spyder.widgets.collectionseditor import CollectionsEditor
from spyder.utils.icon_manager import ima
from spyder.utils.programs import run_shell_command


def envdict2listdict(envdict):
    """Dict --> Dict of lists"""
    sep = os.path.pathsep
    for key, val in envdict.items():
        if isinstance(val, str) and sep in val:
            envdict[key] = [path.strip() for path in val.split(sep)]
    return envdict


def listdict2envdict(listdict):
    """Dict of lists --> Dict"""
    for key, val in listdict.items():
        if isinstance(val, list):
            listdict[key] = os.path.pathsep.join(val)
    return listdict


def get_user_environment_variables():
    """
    Get user environment variables from a subprocess.

    Returns
    -------
    env_var : dict
        Key-value pairs of environment variables.
    """
    if os.name == 'nt':
        cmd = "set"
    else:
        cmd = "printenv"
    proc = run_shell_command(cmd)
    stdout, stderr = proc.communicate()
    res = stdout.decode().strip().split(os.linesep)
    env_var = {}
    for kv in res:
        k, v = kv.split('=', 1)
        env_var[k] = v

    return env_var


def get_user_env():
    """Return current user environment variables with parsed values"""
    env_dict = get_user_environment_variables()
    return envdict2listdict(env_dict)


def set_user_env(env, parent=None):
    """Set HKCU (current user) environment variables"""
    if os.name != 'nt':
        raise NotImplementedError("Not implemented for %s platforms", os.name)

    reg = listdict2envdict(env)
    types = dict()
    key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, "Environment")
    for name in reg:
        try:
            _x, types[name] = winreg.QueryValueEx(key, name)
        except WindowsError:
            types[name] = winreg.REG_EXPAND_SZ
    key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, "Environment", 0,
                         winreg.KEY_SET_VALUE)
    for name in reg:
        winreg.SetValueEx(key, name, 0, types[name], reg[name])
    try:
        from win32gui import SendMessageTimeout
        from win32con import (HWND_BROADCAST, WM_SETTINGCHANGE,
                              SMTO_ABORTIFHUNG)
        SendMessageTimeout(HWND_BROADCAST, WM_SETTINGCHANGE, 0,
                           "Environment", SMTO_ABORTIFHUNG, 5000)
    except Exception:
        QMessageBox.warning(
            parent, _("Warning"),
            _("Module <b>pywin32 was not found</b>.<br>"
              "Please restart this Windows <i>session</i> "
              "(not the computer) for changes to take effect.")
        )


def clean_env(env_vars):
    """
    Remove non-ascii entries from a dictionary of environments variables.

    The values will be converted to strings or bytes (on Python 2). If an
    exception is raised, an empty string will be used.
    """
    new_env_vars = env_vars.copy()
    for key, var in env_vars.items():
        new_env_vars[key] = str(var)

    return new_env_vars


class RemoteEnvDialog(CollectionsEditor):
    """Remote process environment variables dialog."""

    def __init__(self, environ, parent=None,
                 title=_("Environment variables"), readonly=True):
        super().__init__(parent)
        try:
            self.setup(
                envdict2listdict(environ),
                title=title,
                readonly=readonly,
                icon=ima.icon('environ')
            )
        except Exception as e:
            QMessageBox.warning(
                parent,
                _("Warning"),
                _("An error occurred while trying to show your "
                  "environment variables. The error was<br><br>"
                  "<tt>{0}</tt>").format(e),
                QMessageBox.Ok
            )


class EnvDialog(RemoteEnvDialog):
    """Environment variables Dialog"""

    def __init__(self, parent=None):
        RemoteEnvDialog.__init__(self, dict(os.environ), parent=parent)


class UserEnvDialog(RemoteEnvDialog):
    """User Environment Variables Viewer/Editor"""

    def __init__(self, parent=None):
        title = _("User Environment variables")
        readonly = True
        if os.name == 'nt':
            title = _(r"HKEY_CURRENT_USER\Environment")
            readonly = False

        super().__init__(get_user_env(), parent, title, readonly)

        if os.name == 'nt':
            if parent is None:
                parent = self
            QMessageBox.warning(
                parent, _("Warning"),
                _("If you accept changes, "
                  "this will modify the current user environment "
                  "variables directly <b>in Windows registry</b>. "
                  "Use it with precautions, at your own risks.<br>"
                  "<br>Note that for changes to take effect, you will "
                  "need to restart the parent process of this applica"
                  "tion (simply restart Spyder if you have executed it "
                  "from a Windows shortcut, otherwise restart any "
                  "application from which you may have executed it, "
                  "like <i>Python(x,y) Home</i> for example)")
            )

    def accept(self):
        """Reimplement Qt method"""
        if os.name == 'nt':
            set_user_env(listdict2envdict(self.get_value()), parent=self)
        super().accept()


def test():
    """Run Windows environment variable editor"""
    import sys
    from spyder.utils.qthelpers import qapplication
    _ = qapplication()
    dlg = UserEnvDialog()
    dlg.show()
    sys.exit(dlg.exec())


if __name__ == "__main__":
    test()
