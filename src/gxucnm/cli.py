import argparse
import logging
from pathlib import Path

from dotenv import load_dotenv
from gxucnm.network import GXUCampusNetworkManager
from gxucnm.daemon import run as daemon_run


def main():
    load_dotenv()
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
        default=30,
        help="检测间隔（秒），默认 30",
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

    args = parser.parse_args()

    if args.command is None:
        parser.print_help()
        return
    elif args.command == "daemon":
        logging.basicConfig(
            level=logging.INFO,
            format="%(asctime)s [%(levelname)s] %(message)s",
            datefmt="%H:%M:%S",
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
        status, content = gxucnm.login(args.username, args.password)
        print(status, content)
    elif args.command == "logout":
        status, content = gxucnm.logout()
        print(status, content)


if __name__ == "__main__":
    main()
