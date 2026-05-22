# ╭───╮
# │ ⚆_⚆ │  MiMo Terminal Helper v2.0.0
# ╰───╯

> **轻量级终端代码助手**

[![License](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)
[![Python](https://img.shields.io/badge/python-3.8+-blue.svg)](https://www.python.org/)
[![Version](https://img.shields.io/badge/version-2.0.0-orange.svg)](pyproject.toml)

`mimo-terminal-helper` 是一个全交互式的命令行 AI 助手。它不仅支持无缝接入任何兼容 **OpenAI 格式** 的大模型节点（如小米 MiMo、DeepSeek、智谱 GLM、硅基流动等），更内置高级 **Agent 拦截器**，允许大模型在你的安全审查下自动探索目录、批量读写代码以及执行终端 Bash 命令。

> 非小米官方项目；API Key 由用户自行申请并保存在本地 `~/.mimo_config.json`，请勿提交到 Git。

---

## ✨ 核心亮点

- 🌐 **全自主多节点管理**：摆脱单一环境变量，内置交互式配置向导。支持秒级切换节点、修改单节点模型、定点注销节点（运行中输入 `/config`）。
- 🔍 **API 天眼自动探测**：绑定新节点时自动请求 `/v1/models`，智能拉取并平铺可用模型，支持数字键快速选择。
- ⚡ **盲打模型联网校验**：手动输入未知模型时，后台发送极简探测请求，提前拦截拼写错误与无效模型名。
- 🧠 **智能记忆压缩引擎**：上下文对话过长时，自动触发摘要把老旧历史沉淀为系统记忆，缓解多轮对话「健忘」。
- 🛠️ **跨系统万能防撞网**：针对 WSL / Linux 深度优化，字节流安全解码，更好兼容挂载盘路径与中英文报错信息。
- 🤖 **Agent 工作流**：`[[LIST_DIR]]` / `[[READ_FILES]]` / `[[EDIT_FILE]]`（SEARCH/REPLACE）/ `[[RUN_CMD]]`，附带红·黄·绿命令安全网关与失败自动重试（最多 3 次）。

---

## 🛠️ 安装指南

项目基于现代 Python 包管理工具 **`uv`** 构建，推荐一键安装为全局命令 `mimo`。

### 1. 安装 `uv`

**Linux / macOS / WSL：**

```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
source $HOME/.local/bin/env
```

若 `source` 报错，可改为：

```bash
source ~/.bashrc
```

**Windows（PowerShell）：**

```powershell
powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"
```

### 2. 克隆并安装本项目（全局命令）

```bash
git clone https://github.com/sasha-lyk/mimo-terminal-helper.git
cd mimo-terminal-helper
uv tool install --editable .
```

> **说明**：`uv pip install -e .` 只会装进**当前目录的虚拟环境**，退出项目后往往找不到 `mimo`。  
> `pyproject.toml` 里配置了 `[project.scripts]`，应使用 **`uv tool install`** 在系统路径注册全局快捷方式（一般在 `~/.local/bin`，需已在 PATH 中）。

安装完成后，**任意目录**均可运行：

```bash
mimo
```

若提示找不到命令，执行 `source ~/.bashrc` 或重新打开终端，并确认 `~/.local/bin` 在 PATH 里。

### 3. 首次启动：配置模型节点

首次运行会进入**交互式向导**，按提示填写：

| 项 | 说明 |
|----|------|
| 节点别名 | 自定义名称，如 `mimo`、`deepseek` |
| API Base URL | 填到 **`/v1` 为止**即可；向导会**自动补全**为 `/v1/chat/completions`。示例见下表。 |
| API Key | 该平台的密钥（仅存本地 `~/.mimo_config.json`，**勿提交 Git**） |
| 模型名 | 可数字键从 `/v1/models` 列表选择，或手动输入并联网校验 |

**Base URL 示例（任选其一，按你的平台文档为准）：**

| 平台 | 填写示例（到 `/v1` 即可） |
|------|---------------------------|
| DeepSeek | `https://api.deepseek.com/v1` |
| 小米 MiMo | `https://token-plan-cn.xiaomimimo.com/v1` |
| 其他 OpenAI 兼容 | `https://你的网关地址/v1` |

之后随时输入 **`/config`** 重新打开管理菜单：切换节点、改模型、注销节点等。

### 安装后自检（建议做一次）

```bash
which mimo          # Linux/macOS：应显示路径，如 ~/.local/bin/mimo
mimo                # 首次会进入配置向导，选 1 添加节点
```

配置完成后，在任意项目目录执行 `mimo` 即可使用。

### 4. 备选：仅用 pip（无 uv）

仓库名是 **`mimo-terminal-helper`**，主程序文件名是 **`mimo_chat.py`**（二者不同，不要找错文件）：

```bash
git clone https://github.com/sasha-lyk/mimo-terminal-helper.git
cd mimo-terminal-helper
pip3 install requests
python3 mimo_chat.py
```

也可在项目目录执行 `pip3 install -e .`，然后在**该虚拟环境激活后**使用 `mimo` 命令。

或仅复制 **`mimo_chat.py`** 到 `~/.mimo_chat.py`，再运行 `python3 ~/.mimo_chat.py`（需自行维护 `~/.mimo_config.json`，不推荐）。

---

## 🎮 使用示例

```bash
cd ~/your-project
mimo
```

**场景 1：多文件分析**

```text
🤵 你 >>> 看看 src 目录有什么，再读 server.cpp 和 server.h，帮我找逻辑问题
🤖 MiMo >>> ⚙️ [Agent] 正在探索目录… ✅
         ⚙️ [Agent] 正在批量读取… ✅
```

**场景 2：编译失败自动修复**

```text
🤵 你 >>> 编译并运行当前目录的 main.cpp
🤖 MiMo >>> 🟢 [安全命令审查] g++ main.cpp -o main
         （确认后执行；失败则触发自动修复，最多 3 次）
```

输入 **`exit`** / **`quit`** 退出。

---

## 📁 配置文件

| 路径 | 作用 |
|------|------|
| `~/.mimo_config.json` | 多节点 URL、Key、模型（**勿上传、勿提交 Git**） |
| 项目根目录 | Agent 读写与执行命令的当前工作目录 |

`.gitignore` 已忽略常见密钥与日志文件；请勿将 `~/.mimo_config.json` 加入仓库。

---

## 🔒 安全说明

- 高危命令（如 `rm`、`sudo rm`）需输入大写 **`YES`** 才执行。
- 敏感操作（`git push`、`kill` 等）需明确确认。
- 请勿在 Issue、截图、README 中暴露真实 API Key。
- 本工具为第三方开源项目，与小米等公司无官方隶属关系；使用各平台 API 须遵守其服务条款。

---

## ⚖️ 开源协议

本项目基于 [MIT License](LICENSE) 开源，可自由使用与修改；衍生作品请保留原作者署名。

**作者**：一颗朝天椒
