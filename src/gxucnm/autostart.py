import os
import shutil
import platform
import subprocess
from pathlib import Path

SYSTEM = platform.system()
PROJECT_DIR = Path(__file__).resolve().parent.parent.parent
UV = shutil.which("uv") or "uv"
_DEVNULL = subprocess.DEVNULL


def _run(cmd, *, check=True, **kwargs):
    subprocess.run(cmd, check=check, **kwargs)


# ── macOS ──────────────────────────────────────────────────────
_MACOS_PLIST_TEMPLATE = """<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>com.gxucnm.daemon</string>
    <key>ProgramArguments</key>
    <array>
        <string>{uv}</string>
        <string>run</string>
        <string>gxucnm</string>
        <string>daemon</string>
    </array>
    <key>WorkingDirectory</key>
    <string>{project_dir}</string>
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


def _install_macos():
    plist_path = Path.home() / "Library/LaunchAgents" / _MACOS_PLIST
    log_dir = Path.home() / "Library/Logs"
    log_dir.mkdir(parents=True, exist_ok=True)
    plist_path.parent.mkdir(parents=True, exist_ok=True)

    plist_path.write_text(
        _MACOS_PLIST_TEMPLATE.format(
            uv=UV, project_dir=PROJECT_DIR, log_dir=log_dir
        )
    )
    _run(["launchctl", "bootout", f"gui/{os.getuid()}/{_MACOS_SERVICE}"], check=False, stderr=_DEVNULL)
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
WorkingDirectory={project_dir}
ExecStart={uv} run gxucnm daemon
Restart=always
RestartSec=10

[Install]
WantedBy=default.target
"""


def _install_linux():
    unit_dir = Path.home() / ".config/systemd/user"
    unit_dir.mkdir(parents=True, exist_ok=True)
    unit_path = unit_dir / "gxucnm-daemon.service"
    unit_path.write_text(
        _LINUX_SERVICE_TEMPLATE.format(uv=UV, project_dir=PROJECT_DIR)
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
    '"cmd /c cd /d ""{project_dir}"" && ""{uv}"" run gxucnm daemon '
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
    vbs_path.write_text(
        _WIN_VBS_TEMPLATE.format(uv=UV, project_dir=PROJECT_DIR, log_dir=log_dir)
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
    print(f"✓ 自启动已安装并启动 → {path}")


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
