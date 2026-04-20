# GLM Coding Plan 抢购工具

智谱AI编程套餐自动抢购脚本

## 功能特性

- ✅ 自动抢购 GLM Coding Plan 订阅套餐
- ✅ 支持守护模式和定时任务
- ✅ 登录状态检查和会话管理
- ✅ 套餐库存监控
- ✅ 飞书通知推送
- ✅ 交互式用户界面
- ✅ 优雅的进程终止处理

## 套餐信息

| 套餐 | 价格 | 额度 |
|------|------|------|
| Lite | ¥20/月 | 每 5 小时约 120 次 prompts |
| Pro | ¥60/月 | 每 5 小时约 600 次 prompts |
| Max | ¥120/月 | 每 5 小时约 2400 次 prompts |

**限售规则：**
- 每日 10:00 刷新配额
- 每日可购买量 = 原来的 20%
- 已订阅用户自动续订不受影响

## 推广返利（可选）

如果你有智谱的推广邀请码，可以设置环境变量让抢购订单关联到你的推广：

**Linux/macOS：**
```bash
export ZHIPU_IC_CODE="你的邀请码"
```

**Windows CMD：**
```cmd
set ZHIPU_IC_CODE=你的邀请码
```

**Windows PowerShell：**
```powershell
$env:ZHIPU_IC_CODE="你的邀请码"
```

**持久化设置（Windows）：** 右键"此电脑" → 属性 → 高级系统设置 → 环境变量 → 新建系统变量

⚠️ **隐私提示**：推广码属于隐私信息，请勿将 config.py 文件分享给他人！

## 快速开始

### 1. 安装依赖

```bash
pip install -r requirements.txt
```

### 2. 配置参数

复制配置文件并填入真实值：

```bash
cp config.example.py config.py
```

编辑 `config.py`：

```python
# 智谱AI登录Cookie（必须）
# 获取方法：登录 bigmodel.cn → F12 → Network → 任意请求复制Cookie头
COOKIE = ""

# 飞书Webhook地址（可选，留空则打印到终端）
FEISHU_WEBHOOK = ""

# 飞书用户ID（可选，用于@某人）
FEISHU_USER_ID = ""

# 每日抢购时间
GRAB_HOUR = 10
GRAB_MINUTE = 0

# 提前多少秒开始监控（秒）
PRE_START_SECONDS = 30

# 抢购失败后重试间隔（秒）
RETRY_INTERVAL = 1

# 最大重试次数（0=不限制）
MAX_RETRIES = 300

# 要购买的套餐：lite / pro / max
PLAN_TYPE = "lite"

# 是否自动续订
AUTO_RENEW = True
```

### 3. 获取 Cookie

1. 打开浏览器访问 [https://bigmodel.cn](https://bigmodel.cn)
2. 登录你的账号
3. 按 `F12` 打开开发者工具
4. 切换到 `Network`（网络）标签
5. 刷新页面，点击任意请求
6. 复制 `Cookie` 请求头的完整值
7. 粘贴到 `config.py` 的 `COOKIE` 变量中

### 4. 运行脚本

```bash
# 运行单次抢购（交互式选择）
python grab_glm_coding_plan.py

# 运行守护模式（每日定时）
python grab_glm_coding_plan.py --daemon

# 运行测试模式（立即尝试）
python grab_glm_coding_plan.py --test

# 使用便捷脚本运行
./run.sh              # 单次抢购
./run.sh daemon       # 守护模式
./run.sh test         # 测试模式
```

## 运行模式

| 模式 | 参数 | 说明 |
|------|------|------|
| 交互模式 | (无参数) | 运行时交互选择模式 | 
| 守护模式 | `--daemon` | 每日定时自动抢购 |
| 测试模式 | `--test` | 立即尝试抢购（测试） |

## 脚本说明

| 脚本 | 说明 |
|------|------|
| `grab_glm_coding_plan.py` | 主程序，支持多种运行模式 |
| `run.sh` | 便捷启动脚本 |
| `config.example.py` | 配置文件模板 |

## 配置说明

### 账号配置

```python
COOKIE = ""  # 智谱AI登录Cookie
```

### 通知配置

```python
FEISHU_WEBHOOK = ""  # 飞书机器人Webhook地址
FEISHU_USER_ID = ""  # 飞书用户ID（用于@某人）
```

### 抢购配置

```python
GRAB_HOUR = 10          # 每日抢购时间（小时）
GRAB_MINUTE = 0         # 每日抢购时间（分钟）
PRE_START_SECONDS = 30  # 提前多少秒开始监控（秒）
RETRY_INTERVAL = 1      # 抢购失败后重试间隔（秒）
MAX_RETRIES = 300       # 最大重试次数（0=不限制）
```

### 套餐配置

```python
PLAN_TYPE = "lite"   # 要购买的套餐：lite / pro / max
AUTO_RENEW = True    # 是否自动续订
```

## 守护模式

守护模式会在后台持续运行，每天在指定时间自动抢购：

```bash
python grab_glm_coding_plan.py --daemon
```

脚本会在以下时机自动执行抢购：
- 每天指定时间（`GRAB_HOUR:GRAB_MINUTE`）
- 提前 `PRE_START_SECONDS` 秒开始监控库存
- 发现库存后立即下单

## 通知推送

配置飞书 Webhook 后，抢购结果会推送到飞书群：

1. 在飞书群中添加「自定义机器人」
2. 复制 Webhook 地址
3. 填入 `config.py` 的 `FEISHU_WEBHOOK`

通知示例：

```
✅ 抢购成功！
订单号：ORD123456
套餐：专业版
耗时：1.23 秒
```

## 后台运行

### 使用 nohup

```bash
nohup python main.py schedule > grabber.log 2>&1 &
```

### 使用 screen

```bash
screen -S grabber
python main.py schedule
# 按 Ctrl+A, D 分离会话
# 重新连接：screen -r grabber
```

### 使用 crontab（推荐）

```bash
# 编辑 crontab
crontab -e

# 添加每日 9:59 开始监控的任务（10 点抢购）
59 9 * * * cd /path/to/glm-coding-plan-grabber && python main.py run --retries 60
```

## 退出方式

- 按 `Ctrl+C` 优雅终止
- 脚本会等待当前操作完成后退出
- 定时模式会完成本轮监控后退出

## 注意事项

1. **Cookie 有效期**：Cookie 可能过期，如抢购失败请重新获取
2. **网络环境**：确保网络畅通，建议使用稳定的网络连接
3. **抢购频率**：过高的请求频率可能触发限流
4. **合规使用**：请遵守智谱 AI 的服务条款

## 常见问题

### Q: Cookie 在哪里获取？

A: 登录 bigmodel.cn 后，打开浏览器开发者工具（F12），在 Network 标签中找到任意请求，复制 Cookie 请求头。

### Q: 如何验证 Cookie 是否有效？

A: 运行 `python main.py check` 检查登录状态。

### Q: 抢购失败怎么办？

A: 检查以下几点：
- Cookie 是否有效（运行 `check` 命令）
- 套餐是否有库存
- 网络连接是否正常
- 增加重试次数和间隔

### Q: 如何设置多个抢购时间？

A: 修改 crontab 配置，添加多个时间点：
```bash
# 早上 10 点和晚上 20 点各运行一次
0 10 * * * cd /path && python main.py run
0 20 * * * cd /path && python main.py run
```

## 项目结构

```
glm-coding-plan-grabber/
├── main.py            # 主程序入口
├── config_user.py     # 配置模板
├── config.py          # 用户配置（需创建）
├── requirements.txt   # Python 依赖
├── auth.py            # 认证模块
├── subscription.py    # 订阅模块
├── scheduler.py       # 调度模块
├── notification.py    # 通知模块
├── logger.py          # 日志模块
└── README.md          # 说明文档
```

## 相关资源

- [智谱 AI 官网](https://bigmodel.cn)
- [智谱 AI 开放平台](https://open.bigmodel.cn)
- [智谱 AI 开发者文档](https://open.bigmodel.cn/dev/api)

## 免责声明

本脚本仅供学习交流使用，请勿用于商业目的。使用本脚本造成的任何后果由用户自行承担。

## License

MIT License
