#!/bin/bash
# GLM Coding Plan 抢购脚本运行器

DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$DIR"

# 检查依赖
if ! python3 -c "import requests" 2>/dev/null; then
    echo "📦 安装依赖..."
    # 首先尝试用户级别安装，避免权限问题
    pip3 install --user requests httpx -q || pip install --user requests httpx -q || {
        echo "⚠️  尝试使用 pip3 安装..."
        pip3 install requests httpx -q || pip install requests httpx -q
    }
fi

# 检查配置
if [ ! -s "config.py" ] || grep -q 'COOKIE = ""' config.py 2>/dev/null; then
    echo "⚠️  请先配置 config.py 中的 COOKIE"
    echo "   1. 登录 https://bigmodel.cn"
    echo "   2. F12 → Network → 复制 Cookie"
    echo "   3. 填入 config.py"
    exit 1
fi

# 验证 Cookie 有效性
echo "🔍 正在验证 Cookie 有效性..."
if python3 -c "
import sys
sys.path.append('.')
from grab_glm_coding_plan import load_config, validate_cookie
config = load_config()
if validate_cookie(config['cookie']):
    print('✅ Cookie 验证成功')
    sys.exit(0)
else:
    print('❌ Cookie 验证失败，请检查 Cookie 是否正确')
    sys.exit(1)
" 2>/dev/null; then
    echo "✅ Cookie 验证通过，开始运行..."
else
    echo "❌ Cookie 验证失败，程序退出"
    exit 1
fi

# 运行模式
MODE=${1:-single}

case "$MODE" in
    daemon)
        echo "🚀 启动守护模式..."
        python3 grab_glm_coding_plan.py --daemon
        ;;
    test)
        echo "🧪 测试模式..."
        python3 grab_glm_coding_plan.py --test
        ;;
    *)
        echo "📌 单次抢购..."
        python3 grab_glm_coding_plan.py
        ;;
esac
