import logging
import signal
from datetime import datetime
from threading import Event

from gxucnm.network import GXUCampusNetworkManager

PAUSE_START = 0
PAUSE_END = 7
CHECK_INTERVAL = 15
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
    stop_event = Event()
    pause = False

    def handle_stop(signum, frame):
        stop_event.set()

    def handle_toggle(signum, frame):
        nonlocal pause
        pause = not pause
        logger.info(f"手动{'暂停' if pause else '恢复'}")

    signal.signal(signal.SIGINT, handle_stop)
    signal.signal(signal.SIGTERM, handle_stop)
    signal.signal(signal.SIGUSR1, handle_toggle)

    logger.info(
        f"守护进程启动 — 检测间隔 {check_interval}s，重试 {retry_max} 次，失败冷却 {FAIL_COOLDOWN}s"
    )
    while not stop_event.is_set():
        if is_paused():
            now = datetime.now()
            resume = now.replace(hour=PAUSE_END, minute=0, second=0, microsecond=0)
            wait = int((resume - now).total_seconds())
            logger.info(f"工作日 0:00-{PAUSE_END}:00 暂停，{wait}s 后恢复")
            stop_event.wait(min(wait, 300))
            continue

        if pause:
            stop_event.wait(1)
            continue

        if gxucnm.test():
            stop_event.wait(check_interval)
            continue

        logger.warning("检测到断网，尝试重新登录")
        for attempt in range(1, retry_max + 1):
            status, content = gxucnm.login()
            logger.info(f"登录第 {attempt} 次: {status} {content}")
            if gxucnm.test():
                logger.info("网络已恢复")
                break
            if stop_event.wait(retry_interval):
                return
        else:
            logger.error(f"重试 {retry_max} 次后仍无法恢复，冷却 {FAIL_COOLDOWN}s")
            if stop_event.wait(FAIL_COOLDOWN):
                return
            continue

        stop_event.wait(check_interval)
