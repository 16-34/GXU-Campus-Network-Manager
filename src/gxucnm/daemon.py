import logging
import signal
import time
from datetime import datetime

from gxucnm.network import GXUCampusNetworkManager

PAUSE_START = 0
PAUSE_END = 7
CHECK_INTERVAL = 30
RETRY_INTERVAL = 5
RETRY_MAX = 3
FAIL_COOLDOWN = 15 * 60

logger = logging.getLogger("gxucnm.daemon")


def is_paused():
    now = datetime.now()
    return now.weekday() < 5 and PAUSE_START <= now.hour < PAUSE_END


def run(
    check_interval=CHECK_INTERVAL, retry_interval=RETRY_INTERVAL, retry_max=RETRY_MAX
):
    gxucnm = GXUCampusNetworkManager()
    running = True
    paused = False

    def stop(signum, frame):
        nonlocal running
        running = False

    def toggle_pause(signum, frame):
        nonlocal paused
        paused = not paused
        logger.info(f"手动{'暂停' if paused else '恢复'}")

    signal.signal(signal.SIGINT, stop)
    signal.signal(signal.SIGTERM, stop)
    signal.signal(signal.SIGUSR1, toggle_pause)

    logger.info(
        f"守护进程启动 — 检测间隔 {check_interval}s，重试 {retry_max} 次，失败冷却 {FAIL_COOLDOWN}s"
    )
    while running:
        if is_paused():
            now = datetime.now()
            resume = now.replace(hour=PAUSE_END, minute=0, second=0, microsecond=0)
            wait = int((resume - now).total_seconds())
            logger.info(f"工作日 0:00-{PAUSE_END}:00 暂停，{wait}s 后恢复")
            time.sleep(min(wait, 300))
            continue

        if paused:
            time.sleep(1)
            continue

        if gxucnm.test():
            time.sleep(check_interval)
            continue

        logger.warning("检测到断网，尝试重新登录")
        for attempt in range(1, retry_max + 1):
            status, content = gxucnm.login()
            logger.info(f"登录第 {attempt} 次: {status} {content}")
            if gxucnm.test():
                logger.info("网络已恢复")
                break
            time.sleep(retry_interval)
        else:
            logger.error(f"重试 {retry_max} 次后仍无法恢复，冷却 {FAIL_COOLDOWN}s")
            time.sleep(FAIL_COOLDOWN)
            continue

        time.sleep(check_interval)
