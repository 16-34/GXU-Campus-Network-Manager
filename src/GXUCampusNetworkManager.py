import requests
import socket
import os


class GXUCampusNetworkManager:
    @classmethod
    def login(cls, username="", password=""):
        """登录校园网"""
        username = username or os.getenv("GXUCNM_USERNAME", "")
        password = password or os.getenv("GXUCNM_PASSWORD", "")

        url = "http://172.17.0.2:801/eportal/portal/login"

        params = [
            ("callback", "dr1003"),
            ("login_method", "1"),
            ("user_account", username),
            ("user_password", password),
            ("wlan_user_ip", cls.get_local_ip()),
            ("wlan_user_ipv6", ""),
            ("wlan_user_mac", "000000000000"),
            ("wlan_ac_ip", ""),
            ("wlan_ac_name", ""),
            ("jsVersion", "4.2.1"),
            ("terminal_type", "1"),
            ("lang", "zh-cn"),
            ("v", "5574"),
            ("lang", "zh"),
        ]
        try:
            response = requests.get(url, params=params)
            return response.status_code, response.text
        except Exception:
            return -1

    @classmethod
    def logout(cls):
        """注销"""
        try:
            url = "http://172.17.0.2:801/eportal/portal/logout"
            response = requests.get(url)
            return response.status_code, response.text
        except Exception:
            return -1

    @classmethod
    def test(cls):
        """测试网络通断"""
        try:
            return (
                requests.get(
                    "http://connect.rom.miui.com/generate_204",
                    timeout=0.5,
                ).status_code
                == 204
            )
        except Exception:
            return False

    @classmethod
    def get_local_ip(cls):
        """动态获取本机局域网IPv4地址"""
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
                s.connect(("8.8.8.8", 80))
                return s.getsockname()[0]
        except Exception:
            try:
                hostname = socket.gethostname()
                ip_list = socket.getaddrinfo(hostname, None)
                for ip in ip_list:
                    if ip[0] == socket.AF_INET:
                        current_ip = ip[4][0]
                        if not current_ip.startswith(
                            "127."
                        ) and not current_ip.startswith("169.254"):
                            return current_ip
                raise RuntimeError("未找到有效局域网IP")
            except Exception as e:
                raise RuntimeError(f"无法自动获取IP，请手动填写: {str(e)}")


if __name__ == "__main__":
    gxucnm = GXUCampusNetworkManager()
    print(gxucnm.get_local_ip())
    print(gxucnm.test())
    # print(gxucn.login())
    # print(gxucn.test())
