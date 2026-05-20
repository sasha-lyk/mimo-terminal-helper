# ╰───╯ 小米 MiMo 助手 1.0 (Agent Mode)

#   │ ⚆_⚆ │  轻量级终端代码助手

中文安装说明见同仓库上级目录：**`小米mimo助手1.0.md`**

[![License](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)
[![Python](https://img.shields.io/badge/python-3.6+-blue.svg)](https://www.python.org/)

**小米 MiMo 助手** 是一款专为 Linux / 树莓派终端打造的**轻量级终端代码助手**。拒绝繁重的第三方 Agent 框架，仅用两百余行纯原生 Python，对接小米 MiMo 对话 API，在命令行里完成流式问答、读改代码与命令执行。

> **当前开源版本：1.0 Agent Mode**（本仓库 `mimo_chat.py`）：流式对话 + 目录/读文件/改文件/跑命令 + 安全网关。

本工具对标 **Claude Code / Aider** 的终端使用体验：在舒适的 Shell 里用自然语言问问题、要代码，再按需保存到本地文件。

---

## 当前版本核心特性 (Agent 1.0)

- **Spinner 等待动画**：请求期间终端盲文点阵动画。
- **流式打字机输出**：`stream=True`，回复逐字显示。
- **环境感知**：启动时注入当前目录与文件列表。
- **LIST_DIR / READ_FILES**：AI 输出标签后由脚本静默执行并回填。
- **EDIT_FILE（SEARCH/REPLACE）**：局部改文件或新建文件。
- **RUN_CMD + 安全网关**：红/黄/绿三级确认；阻塞命令可后台 + 日志。
- **自动修 Bug**：命令失败最多自动重试 3 次。
- **密钥环境变量**：从 `MIMO_API_KEY` 读取；代码内仅占位 `YOUR API KEY`。

---

## 环境搭建与安装

### 1. 安装依赖

```bash
pip3 install requests
```

### 2. 配置环境变量（必做）

脚本**只**从系统环境变量读取 API Key。在 `~/.bashrc` 或 `~/.zshrc` 中加入：

```bash
export MIMO_API_KEY="您的真实小米MiMo API密钥"
```

使其生效：

```bash
source ~/.bashrc
```

验证：

```bash
echo $MIMO_API_KEY
# 应输出你的密钥（勿截图外传）
```

### 3. 下载并部署脚本

将本仓库的 `mimo_chat.py` 复制到用户目录（推荐）：

```bash
cp mimo_chat.py ~/.mimo_chat.py
chmod +x ~/.mimo_chat.py
```

### 4. 一键启动别名

```bash
echo "alias mimo='python3 ~/.mimo_chat.py'" >> ~/.bashrc
source ~/.bashrc
```

---

## 使用示例

任意目录下：

```bash
mimo
```

输入 `exit` 或 `quit` 退出。

**示例对话：**

```text
🤵 你 >>> 用一句话解释 ROS2 里 topic 和 service 的区别
🤖 MiMo >>> （流式输出回答…）
┌─── Token 消耗面板 ───
│ [本次] 输入: … | 输出: …
```

若回复含代码块，按提示输入文件名即可保存到**当前工作目录**。

---

---

## 安全说明

- **禁止** 将真实 `MIMO_API_KEY` 写入 `mimo_chat.py` 或提交到 Git。
- 若 Key 曾误提交，请立即在小米控制台**吊销并轮换**新 Key。
- 本仓库已包含 `.gitignore`，请勿强制添加 `.env` 或含密钥的文件。

---

## 开源协议

本项目基于 [MIT License](LICENSE) 开源。可自由复制、修改与商用；衍生作品请保留原作者署名。

**作者**：一颗朝天椒
