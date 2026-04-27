# GXU Campus Network Manager

广西大学校园网登录/注销 CLI 工具，支持断网自动重连。

## 安装

```bash
# 开发/本地使用
uv sync

# 全局安装（通过 pipx）
pipx install .
```
安装后可直接使用 `gxucnm` 命令，无需 `uv run` 前缀。

## 配置

凭据加载优先级：**CLI 参数 > 环境变量 > 配置文件**

配置文件 `.env` 可放在两个位置（任一即可）：
- 项目根目录（开发时）
- **全局配置目录**（推荐，pipx 安装后唯一可用位置）：

| 系统 | 配置目录 |
|------|----------|
| macOS | `~/Library/Application Support/gxucnm/.env` |
| Linux | `~/.config/gxucnm/.env` |
| Windows | `%APPDATA%\gxucnm\.env` |

```
GXUCNM_USERNAME=你的学号
GXUCNM_PASSWORD=你的密码
```

## 用法

```bash
# 查看网络状态和本机 IP
uv run gxucnm info

# 设置凭据（交互式）
uv run gxucnm config set

# 设置凭据（参数式）
uv run gxucnm config set -u 学号 -p 密码

# 查看当前凭据状态
uv run gxucnm config

# 登录（使用 .env 或环境变量中的凭据）
uv run gxucnm login

# 手动指定凭据登录
uv run gxucnm login -u 学号 -p 密码

# 注销
uv run gxucnm logout

# 守护模式：自动检测断网并重连
uv run gxucnm daemon

# 自定义守护参数
uv run gxucnm daemon -i 60 -r 5 -w 10

# 安装开机自启动（macOS / Linux / Windows）
uv run gxucnm autostart install

# 卸载开机自启动
uv run gxucnm autostart uninstall

# 查看守护进程日志（最近 50 行）
uv run gxucnm autostart logs

# 实时跟踪日志
uv run gxucnm autostart logs -f
```

### 守护模式参数

| 参数 | 说明 | 默认值 |
|------|------|--------|
| `-i` / `--interval` | 检测间隔（秒） | 15 |
| `-r` / `--retry` | 断网时最大重试次数 | 3 |
| `-w` / `--wait` | 重试等待间隔（秒） | 5 |

### 守护模式行为

- 每 15 秒检测一次网络连通性（小米 + 华为双端点，任一返回 204 即判定在线）
- 断网时自动使用已配置的凭据登录
- 重试全部失败后冷却 15 分钟再尝试
- 工作日（周一至周五）0:00–7:00 暂停检测
- 运行中发送 `SIGUSR1` 信号可手动暂停/恢复检测：

```bash
kill -USR1 <pid>
```

按 `Ctrl+C` 或发送 `SIGTERM` 正常退出守护进程。

### 开机自启动

`uv run gxucnm autostart install` 一键安装，自动识别操作系统和运行方式：

| 系统 | 实现方式 |
|------|----------|
| macOS | LaunchAgent（`~/Library/LaunchAgents/`） |
| Linux | systemd 用户单元（`~/.config/systemd/user/`） |
| Windows | VBS 启动脚本（启动文件夹） |

安装时会自动检测当前运行方式，输出 `[源码 (uv run)]` 或 `[已安装 (pipx/pip)]`。

使用 `uninstall` 即可移除：`uv run gxucnm autostart uninstall`

检查运行状态与日志（也可用统一命令 `uv run gxucnm autostart logs [-f]`）：

| 系统 | 查看状态 | 查看日志 |
|------|----------|----------|
| macOS | `launchctl list \| grep gxucnm` | `tail -f ~/Library/Logs/com.gxucnm.daemon.log` |
| Linux | `systemctl --user status gxucnm-daemon` | `journalctl --user -u gxucnm-daemon -f` |
| Windows | 任务管理器查看 `uv` 进程 | `%LOCALAPPDATA%\gxucnm\gxucnm-daemon.log` |