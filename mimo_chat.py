#!/usr/bin/env python3
import json
import os
import re
import subprocess
import sys
import threading
import time
import requests

CONFIG_PATH = os.path.expanduser("~/.mimo_config.json")


def load_config():
    if os.path.exists(CONFIG_PATH):
        try:
            with open(CONFIG_PATH, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass
    return {"current_provider": None, "providers": {}}


def save_config(config):
    try:
        with open(CONFIG_PATH, "w", encoding="utf-8") as f:
            json.dump(config, f, indent=4, ensure_ascii=False)
    except Exception as e:
        print(f"❌ 保存配置文件失败: {e}")


def fetch_available_models(base_url, api_key):
    url = base_url.strip()
    if url.endswith("/chat/completions"):
        url = url.replace("/chat/completions", "/models")
    elif not url.endswith("/models"):
        url = url.rstrip("/") + "/models"

    headers = {"Authorization": f"Bearer {api_key}"}
    spinner = Spinner("🔍 正在为您疯狂探测可用模型")
    spinner.start()
    try:
        response = requests.get(url, headers=headers, timeout=5)
        spinner.stop()
        if response.status_code == 200:
            data = response.json()
            if isinstance(data, dict) and "data" in data:
                models = [item["id"] for item in data["data"] if isinstance(item, dict) and "id" in item]
                return sorted(list(set(models)))
    except Exception:
        spinner.stop()
    return []


def validate_model_name(base_url, api_key, model_name):
    """💡 不足 2 修复：发送后台静默请求，强力验证盲打的模型名称是否真实存在"""
    url = base_url.strip()
    if not url.endswith("/chat/completions"):
        url = url.rstrip("/") + "/chat/completions"

    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }
    # 极简撞击数据包
    payload = {
        "model": model_name,
        "messages": [{"role": "user", "content": "."}],
        "max_tokens": 1,
        "stream": False
    }
    spinner = Spinner(f"⚡ 正在联网验证模型 [{model_name}] 的合法性")
    spinner.start()
    try:
        res = requests.post(url, json=payload, headers=headers, timeout=6)
        spinner.stop()
        # 如果模型名字错了，大部分服务商会返回 400、404 等错误
        if res.status_code in (400, 404):
            try:
                err_msg = res.json().get("error", {}).get("message", "")
            except Exception:
                err_msg = res.text
            # 智能容错：如果是余额不足(429/400且含余额提示)，说明模型名字是对的，放行
            if "余额" in err_msg or "insufficient" in err_msg.lower():
                return True
            print(f"\n⚠️  验证未通过：服务器拒绝了该模型名称。报错提示: {err_msg}")
            return False
        return True
    except Exception as e:
        spinner.stop()
        print(f"\n⚠️  网络请求测试失败 ({e})，跳过合规校验。")
        return True


def compress_history_summary(base_url, api_key, model_name, old_messages, current_summary=""):
    """💡 不足 3 修复：智能大模型摘要压缩引擎"""
    url = base_url.strip()
    if not url.endswith("/chat/completions"):
        url = url.rstrip("/") + "/chat/completions"

    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }

    # 构建压缩提示词
    formatted_dialogue = ""
    for msg in old_messages:
        formatted_dialogue += f"{msg['role']}: {msg['content']}\n"

    prompt = "请帮我将以下长对话内容提炼并融合成一段简短、精炼的历史记忆概要（不超过200字）。\n"
    if current_summary:
        prompt += f"现有的历史记忆概要是: {current_summary}\n请在此基础上合并以下新对话：\n"
    prompt += f"--- 新对话开始 ---\n{formatted_dialogue}--- 新对话结束 ---\n请直接输出提炼后的纯文本概要。"

    payload = {
        "model": model_name,
        "messages": [{"role": "user", "content": prompt}],
        "stream": False
    }

    spinner = Spinner("🧠 正在触发智能记忆压缩，沉淀历史上下文")
    spinner.start()
    try:
        res = requests.post(url, json=payload, headers=headers, timeout=15)
        spinner.stop()
        if res.status_code == 200:
            summary = res.json()["choices"][0]["message"]["content"].strip()
            print(f"\033[0;90m⚙️  [System] 历史记忆成功压缩沉淀。\033[0m")
            return summary
    except Exception:
        spinner.stop()
    return current_summary


def configure_api_wizard():
    config = load_config()
    print("\n\033[1;36m⚙️  欢迎来到 MiMo 助手全自定义配置中心\033[0m")
    print("\033[0;90m──────────────────────────────────────────\033[0m")
    print("1. ➕ 添加/修改自定义 API 节点 (自定URL+自动获取模型)")
    print("2. 🔄 切换当前使用的 AI 节点 / 模型")
    print("3. 🗑️  精准清除/注销某一个本地 API 节点")
    print("4. 🚀 直接启动助手 (保持当前配置)")

    choice = input("\n\033[1;32m👉 请输入选项序号 [默认 4]: \033[0m").strip()

    if choice == "1":
        alias = input("\n🏷️  请为这个新节点起个名字 (如 deepseek, mimo, glm): ").strip().lower()
        if not alias:
            print("❌ 名字不能为空")
            return config

        url = input("🌐 请输入 API Base URL (如 https://api.deepseek.com/v1): ").strip()
        key = input("🔑 请输入对应的 API Key: ").strip()

        if url and key:
            if not url.startswith("http"):
                url = "https://" + url

            models = fetch_available_models(url, key)
            chosen_model = ""
            if models:
                print("\n\033[1;32m🎉 成功探测到以下可用模型：\033[0m")
                for idx, model in enumerate(models, 1):
                    print(f"  [{idx}] {model}")
                try:
                    m_idx = int(input(f"👉 请输入序号选择要绑定的模型 (1-{len(models)}): ").strip()) - 1
                    if 0 <= m_idx < len(models):
                        chosen_model = models[m_idx]
                except ValueError:
                    pass

            if not chosen_model:
                print("\n\033[1;33m⚠️  进入手动盲打模式。\033[0m")
                while True:
                    chosen_model = input("✍️  请输入您想绑定的确切模型名称 (如 glm-4-flash): ").strip()
                    if not chosen_model:
                        break
                    # ✨ 触发盲打合规性撞击校验
                    if validate_model_name(url, key, chosen_model):
                        break
                    else:
                        retry = input("❓ 该模型名称疑似不正确，是否强行坚持使用？(y/N): ").strip().lower()
                        if retry in ("y", "yes"):
                            break

            if chosen_model:
                final_url = url
                if not final_url.endswith("/chat/completions"):
                    final_url = final_url.rstrip("/") + "/chat/completions"

                config["providers"][alias] = {
                    "api_key": key,
                    "base_url": final_url,
                    "model": chosen_model
                }
                config["current_provider"] = alias
                print(f"✅ 节点 [{alias}] 配置成功，已绑定模型: {chosen_model}！")
                save_config(config)

    elif choice == "2":
        if not config["providers"]:
            print("\n❌ 当前未配置任何节点，请先选择选项 1 建立节点！")
            return config

        print("\n\033[1;35m请选择要管理的 AI 节点：\033[0m")
        available = list(config["providers"].keys())
        for idx, provider in enumerate(available, 1):
            status = "🔥 当前激活" if provider == config["current_provider"] else ""
            p_info = config["providers"][provider]
            print(f"  [{idx}] {provider.upper()} (当前模型: {p_info['model']}) {status}")

        try:
            ch_idx = int(input(f"请输入序号 (1-{len(available)}): ").strip()) - 1
            if 0 <= ch_idx < len(available):
                selected_node = available[ch_idx]
                config["current_provider"] = selected_node

                print(f"\n⚡ 已切换至节点 [{selected_node.upper()}]。")
                change_model = input("❓ 是否需要修改该节点的模型型号？(y/N): ").strip().lower()
                if change_model in ("y", "yes"):
                    p_info = config["providers"][selected_node]
                    models = fetch_available_models(p_info["base_url"], p_info["api_key"])

                    new_model = ""
                    if models:
                        print("\n\033[1;32m🎉 探测到该节点有以下可用模型：\033[0m")
                        for m_idx, model in enumerate(models, 1):
                            print(f"  [{m_idx}] {model}")
                        try:
                            m_sel = int(input(f"请输入序号选择新模型 (1-{len(models)}): ").strip()) - 1
                            if 0 <= m_sel < len(models):
                                new_model = models[m_sel]
                        except ValueError:
                            pass

                    if not new_model:
                        while True:
                            new_model = input(f"✍️  请输入新的模型型号名称 (当前为 {p_info['model']}): ").strip()
                            if not new_model:
                                break
                            # ✨ 触发修改时的盲打合规性测试
                            if validate_model_name(p_info["base_url"], p_info["api_key"], new_model):
                                break
                            else:
                                retry = input("❓ 该模型名称疑似不正确，是否强行坚持使用？(y/N): ").strip().lower()
                                if retry in ("y", "yes"):
                                    break

                    if new_model:
                        config["providers"][selected_node]["model"] = new_model
                        print(f"✅ 成功将节点 [{selected_node.upper()}] 的模型变更为: {new_model}")

                save_config(config)
        except ValueError:
            print("❌ 输入无效")

    elif choice == "3":
        if not config["providers"]:
            print("\n❌ 当前没有可删除的节点！")
            return config
        print("\n\033[1;31m🗑️  请选择要删除的 AI 节点：\033[0m")
        available = list(config["providers"].keys())
        for idx, provider in enumerate(available, 1):
            status = "🔥 当前激活" if provider == config["current_provider"] else ""
            print(f"  [{idx}] {provider.upper()} ({config['providers'][provider]['model']}) {status}")
        print(f"  [{len(available) + 1}] 💥 毁灭吧！一键清空所有节点")

        try:
            del_choice = input(f"\n👉 请输入序号 (1-{len(available) + 1}) [默认 取消]: ").strip()
            if del_choice:
                ch_idx = int(del_choice) - 1
                if ch_idx == len(available):
                    if input("\n⚠️ 确定全清吗？(yes/no): ").strip().lower() == "yes":
                        if os.path.exists(CONFIG_PATH): os.remove(CONFIG_PATH)
                        config = {"current_provider": None, "providers": {}}
                        print("🗑️ 配置全清！")
                        sys.exit(0)
                elif 0 <= ch_idx < len(available):
                    target_del = available[ch_idx]
                    if input(f"⚠️ 确定删除 [{target_del.upper()}] 吗？(yes/no): ").strip().lower() == "yes":
                        del config["providers"][target_del]
                        if config["current_provider"] == target_del:
                            config["current_provider"] = list(config["providers"].keys())[0] if config[
                                "providers"] else None
                        save_config(config)
                        print(f"🗑️  成功清除节点: [{target_del.upper()}]")
        except ValueError:
            print("❌ 输入无效")

    return config


class Spinner:
    def __init__(self, message="🤖 MiMo 正在思考"):
        self.spinner_chars = ["⠋", "⠙", "⠹", "⠸", "⠼", "⠴", "⠦", "⠧", "⠇", "⠏"]
        self.delay = 0.08
        self.running = False
        self.thread = None
        self.message = message

    def spin(self):
        i = 0
        while self.running:
            sys.stdout.write(f"\r\033[1;35m{self.message} {self.spinner_chars[i % len(self.spinner_chars)]}\033[0m")
            sys.stdout.flush()
            time.sleep(self.delay)
            i += 1
        sys.stdout.write("\r\033[K")
        sys.stdout.flush()

    def start(self):
        self.running = True
        self.thread = threading.Thread(target=self.spin)
        self.thread.daemon = True
        self.thread.start()

    def stop(self):
        self.running = False
        if self.thread:
            self.thread.join()


def main():
    config = load_config()

    if not config.get("current_provider") or config["current_provider"] not in config["providers"]:
        print("\n👋 未检测到有效配置，正在为您打开交互式向导...")
        config = configure_api_wizard()
        if not config.get("current_provider"):
            print("❌ 必须配置至少一个可用节点才能启动！")
            sys.exit(1)

    current = config["current_provider"]
    MY_API_KEY = config["providers"][current]["api_key"]
    URL = config["providers"][current]["base_url"]
    MODEL_NAME = config["providers"][current]["model"]

    cwd = os.getcwd()
    try:
        raw_files = os.listdir(cwd)[:20]
        files = ", ".join([f.encode('utf-8', errors='replace').decode('utf-8', errors='replace') for f in raw_files])
    except Exception:
        files = "无法获取目录详情"

    # 全局动态记忆摘要缓存
    history_memory_summary = ""

    # 基础核心 System 提示词
    base_system_prompt = (
        "你是一个驻留在 Linux 终端里的顶级 AI 极客助手，对标 Claude Code。\n"
        f"【环境感知】当前工作目录: {cwd}\n"
        f"【根目录概览】: {files}\n\n"
        "【核心能力 1 - 探测与阅读】：\n"
        "- 查看某目录下有哪些文件，输出 [[LIST_DIR:相对路径]]\n"
        "- 读取一个或多个文件，输出 [[READ_FILES:文件1,文件2...]]\n"
        "【核心能力 2 - 修改/创建文件】：必须使用以下格式：\n"
        "[[EDIT_FILE:文件名]]\n"
        "<<<SEARCH\n原代码\n===\n新代码\nREPLACE>>>\n"
        "【核心能力 3 - 执行终端命令】：必须输出：[[RUN_CMD:要执行的bash命令]]。\n"
        "系统会自动解析并静默执行，结果将返回给你。"
    )

    history = [{"role": "system", "content": base_system_prompt}]

    MAX_HISTORY = 8  # 允许最大长对话轮数
    total_prompt_tokens = total_completion_tokens = 0

    # ✨ 灵魂重构：注入炫酷的流式打字机启动动画
    logo_animation = [
        "\n\033[1;36m  ╭───╮  \033[0m",
        "\033[1;36m  │ ⚆_⚆ │  MiMo Terminal Helper v2.0.0\033[0m",
        "\033[1;36m  ╰───╯  \033[0m\n",
        "\033[0;90m  ────────────────────────────────────────────────────────────────\033[0m\n",
        f"  \033[0;32m> Node Active:\033[0m \033[1;34m[{current.upper()}]\033[0m  \033[0;32mModel:\033[0m \033[1;35m{MODEL_NAME}\033[0m  \033[0;33m输入 /config 管理配置 | 输入 exit 退出。\033[0m\n\n"
    ]

    for line in logo_animation:
        for char in line:
            sys.stdout.write(char)
            sys.stdout.flush()
            time.sleep(0.005)  # 微延时动效
        time.sleep(0.05)       # 行停顿间隙

    headers = {"Authorization": f"Bearer {MY_API_KEY}", "Content-Type": "application/json"}
    auto_trigger = False
    auto_fix_retries = 0

    while True:
        try:
            if not auto_trigger:
                user_input = input("\033[1;32m🤵 你 >>> \033[0m").strip()
                if not user_input: continue
                if user_input.lower() in ("exit", "quit"):
                    print("\n🤖 助手下线，再见！\n")
                    break

                if user_input.lower() == "/config":
                    config = configure_api_wizard()
                    current = config["current_provider"]
                    MY_API_KEY = config["providers"][current]["api_key"]
                    URL = config["providers"][current]["base_url"]
                    MODEL_NAME = config["providers"][current]["model"]
                    headers["Authorization"] = f"Bearer {MY_API_KEY}"
                    # 切换节点时重置记忆
                    history_memory_summary = ""
                    history = [{"role": "system", "content": base_system_prompt}]
                    print(
                        f"\n\033[0;32m🔄 已重载节点并切换引擎:\033[0m \033[1;34m[{current.upper()}]\033[0m -> \033[1;35m{MODEL_NAME}\033[0m (上下文历史记忆已安全交接)\n")
                    continue

                history.append({"role": "user", "content": user_input})
            else:
                auto_trigger = False

            # ✨ 绝杀重构位置 2（不足 3 历史记忆智能压缩算法）
            # 当用户多轮对话导致上下文堆积时，抽取中间最老的 4 轮对话拿去进行智能压缩总结
            if len(history) > MAX_HISTORY:
                slice_index = 4
                messages_to_compress = history[1:slice_index]

                # 触发多线程安全保护或直接后台同步压缩
                history_memory_summary = compress_history_summary(
                    URL, MY_API_KEY, MODEL_NAME, messages_to_compress, history_memory_summary
                )

                # 把压缩完的历史直接切掉，注入全新的带“历史概要”的 System 提示词
                dynamic_system_prompt = base_system_prompt + f"\n\n【关键历史对话遗留记忆摘要】：\n{history_memory_summary}\n"
                history = [{"role": "system", "content": dynamic_system_prompt}] + history[slice_index:]

            # 统一流式报文清洗
            safe_history = []
            for msg in history:
                if not msg.get("content") or not msg.get("role"): continue
                safe_content = msg["content"].encode('utf-8', errors='replace').decode('utf-8', errors='replace')
                safe_history.append({"role": msg["role"], "content": safe_content})

            payload = {"model": MODEL_NAME, "messages": safe_history, "stream": True}
            if "mimo" in current:
                payload["stream_options"] = {"include_usage": True}

            spinner = Spinner("🤖 MiMo 正在思考")
            spinner.start()
            try:
                response = requests.post(URL, json=payload, headers=headers, stream=True, timeout=20)
            finally:
                spinner.stop()

            if response.status_code != 200:
                raw_text = response.content.decode("utf-8", errors="replace")
                print(f"\n❌ 服务器返回错误 {response.status_code}: {raw_text}\n")
                continue

            print(f"\033[1;35m🤖 MiMo >>>\033[0m ", end="", flush=True)
            full_reply = ""
            p_tokens = c_tokens = t_tokens = 0

            for line in response.iter_lines():
                if not line: continue
                line_str = line.decode("utf-8", errors="ignore").strip()
                if not line_str.startswith("data:"): continue
                data_str = line_str[5:].strip()
                if data_str == "[DONE]": break
                try:
                    data_json = json.loads(data_str)
                    if "choices" in data_json and data_json["choices"]:
                        delta = data_json["choices"][0].get("delta", {})
                        chunk = delta.get("content", "")
                        if chunk:
                            full_reply += chunk
                            print(chunk, end="", flush=True)
                    if data_json.get("usage"):
                        usage = data_json["usage"]
                        p_tokens = usage.get("prompt_tokens", 0)
                        c_tokens = usage.get("completion_tokens", 0)
                        t_tokens = usage.get("total_tokens", 0)
                except Exception:
                    pass

            print("\n")

            if t_tokens > 0:
                total_prompt_tokens += p_tokens
                total_completion_tokens += c_tokens
                g, z = "\033[0;90m", "\033[0m"
                print(f"{g}┌─── Token 消耗面板 ─────────────────────────────────────┐{z}")
                print(
                    f"{g}│{z} \033[1;34m[本次] 输入: {p_tokens:<5} | 输出: {c_tokens:<5} | 总计: {t_tokens:<5}\033[0m")
                print(
                    f"{g}│{z} \033[1;33m[累计] 输入: {total_prompt_tokens:<7} | 输出: {total_completion_tokens:<7} | 总和: {total_prompt_tokens + total_completion_tokens:<7}\033[0m")
                print(f"{g}└────────────────────────────────────────────────────────┘{z}\n")

            history.append({"role": "assistant", "content": full_reply})

            # === 拦截器群组运作体系完全保持原样 ===
            dir_match = re.search(r"\[\[LIST_DIR:(.+?)\]\]", full_reply)
            if dir_match:
                target_dir = dir_match.group(1).strip()
                print(f"\033[0;33m⚙️ [Agent] 正在探索目录: {target_dir}...\033[0m")
                try:
                    dir_contents = "\n".join(os.listdir(target_dir))
                    history.append({"role": "user",
                                    "content": f"【系统静默返回目录 {target_dir} 的内容】:\n```\n{dir_contents}\n```\n请继续。"})
                    auto_trigger = True
                    continue
                except Exception as e:
                    history.append({"role": "user", "content": f"【系统报错】：无法读取目录 {target_dir}: {e}"})
                    auto_trigger = True
                    continue

            read_match = re.search(r"\[\[READ_FILES:(.+?)\]\]", full_reply)
            if read_match:
                filenames = [f.strip() for f in read_match.group(1).split(",")]
                print(f"\033[0;33m⚙️ [Agent] 正在批量静默读取: {', '.join(filenames)}...\033[0m")
                combined_content = ""
                for fname in filenames:
                    try:
                        with open(fname, "r", encoding="utf-8") as f:
                            combined_content += f"--- {fname} ---\n{f.read()}\n\n"
                    except Exception as e:
                        combined_content += f"--- {fname} ---\n读取失败: {e}\n\n"
                history.append(
                    {"role": "user", "content": f"【系统静默返回文件内容】:\n```\n{combined_content}```\n请继续。"})
                auto_trigger = True
                continue

            edit_blocks = re.findall(r"\[\[EDIT_FILE:(.+?)\]\]\s*<<<SEARCH\n?(.*?)\n?===\n?(.*?)\n?REPLACE>>>",
                                     full_reply, re.DOTALL)
            for block in edit_blocks:
                filename = block[0].strip()
                search_text = block[1].strip()
                replace_text = block[2].strip("\n")
                print(f"\033[0;33m⚙️ [Agent] 正在处理文件: {filename}...\033[0m")
                try:
                    if not os.path.exists(filename) or not search_text:
                        with open(filename, "w", encoding="utf-8") as f:
                            f.write(replace_text + "\n")
                        print(f"\033[1;32m✅ 成功创建/写入 {filename}！\033[0m\n")
                    else:
                        with open(filename, "r", encoding="utf-8") as f:
                            original_content = f.read()
                        if search_text in original_content:
                            new_content = original_content.replace(search_text, replace_text, 1)
                            with open(filename, "w", encoding="utf-8") as f:
                                f.write(new_content)
                            print(f"\033[1;32m✅ 成功修改 {filename}！\033[0m\n")
                        else:
                            print("\033[1;31m❌ 修改失败：无法精确匹配原代码。\033[0m\n")
                            history.append({"role": "user",
                                            "content": f"【系统报错】：尝试修改 {filename} 失败，原代码未精确匹配，请检查缩进。"})
                            auto_trigger = True
                except Exception as e:
                    print(f"\n❌ 文件操作报错: {e}\n")

            cmd_match = re.search(r"\[\[RUN_CMD:(.+?)\]\]", full_reply)
            if cmd_match:
                cmd = cmd_match.group(1).strip()
                danger_keywords = r"\b(rm|dd|mkfs|chmod\s+777|chown|shutdown|reboot|sudo\s+rm)\b"
                warn_keywords = r"\b(git\s+commit|git\s+push|mkdir|mv|kill|pkill|ufw|iptables)\b"
                is_blocking = any(k in cmd.lower() for k in
                                  ["server", "listen", "python3", "node", "npm start"]) or cmd.strip().endswith("&")

                if re.search(danger_keywords, cmd):
                    print(f"\n\033[1;41m🛑 [高危安全警报]:\033[0m \033[1;31m{cmd}\033[0m")
                    if input("\033[1;33m⚠️ 请输入大写 YES 确认执行: \033[0m").strip() != "YES": continue
                elif re.search(warn_keywords, cmd):
                    print(f"\n\033[1;33m⚠️ [敏感操作提示]:\033[0m \033[1;36m{cmd}\033[0m")
                    if input("允许执行吗？(y/n) [默认 n]: ").strip().lower() not in ("y", "yes"): continue
                else:
                    print(f"\n\033[1;32m🟢 [安全命令审查]:\033[0m \033[1;36m{cmd}\033[0m")
                    if input("确认执行？(Y/n) [默认 Y]: ").strip().lower() not in ("", "y", "yes"): continue

                print("\033[0;90m[系统执行中...]\033[0m")
                try:
                    if is_blocking and not cmd.strip().endswith("&"):
                        log_file = f".mimo_{int(time.time())}.log"
                        subprocess.run(f"{cmd} > {log_file} 2>&1 &", shell=True)
                        print(f"\033[1;32m⚡ [智能接管] 服务已在后台运行！日志: {log_file}\033[0m\n")
                        history.append(
                            {"role": "user", "content": f"【系统静默返回】：服务端命令已在后台运行。日志在 `{log_file}`。"})
                        auto_trigger = True
                        continue

                    result = subprocess.run(cmd, shell=True, capture_output=True, timeout=30)
                    stdout_str = result.stdout.decode('utf-8',
                                                      errors='replace') if b'\xef\xbb\xbf' in result.stdout or b'\xe4\xb8\xad' in result.stdout else result.stdout.decode(
                        'gbk', errors='replace')
                    stderr_str = result.stderr.decode('utf-8',
                                                      errors='replace') if b'\xef\xbb\xbf' in result.stderr or b'\xe4\xb8\xad' in result.stderr else result.stderr.decode(
                        'gbk', errors='replace')
                    output = stdout_str + stderr_str

                    if result.returncode == 0:
                        print(f"\033[0;32m✅ [执行成功]\033[0m\n{output}")
                        history.append({"role": "user",
                                        "content": f"【系统静默返回】：命令 `{cmd}` 执行成功。\n输出:\n```\n{output}\n```"})
                        auto_fix_retries = 0
                    else:
                        print(f"\n❌ [执行失败 (Exit {result.returncode})]\033[0m\n{output}")
                        auto_fix_retries += 1
                        if auto_fix_retries <= 3:
                            print(f"\033[0;33m🔄 [Agent] 自动修复 ({auto_fix_retries}/3)...\033[0m")
                            history.append({"role": "user",
                                            "content": f"【系统报错】：命令 `{cmd}` 失败 (Exit {result.returncode})。\n```\n{output}\n```\n请修复并重试。"})
                        else:
                            print("\033[1;31m🛑 自动修复已达最大次数，交由人类接管。\033[0m")
                            history.append(
                                {"role": "user", "content": "【系统通知】：连续 3 次修复失败。请向用户总结报错。"})
                            auto_fix_retries = 0
                    auto_trigger = True
                    continue
                except subprocess.TimeoutExpired:
                    print("\033[1;31m❌ 执行超时 (30s)\033[0m\n")
                    history.append({"role": "user", "content": f"【系统报错】：命令 `{cmd}` 执行超时。"})
                    auto_trigger = True

        except KeyboardInterrupt:
            print("\n\n🤖 接收到中断信号，助手下线。\n")
            break
        except Exception as e:
            print(f"\n❌ 发生异常错误: {e}\n")


if __name__ == "__main__":
    main()