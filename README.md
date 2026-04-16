# GXU Campus Network Manager

广西大学校园网登录/注销 CLI 工具，支持断网自动重连。

## 安装

```bash
uv sync
```

## 配置

在项目根目录创建 `.env` 文件：

```
GXUCNM_USERNAME=你的学号
GXUCNM_PASSWORD=你的密码
```

也可以通过 CLI 参数手动传入凭据，优先级：CLI 参数 > 环境变量 > `.env` 文件。

## 用法

```bash
# 查看网络状态和本机 IP
uv run gxucnm info

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
```

### 守护模式参数

| 参数 | 说明 | 默认值 |
|------|------|--------|
| `-i` / `--interval` | 检测间隔（秒） | 30 |
| `-r` / `--retry` | 断网时最大重试次数 | 3 |
| `-w` / `--wait` | 重试等待间隔（秒） | 5 |

### 守护模式行为

- 每 30 秒检测一次网络连通性（小米 + 华为双端点，任一返回 204 即判定在线）
- 断网时自动使用已配置的凭据登录
- 重试全部失败后冷却 15 分钟再尝试
- 工作日（周一至周五）0:00–7:00 暂停检测
- 运行中发送 `SIGUSR1` 信号可手动暂停/恢复检测：

```bash
kill -USR1 <pid>
```

按 `Ctrl+C` 或发送 `SIGTERM` 正常退出守护进程。