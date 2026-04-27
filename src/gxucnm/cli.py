import argparse
import getpass
import logging
import os
import sys

from dotenv import load_dotenv, set_key
from gxucnm.network import GXUCampusNetworkManager
from gxucnm.daemon import run as daemon_run
from gxucnm import autostart


def _resolve_credentials(cli_user="", cli_pass=""):
    """解析凭据：CLI → 环境变量 → .env → 交互输入"""
    user = cli_user or os.getenv("GXUCNM_USERNAME", "")
    password = cli_pass or os.getenv("GXUCNM_PASSWORD", "")

    if not user:
        user = input("校园网账号: ").strip()
    if not password:
        password = getpass.getpass("校园网密码: ")

    if user and password:
        env_path = str(autostart.config_dir() / ".env")
        set_key(env_path, "GXUCNM_USERNAME", user)
        set_key(env_path, "GXUCNM_PASSWORD", password)
        os.environ["GXUCNM_USERNAME"] = user
        os.environ["GXUCNM_PASSWORD"] = password
        print(f"✓ 凭据已保存至 {env_path}")

    return user, password


def main():
    load_dotenv()
    load_dotenv(autostart.config_dir() / ".env")
    parser = argparse.ArgumentParser(description="GXU Campus Network Manager")
    subparsers = parser.add_subparsers(dest="command")

    subparsers.add_parser("info", help="获取网络信息")

    login_parser = subparsers.add_parser("login", help="登录校园网")
    login_parser.add_argument(
        "-u", "--username", type=str, default="", help="校园网账户用户名"
    )
    login_parser.add_argument(
        "-p", "--password", type=str, default="", help="校园网账户密码"
    )

    subparsers.add_parser("logout", help="注销")

    daemon_parser = subparsers.add_parser("daemon", help="后台守护进程，断网自动登录")
    daemon_parser.add_argument(
        "-i",
        "--interval",
        type=int,
        default=15,
        help="检测间隔（秒），默认 15",
    )
    daemon_parser.add_argument(
        "-r",
        "--retry",
        type=int,
        default=3,
        help="断网时最大重试次数，默认 3",
    )
    daemon_parser.add_argument(
        "-w",
        "--wait",
        type=int,
        default=5,
        help="重试等待间隔（秒），默认 5",
    )

    config_parser = subparsers.add_parser("config", help="管理凭据")
    config_sub = config_parser.add_subparsers(dest="config_action")
    set_parser = config_sub.add_parser("set", help="设置凭据")
    set_parser.add_argument(
        "-u", "--username", type=str, default="", help="校园网账户用户名"
    )
    set_parser.add_argument(
        "-p", "--password", type=str, default="", help="校园网账户密码"
    )

    autostart_parser = subparsers.add_parser("autostart", help="管理开机自启动")
    autostart_sub = autostart_parser.add_subparsers(dest="autostart_action")
    autostart_sub.add_parser("install", help="安装自启动")
    autostart_sub.add_parser("uninstall", help="卸载自启动")
    logs_parser = autostart_sub.add_parser("logs", help="查看守护进程日志")
    logs_parser.add_argument(
        "-n", "--lines", type=int, default=50, help="显示最近 N 行（默认 50）"
    )
    logs_parser.add_argument(
        "-f", "--follow", action="store_true", help="实时跟踪日志"
    )

    args = parser.parse_args()

    if args.command is None:
        parser.print_help()
        return
    elif args.command == "config":
        if args.config_action == "set":
            _resolve_credentials(args.username, args.password)
        else:
            user = os.getenv("GXUCNM_USERNAME", "")
            print(f"用户名: {'(已设置)' if user else '(未设置)'}")
            print(f"密码:   {'(已设置)' if os.getenv('GXUCNM_PASSWORD', '') else '(未设置)'}")
            print(f"配置文件: {autostart.config_dir() / '.env'}")
        return
    elif args.command == "autostart":
        if args.autostart_action == "install":
            autostart.install()
        elif args.autostart_action == "uninstall":
            autostart.uninstall()
        elif args.autostart_action == "logs":
            autostart.logs(follow=args.follow, lines=args.lines)
        else:
            autostart_parser.print_help()
        return
    elif args.command == "daemon":
        _resolve_credentials()
        logging.basicConfig(
            level=logging.INFO,
            format="%(asctime)s [%(levelname)s] %(message)s",
            datefmt="%H:%M:%S",
            stream=sys.stdout,
        )
        daemon_run(
            check_interval=args.interval,
            retry_interval=args.wait,
            retry_max=args.retry,
        )
        return

    gxucnm = GXUCampusNetworkManager()
    if args.command == "info":
        print("网络状态: \t", "已连接" if gxucnm.test() else "未连接")
        print("本地 IP 地址: \t", gxucnm.get_local_ip())
    elif args.command == "login":
        username, password = _resolve_credentials(args.username, args.password)
        status, content = gxucnm.login(username, password)
        print(status, content)
    elif args.command == "logout":
        status, content = gxucnm.logout()
        print(status, content)


if __name__ == "__main__":
    main()
