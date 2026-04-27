import os
import shutil
import platform
import subprocess
import time
from pathlib import Path

SYSTEM = platform.system()
PROJECT_DIR = Path(__file__).resolve().parent.parent.parent
UV = shutil.which("uv") or "uv"
_DEVNULL = subprocess.DEVNULL


def _run(cmd, *, check=True, **kwargs):
    subprocess.run(cmd, check=check, **kwargs)


# ── 配置目录 ────────────────────────────────────────────────────
def config_dir():
    if SYSTEM == "Darwin":
        return Path.home() / "Library/Application Support/gxucnm"
    elif SYSTEM == "Windows":
        return Path(os.environ["APPDATA"]) / "gxucnm"
    else:
        xdg = os.environ.get("XDG_CONFIG_HOME")
        return Path(xdg) / "gxucnm" if xdg else Path.home() / ".config/gxucnm"


_CONFIG = config_dir()
_CONFIG.mkdir(parents=True, exist_ok=True)


# ── 执行方式检测：源码模式 vs pipx/pip 安装模式 ─────────────────
def _detect_exec():
    """检测运行模式，返回 (daemon_cmd, work_dir)。
    源码模式：uv run gxucnm daemon，工作目录为项目根目录
    安装模式：gxucnm daemon，工作目录为 HOME
    """
    pyproject = PROJECT_DIR / "pyproject.toml"
    if pyproject.exists():
        try:
            content = pyproject.read_text()
            if "gxucnm" in content:
                return (UV, "run", "gxucnm"), str(PROJECT_DIR)
        except Exception:
            pass
    gxucnm = shutil.which("gxucnm") or "gxucnm"
    return (gxucnm,), str(Path.home())


_DAEMON_CMD, _WORK_DIR = _detect_exec()
_IS_SOURCE = len(_DAEMON_CMD) > 1  # uv run gxucnm → 3 tokens；gxucnm → 1 token


# ── macOS ──────────────────────────────────────────────────────
_MACOS_PLIST_TEMPLATE = """<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>com.gxucnm.daemon</string>
    <key>ProgramArguments</key>
    <array>
{program_args}    </array>
    <key>WorkingDirectory</key>
    <string>{work_dir}</string>
    <key>RunAtLoad</key>
    <true/>
    <key>KeepAlive</key>
    <true/>
    <key>StandardOutPath</key>
    <string>{log_dir}/com.gxucnm.daemon.log</string>
    <key>StandardErrorPath</key>
    <string>{log_dir}/com.gxucnm.daemon.log</string>
</dict>
</plist>"""

_MACOS_SERVICE = "com.gxucnm.daemon"
_MACOS_PLIST = "com.gxucnm.daemon.plist"


def _macos_plist_xml():
    args_lines = ""
    for arg in _DAEMON_CMD + ("daemon",):
        args_lines += f"        <string>{arg}</string>\n"
    log_dir = Path.home() / "Library/Logs"
    return _MACOS_PLIST_TEMPLATE.format(
        program_args=args_lines, work_dir=_WORK_DIR, log_dir=log_dir
    )


def _install_macos():
    log_dir = Path.home() / "Library/Logs"
    log_dir.mkdir(parents=True, exist_ok=True)
    plist_path = Path.home() / "Library/LaunchAgents" / _MACOS_PLIST
    plist_path.parent.mkdir(parents=True, exist_ok=True)
    plist_path.write_text(_macos_plist_xml())
    _run(["launchctl", "bootout", f"gui/{os.getuid()}/{_MACOS_SERVICE}"], check=False, stderr=_DEVNULL)
    time.sleep(0.3)
    try:
        _run(["launchctl", "bootstrap", f"gui/{os.getuid()}", str(plist_path)])
    except subprocess.CalledProcessError:
        time.sleep(0.5)
        _run(["launchctl", "bootstrap", f"gui/{os.getuid()}", str(plist_path)])
    return plist_path


def _uninstall_macos():
    _run(["launchctl", "bootout", f"gui/{os.getuid()}/{_MACOS_SERVICE}"], check=False, stderr=_DEVNULL)
    (Path.home() / "Library/LaunchAgents" / _MACOS_PLIST).unlink(missing_ok=True)


# ── Linux ──────────────────────────────────────────────────────
_LINUX_SERVICE_TEMPLATE = """[Unit]
Description=GXU Campus Network Manager Daemon
After=network-online.target
Wants=network-online.target

[Service]
Type=simple
WorkingDirectory={work_dir}
ExecStart=env "GXUCNM_CONFIG_DIR={config_dir}" {exec_cmd}
Restart=always
RestartSec=10

[Install]
WantedBy=default.target
"""


def _install_linux():
    unit_dir = Path.home() / ".config/systemd/user"
    unit_dir.mkdir(parents=True, exist_ok=True)
    unit_path = unit_dir / "gxucnm-daemon.service"
    exec_cmd = " ".join(_DAEMON_CMD + ("daemon",))
    unit_path.write_text(
        _LINUX_SERVICE_TEMPLATE.format(
            exec_cmd=exec_cmd, work_dir=_WORK_DIR, config_dir=_CONFIG
        )
    )
    _run(["systemctl", "--user", "daemon-reload"])
    _run(["systemctl", "--user", "enable", "--now", "gxucnm-daemon"])
    return unit_path


def _uninstall_linux():
    _run(["systemctl", "--user", "disable", "--now", "gxucnm-daemon"], check=False)
    (Path.home() / ".config/systemd/user/gxucnm-daemon.service").unlink(missing_ok=True)
    _run(["systemctl", "--user", "daemon-reload"])


# ── Windows ────────────────────────────────────────────────────
_WIN_VBS_TEMPLATE = (
    'CreateObject("Wscript.Shell").Run '
    '"cmd /c set GXUCNM_CONFIG_DIR={config_dir} && '
    'cd /d ""{work_dir}"" && {exec_cmd} '
    '>> ""{log_dir}\\gxucnm-daemon.log"" 2>&1", 0, False'
)


def _install_windows():
    log_dir = Path(os.environ["LOCALAPPDATA"]) / "gxucnm"
    log_dir.mkdir(parents=True, exist_ok=True)
    startup = (
        Path(os.environ["APPDATA"])
        / "Microsoft/Windows/Start Menu/Programs/Startup"
    )
    vbs_path = startup / "gxucnm-daemon.vbs"
    exec_cmd = " ".join(f'""{a}""' for a in _DAEMON_CMD + ("daemon",))
    vbs_path.write_text(
        _WIN_VBS_TEMPLATE.format(
            exec_cmd=exec_cmd, work_dir=_WORK_DIR,
            config_dir=_CONFIG, log_dir=log_dir,
        )
    )
    return vbs_path


def _uninstall_windows():
    startup = (
        Path(os.environ["APPDATA"])
        / "Microsoft/Windows/Start Menu/Programs/Startup"
    )
    (startup / "gxucnm-daemon.vbs").unlink(missing_ok=True)


# ── Public API ─────────────────────────────────────────────────
_INSTALLERS = {
    "Darwin": (_install_macos, _uninstall_macos),
    "Linux": (_install_linux, _uninstall_linux),
    "Windows": (_install_windows, _uninstall_windows),
}


def install():
    if SYSTEM not in _INSTALLERS:
        raise RuntimeError(f"不支持的操作系统: {SYSTEM}")
    path = _INSTALLERS[SYSTEM][0]()
    mode = "源码 (uv run)" if _IS_SOURCE else "已安装 (pipx/pip)"
    print(f"✓ 自启动已安装并启动 [{mode}] → {path}")


def uninstall():
    if SYSTEM not in _INSTALLERS:
        raise RuntimeError(f"不支持的操作系统: {SYSTEM}")
    _INSTALLERS[SYSTEM][1]()
    print("✓ 自启动已卸载")


# ── 日志查看 ────────────────────────────────────────────────────
_LOGS = {
    "Darwin": lambda: Path.home() / "Library/Logs/com.gxucnm.daemon.log",
    "Linux": None,
    "Windows": lambda: Path(os.environ["LOCALAPPDATA"]) / "gxucnm" / "gxucnm-daemon.log",
}


def logs(follow=False, lines=50):
    log_path_getter = _LOGS.get(SYSTEM)
    if log_path_getter is None:
        if SYSTEM == "Linux":
            cmd = ["journalctl", "--user", "-u", "gxucnm-daemon"]
            if follow:
                cmd.append("-f")
            else:
                cmd.extend(["-n", str(lines)])
            _run(cmd)
        else:
            raise RuntimeError(f"不支持的操作系统: {SYSTEM}")
    else:
        log_path = log_path_getter()
        if not log_path.exists():
            print(f"日志文件不存在: {log_path}")
            return
        if follow:
            try:
                _run(["tail", "-f", str(log_path)])
            except KeyboardInterrupt:
                pass
        else:
            text = log_path.read_text(encoding="utf-8", errors="replace")
            for line in text.splitlines()[-lines:]:
                print(line)
