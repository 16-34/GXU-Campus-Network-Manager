import argparse

from src.GXUCampusNetworkManager import GXUCampusNetworkManager


def main():
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

    args = parser.parse_args()
    gxucnm = GXUCampusNetworkManager()

    if args.command is None:
        parser.print_help()
        return
    elif args.command == "info":
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
