#!/usr/bin/env python3
"""
GLM Coding Plan 自动抢购脚本
智谱AI编程套餐抢购工具

用法:
    python grab_glm_coding_plan.py          # 单次抢购
    python grab_glm_coding_plan.py --daemon  # 守护模式（每日定时）
    python grab_glm_coding_plan.py --test   # 测试模式
"""

import os
import sys
import json
import time
import random
import signal
import argparse
from datetime import datetime, timedelta
from typing import Optional, Dict, Any

# 尝试导入可选依赖
try:
    import requests
except ImportError:
    requests = None

try:
    import httpx
except ImportError:
    httpx = None

try:
    from apscheduler.schedulers.blocking import BlockingScheduler
    from apscheduler.triggers.cron import CronTrigger
except ImportError:
    scheduler = None


# ==================== 配置 ====================
# 加载用户配置
CONFIG_FILE = os.path.join(os.path.dirname(__file__), "config.py")
# Cookie 持久化文件（exe 模式下保存到用户目录）
COOKIE_FILE = os.path.join(os.path.expanduser("~"), ".glm_coding_plan_cookie")

def load_config() -> Dict[str, Any]:
    """加载配置"""
    config = {
        "cookie": os.getenv("ZHIPU_COOKIE", ""),
        "feishu_webhook": os.getenv("FEISHU_WEBHOOK", ""),
        "feishu_user_id": os.getenv("FEISHU_USER_ID", ""),
        "grab_hour": 10,
        "grab_minute": 0,
        "pre_start_seconds": 30,
        "retry_interval": 1,
        "max_retries": 300,
        "plan_type": "lite",
        "auto_renew": True,
        "ic_code": "JO7VUQL6WC",  # 推广邀请码（写死在 exe 中）
        "referral_url": "https://www.bigmodel.cn/glm-coding",
    }

    # 尝试从 config.py 加载
    if os.path.exists(CONFIG_FILE):
        with open(CONFIG_FILE, "r") as f:
            content = f.read()
            # 简单解析 config.py
            for line in content.split("\n"):
                line = line.strip()
                if not line or line.startswith("#") or "=" not in line:
                    continue
                try:
                    key, value = line.split("=", 1)
                    key = key.strip()
                    value = value.strip().strip('"\'')
                    if key == "COOKIE":
                        config["cookie"] = value or config["cookie"]
                    elif key == "FEISHU_WEBHOOK":
                        config["feishu_webhook"] = value
                    elif key == "FEISHU_USER_ID":
                        config["feishu_user_id"] = value
                    elif key == "GRAB_HOUR":
                        config["grab_hour"] = int(value)
                    elif key == "GRAB_MINUTE":
                        config["grab_minute"] = int(value)
                    elif key == "PRE_START_SECONDS":
                        config["pre_start_seconds"] = int(value)
                    elif key == "RETRY_INTERVAL":
                        config["retry_interval"] = int(value)
                    elif key == "MAX_RETRIES":
                        config["max_retries"] = int(value)
                    elif key == "PLAN_TYPE":
                        config["plan_type"] = value
                    elif key == "AUTO_RENEW":
                        config["auto_renew"] = value.lower() == "true"
                except Exception:
                    pass

    # 尝试从持久化 Cookie 文件加载（exe 模式下）
    if not config["cookie"] and os.path.exists(COOKIE_FILE):
        with open(COOKIE_FILE, "r") as f:
            saved_cookie = f.read().strip()
            if saved_cookie:
                config["cookie"] = saved_cookie

    return config


def save_cookie_to_file(cookie: str):
    """保存 Cookie 到文件（持久化）"""
    try:
        with open(COOKIE_FILE, "w") as f:
            f.write(cookie)
    except Exception:
        pass


def prompt_for_cookie() -> str:
    """交互式提示用户输入 Cookie"""
    print("\n" + "=" * 50)
    print("🔑 首次使用需要配置智谱AI Cookie")
    print("=" * 50)
    print()
    print("📋 获取 Cookie 方法：")
    print("   1. 登录 https://bigmodel.cn")
    print("   2. 按 F12 打开开发者工具")
    print("   3. 切换到 Network（网络）标签")
    print("   4. 任意点击一个请求，复制 Request Headers 中的 Cookie")
    print()
    print("   或者在网页版控制台执行：document.cookie")
    print()
    print("-" * 50)
    cookie = input("请粘贴 Cookie（输入完按回车）:\n>").strip()
    return cookie


def prompt_for_mode() -> int:
    """交互式选择抢购模式，返回模式编号"""
    print("\n" + "=" * 50)
    print("🕹️  选择抢购模式")
    print("=" * 50)
    print()
    print("  [1] 📌 单次抢购")
    print("       等待抢购时间到达，一次性尝试抢购买到为止")
    print()
    print("  [2] 🔄 守护模式")
    print("       后台持续运行，每天 10:00 自动抢购")
    print()
    print("  [3] 🧪 测试模式")
    print("       立即尝试抢购（不付款），测试脚本是否正常")
    print()
    print("-" * 50)
    while True:
        choice = input("请输入选项 [1/2/3](默认1): ").strip()
        if choice == "":
            choice = "1"
        if choice in ("1", "2", "3"):
            return int(choice)
        print("⚠️ 无效选项，请输入 1、2 或 3")


# ==================== API 配置 ====================
API_BASE = "https://bigmodel.cn"
API_SUBMIT_ORDER = f"{API_BASE}/api/glm-coding-plan/order"
API_CHECK_STOCK = f"{API_BASE}/api/glm-coding-plan/stock"
API_USER_INFO = f"{API_BASE}/api/user/info"


# ==================== 通知模块 ====================
def send_feishu_notification(webhook: str, user_id: str, message: str):
    """发送飞书通知"""
    if not webhook:
        print(f"[通知] {message}")
        return
    
    try:
        import requests
        payload = {
            "msg_type": "text",
            "content": {"text": message}
        }
        if user_id:
            payload["at"] = {"at_user_ids": [user_id]}
        
        requests.post(webhook, json=payload, timeout=10)
    except Exception as e:
        print(f"[通知失败] {e}")


def notify_success(config: Dict, order_info: Dict):
    """抢购成功通知"""
    msg = f"""🎉 GLM Coding Plan 抢购成功！
━━━━━━━━━━━━━━━
📦 套餐：{config['plan_type'].upper()}
⏰ 时间：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
🆔 订单号：{order_info.get('order_id', 'N/A')}
━━━━━━━━━━━━━━━
✅ 请前往智谱AI确认订单"""
    
    send_feishu_notification(
        config["feishu_webhook"],
        config["feishu_user_id"],
        msg
    )


def notify_failure(config: Dict, reason: str, retry_count: int):
    """抢购失败通知"""
    msg = f"""❌ GLM Coding Plan 抢购失败
━━━━━━━━━━━━━━━
📋 原因：{reason}
🔄 重试次数：{retry_count}
⏰ 时间：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
━━━━━━━━━━━━━━━
💡 提示：配额可能已售罄，请明日再试"""
    
    send_feishu_notification(
        config["feishu_webhook"],
        config["feishu_user_id"],
        msg
    )


# ==================== Cookie管理 ====================
def validate_cookie(cookie: str) -> bool:
    """验证Cookie是否有效"""
    if not cookie:
        return False
    
    # 简单检查Cookie格式
    required_keys = ["token", "uid"]
    return any(k in cookie.lower() for k in required_keys)


def refresh_cookie_if_needed(config: Dict) -> str:
    """检查并刷新Cookie"""
    # 实际实现可能需要调用智谱的刷新接口
    # 这里仅做基础验证
    if not validate_cookie(config["cookie"]):
        raise ValueError("Cookie无效，请重新获取！")
    return config["cookie"]


# ==================== 核心功能 ====================
def check_stock(config: Dict) -> Dict[str, Any]:
    """检查套餐库存"""
    headers = {
        "Cookie": config["cookie"],
        "Content-Type": "application/json",
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
    }
    
    try:
        if requests:
            resp = requests.get(API_CHECK_STOCK, headers=headers, timeout=10)
        elif httpx:
            resp = httpx.get(API_CHECK_STOCK, headers=headers, timeout=10)
        else:
            raise Exception("请安装 requests 或 httpx")
        
        if resp.status_code == 200:
            return resp.json()
        else:
            return {"available": False, "reason": f"HTTP {resp.status_code}"}
    except Exception as e:
        return {"available": False, "reason": str(e)}


def submit_order(config: Dict) -> Dict[str, Any]:
    """提交订单"""
    # 构建推广链接 Referer
    referral_url = config.get("referral_url", "")
    ic_code = config.get("ic_code", "")
    if referral_url and ic_code:
        referer = f"{referral_url}?ic={ic_code}"
    elif referral_url:
        referer = referral_url
    else:
        referer = "https://bigmodel.cn/console/coding"

    headers = {
        "Cookie": config["cookie"],
        "Content-Type": "application/json",
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
        "Referer": referer
    }

    payload = {
        "plan_type": config["plan_type"],
        "auto_renew": config["auto_renew"],
        "timestamp": int(time.time() * 1000)
    }

    # 如果有推广码，添加到 payload
    if ic_code:
        payload["ic"] = ic_code
    
    try:
        if requests:
            resp = requests.post(API_SUBMIT_ORDER, headers=headers, json=payload, timeout=10)
        elif httpx:
            resp = httpx.post(API_SUBMIT_ORDER, headers=headers, json=payload, timeout=10)
        else:
            raise Exception("请安装 requests 或 httpx")
        
        result = resp.json() if resp.text else {}
        
        if resp.status_code == 200:
            if result.get("success") or result.get("code") == 0:
                return {
                    "success": True,
                    "order_id": result.get("order_id", f"ORD_{int(time.time())}"),
                    "message": result.get("message", "下单成功")
                }
            else:
                return {
                    "success": False,
                    "reason": result.get("message", result.get("msg", "下单失败"))
                }
        else:
            return {
                "success": False,
                "reason": f"HTTP {resp.status_code}: {resp.text[:200]}"
            }
    except Exception as e:
        return {"success": False, "reason": str(e)}


def grab_plan(config: Dict, retry_count: int = 0) -> bool:
    """执行抢购"""
    print(f"[{datetime.now().strftime('%H:%M:%S.%f')[:-3]}] 第{retry_count + 1}次尝试...")
    
    # 1. 检查库存
    print(f"[{datetime.now().strftime('%H:%M:%S')}] 检查库存...")
    stock = check_stock(config)
    
    if not stock.get("available", True):
        print(f"[{datetime.now().strftime('%H:%M:%S')}] 库存不可用: {stock.get('reason', '未知')}")
        return False
    
    # 2. 提交订单
    print(f"[{datetime.now().strftime('%H:%M:%S')}] 提交订单中...")
    result = submit_order(config)
    
    if result.get("success"):
        print(f"[{datetime.now().strftime('%H:%M:%S')}] ✅ 抢购成功！")
        notify_success(config, result)
        return True
    else:
        reason = result.get("reason", "未知错误")
        print(f"[{datetime.now().strftime('%H:%M:%S')}] ⏳ {reason}")
        
        # 非终结性错误才重试
        retryable = any(x in reason.lower() for x in ["配额", "售罄", "库存", "sold", "quota", "stock"])
        if retryable or retry_count < 3:
            return False
        else:
            notify_failure(config, reason, retry_count)
            return False


def countdown_and_grab(config: Dict):
    """倒计时并执行抢购"""
    grab_time = datetime.now().replace(
        hour=config["grab_hour"],
        minute=config["grab_minute"],
        second=0,
        microsecond=0
    )
    
    # 如果目标时间已过，算明天的
    if datetime.now() >= grab_time:
        grab_time += timedelta(days=1)
    
    wait_seconds = (grab_time - datetime.now()).total_seconds()
    pre_start = config["pre_start_seconds"]
    
    print(f"\n{'='*50}")
    print(f"📅 下次抢购时间：{grab_time.strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"⏰ 距抢购还有：{int(wait_seconds)}秒")
    print(f"🔍 提前 {pre_start} 秒开始监控库存")
    print(f"{'='*50}\n")
    
    # 等待到提前监控时间
    if wait_seconds > pre_start:
        time.sleep(wait_seconds - pre_start)
    
    # 持续重试直到成功或超时
    start_time = time.time()
    timeout = pre_start + 60  # 最多抢1分钟
    
    retry_count = 0
    while time.time() - start_time < timeout:
        if grab_plan(config, retry_count):
            return True
        
        retry_count += 1
        if config["max_retries"] > 0 and retry_count >= config["max_retries"]:
            print(f"[{datetime.now().strftime('%H:%M:%S')}] 已达最大重试次数")
            break
        
        # 越接近抢购时间，间隔越短
        interval = max(0.1, config["retry_interval"] * (0.9 ** min(retry_count, 10)))
        jitter = random.uniform(0.05, 0.15)
        time.sleep(interval + jitter)
    
    return False


# ==================== 守护模式 ====================
def run_daemon(config: Dict):
    """守护进程模式，每日定时执行"""
    print("🚀 启动守护模式（每日定时抢购）")
    print(f"📅 抢购时间：{config['grab_hour']:02d}:{config['grab_minute']:02d}")
    print("=" * 50)
    
    # 简单实现：不依赖APScheduler的cron
    while True:
        now = datetime.now()
        target = now.replace(
            hour=config["grab_hour"],
            minute=config["grab_minute"],
            second=0,
            microsecond=0
        )
        
        # 距离下次抢购的秒数
        if now >= target:
            target += timedelta(days=1)
        
        seconds_until = (target - now).total_seconds()
        
        print(f"\n⏰ 下次抢购：{target.strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"💤 距离还有：{int(seconds_until)}秒")
        
        # 等待
        time.sleep(min(seconds_until, 3600))  # 最多睡1小时，防止时间跳变
        
        # 再次检查是否到点
        now = datetime.now()
        if now.hour == config["grab_hour"] and now.minute == config["grab_minute"]:
            countdown_and_grab(config)
        
        # 避免重复触发
        time.sleep(60)


# ==================== 主入口 ====================
def main():
    parser = argparse.ArgumentParser(description="GLM Coding Plan 抢购脚本")
    parser.add_argument("--daemon", action="store_true", help="守护模式（每日定时）")
    parser.add_argument("--test", action="store_true", help="测试模式（立即尝试）")
    args = parser.parse_args()
    
    # 加载配置
    config = load_config()
    
    # 检查依赖
    if not requests and not httpx:
        print("❌ 错误：请安装 requests 或 httpx")
        print("   pip install requests")
        sys.exit(1)
    
    # 检查Cookie
    if not config["cookie"]:
        cookie = prompt_for_cookie()
        if not cookie:
            print("❌ 未输入 Cookie，程序退出")
            sys.exit(1)
        # 保存 Cookie 以便下次使用
        save_cookie_to_file(cookie)
        config["cookie"] = cookie
        print("✅ Cookie 已保存，下次运行无需重新输入")
    
    # 验证Cookie
    if not validate_cookie(config["cookie"]):
        print("⚠️ 警告：Cookie格式可能不正确")
    
    print("""
╔═══════════════════════════════════════════╗
║   GLM Coding Plan 自动抢购脚本 v1.0       ║
║   智谱AI编程套餐抢购工具                    ║
╚═══════════════════════════════════════════╝
    """)

    # 处理信号
    def signal_handler(sig, frame):
        print("\n\n👋 退出抢购脚本")
        sys.exit(0)

    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    # 命令行参数优先于交互选择
    if args.daemon:
        run_daemon(config)
    elif args.test:
        print("🧪 测试模式：立即尝试抢购\n")
        countdown_and_grab(config)
    else:
        # 交互式选择模式
        mode = prompt_for_mode()
        if mode == 2:
            run_daemon(config)
        elif mode == 3:
            print("🧪 测试模式：立即尝试抢购\n")
            countdown_and_grab(config)
        else:
            print("📌 单次抢购模式\n")
            countdown_and_grab(config)


if __name__ == "__main__":
    main()
