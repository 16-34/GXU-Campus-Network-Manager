# shellcheck shell=bash

_gxucnm_local_ip() {
    local ip=""

    if command -v ip >/dev/null 2>&1; then
        ip="$(ip route get 8.8.8.8 2>/dev/null | awk '{for (i=1; i<=NF; i++) if ($i == "src") {print $(i+1); exit}}')"
    fi

    if [ -z "$ip" ] && command -v route >/dev/null 2>&1; then
        ip="$(route get 8.8.8.8 2>/dev/null | awk '/interface:/{iface=$2} END{if (iface) print iface}' | xargs -I{} ipconfig getifaddr {} 2>/dev/null)"
    fi

    if [ -z "$ip" ]; then
        ip="$(hostname -I 2>/dev/null | awk '{print $1}')"
    fi

    if [ -z "$ip" ]; then
        ip="$(ifconfig 2>/dev/null | awk '/inet / && $2 !~ /^127\./ && $2 !~ /^169\.254\./ {print $2; exit}')"
    fi

    if [ -z "$ip" ]; then
        printf '无法自动获取IP，请手动检查网络接口\n' >&2
        return 1
    fi

    printf '%s\n' "$ip"
}

_gxucnm_request() {
    local url="$1"
    shift

    local tmp http_code
    tmp="$(mktemp "${TMPDIR:-/tmp}/gxucnm.XXXXXX")" || return 1
    http_code="$(curl -sS -G -o "$tmp" -w '%{http_code}' "$url" "$@")"
    local curl_status=$?

    if [ "$curl_status" -ne 0 ]; then
        rm -f "$tmp"
        printf -- '-1 \n'
        return 0
    fi

    printf '%s ' "$http_code"
    cat "$tmp"
    printf '\n'
    rm -f "$tmp"
}

_gxucnm_login() {
    local username="${GXUCNM_USERNAME:-}"
    local password="${GXUCNM_PASSWORD:-}"

    while [ "$#" -gt 0 ]; do
        case "$1" in
            -u|--username)
                username="$2"
                shift 2
                ;;
            -p|--password)
                password="$2"
                shift 2
                ;;
            *)
                printf '未知参数: %s\n' "$1" >&2
                return 2
                ;;
        esac
    done

    local local_ip
    local_ip="$(_gxucnm_local_ip)" || return 1

    _gxucnm_request \
        'http://172.17.0.2:801/eportal/portal/login' \
        --data-urlencode 'callback=dr1003' \
        --data-urlencode 'login_method=1' \
        --data-urlencode "user_account=$username" \
        --data-urlencode "user_password=$password" \
        --data-urlencode "wlan_user_ip=$local_ip" \
        --data-urlencode 'wlan_user_ipv6=' \
        --data-urlencode 'wlan_user_mac=000000000000' \
        --data-urlencode 'wlan_ac_ip=' \
        --data-urlencode 'wlan_ac_name=' \
        --data-urlencode 'jsVersion=4.2.1' \
        --data-urlencode 'terminal_type=1' \
        --data-urlencode 'lang=zh-cn' \
        --data-urlencode 'v=5574' \
        --data-urlencode 'lang=zh'
}

_gxucnm_logout() {
    _gxucnm_request 'http://172.17.0.2:801/eportal/portal/logout'
}

gxucnm() {
    local command="${1:-help}"
    [ "$#" -gt 0 ] && shift

    case "$command" in
        login)
            _gxucnm_login "$@"
            ;;
        logout)
            _gxucnm_logout "$@"
            ;;
        ip|get-local-ip|get_local_ip)
            _gxucnm_local_ip
            ;;
        help|-h|--help)
            cat <<'EOF'
用法:
  source ./gxucnm.sh
  gxucnm login [-u 学号] [-p 密码]
  gxucnm logout
  gxucnm ip

环境变量:
  GXUCNM_USERNAME
  GXUCNM_PASSWORD
EOF
            ;;
        *)
            printf '未知命令: %s\n' "$command" >&2
            printf '运行 gxucnm help 查看用法\n' >&2
            return 2
            ;;
    esac
}
