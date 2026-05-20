#!/usr/bin/env python3
import json
import os
import re
import subprocess
import sys
import threading
import time

import requests


class Spinner:
    def __init__(self, message="🤖 MiMo 正在思考"):
        self.spinner_chars = [
            "⠋", "⠙", "⠹", "⠸", "⠼", "⠴", "⠦", "⠧", "⠇", "⠏",
        ]
        self.delay = 0.08
        self.running = False
        self.thread = None
        self.message = message

    def spin(self):
        i = 0
        while self.running:
            sys.stdout.write(
                f"\r\033[1;35m{self.message} "
                f"{self.spinner_chars[i % len(self.spinner_chars)]}\033[0m"
            )
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
    # 从环境变量读取；勿在代码里写真实 Key（开源用 YOUR API KEY 占位）
    MY_API_KEY = os.environ.get("MIMO_API_KEY", "YOUR API KEY")
    if not MY_API_KEY or MY_API_KEY.strip() == "YOUR API KEY":
        print(
            "\n❌ 未配置 API Key。\n"
            "请执行：\n"
            '  echo \'export MIMO_API_KEY="你的真实密钥"\' >> ~/.bashrc\n'
            "  source ~/.bashrc\n"
        )
        sys.exit(1)

    URL = "https://token-plan-cn.xiaomimimo.com/v1/chat/completions"
    MODEL_NAME = "mimo-v2.5-pro"

    cwd = os.getcwd()
    try:
        files = ", ".join(os.listdir(cwd)[:20])
    except Exception:
        files = "无法获取目录详情"

    history = [
        {
            "role": "system",
            "content": (
                "你是一个驻留在 Linux 终端里的顶级 AI 极客助手，对标 Claude Code。\n"
                f"【环境感知】当前工作目录: {cwd}\n"
                f"【根目录概览】: {files}\n\n"
                "【核心能力 1 - 探测与阅读】：\n"
                "- 查看某目录下有哪些文件，输出 [[LIST_DIR:相对路径]] "
                "(如 [[LIST_DIR:./src]])\n"
                "- 读取一个或多个文件，输出 [[READ_FILES:文件1,文件2...]] "
                "(如 [[READ_FILES:main.cpp,utils.h]])\n"
                "【核心能力 2 - 修改/创建文件】：必须使用以下格式"
                "（严禁使用XML tool_calls）：\n"
                "[[EDIT_FILE:文件名]]\n"
                "<<<SEARCH\n"
                "原代码（若为新建文件，此处留空）\n"
                "===\n"
                "新代码\n"
                "REPLACE>>>\n"
                "【核心能力 3 - 执行终端命令】：当需要编译、运行或执行系统命令"
                "（如 git status）时，你必须输出：[[RUN_CMD:要执行的bash命令]]。"
                "绝对不要输出任何 XML 标签格式。\n"
                "系统会自动解析这些特定标签并静默执行，将结果返回给你。"
            ),
        },
    ]

    MAX_HISTORY = 6
    total_prompt_tokens = 0
    total_completion_tokens = 0

    print("\n\033[1;36m")
    print("  ╭───╮  ")
    print("  │ ⚆_⚆ │  小米 MiMo 助手 1.0 (Agent Mode)")
    print("  ╰───╯  \033[0m")
    print("\033[0;90m  ──────────────────────────────────────────\033[0m")
    print("  \033[0;32m> System Online.\033[0m \033[0;33m输入 exit 退出。\033[0m\n")

    headers = {
        "Authorization": f"Bearer {MY_API_KEY}",
        "Content-Type": "application/json",
    }

    auto_trigger = False
    auto_fix_retries = 0

    while True:
        try:
            if not auto_trigger:
                user_input = input("\033[1;32m🤵 你 >>> \033[0m").strip()
                if not user_input:
                    continue
                if user_input.lower() in ("exit", "quit"):
                    print("\n🤖 助手下线，再见！\n")
                    break
                history.append({"role": "user", "content": user_input})
            else:
                auto_trigger = False

            if len(history) > MAX_HISTORY:
                history = [history[0]] + history[-(MAX_HISTORY - 1) :]

            payload = {
                "model": MODEL_NAME,
                "messages": history,
                "stream": True,
                "stream_options": {"include_usage": True},
            }

            spinner = Spinner("🤖 MiMo 正在思考")
            spinner.start()
            try:
                response = requests.post(
                    URL,
                    json=payload,
                    headers=headers,
                    stream=True,
                    timeout=20,
                )
            finally:
                spinner.stop()

            if response.status_code != 200:
                raw_text = response.content.decode("utf-8", errors="ignore")
                print(
                    f"\n❌ 服务器返回错误 {response.status_code}: "
                    f"{raw_text}\n"
                )
                continue

            print(f"\033[1;35m🤖 MiMo >>>\033[0m ", end="", flush=True)

            full_reply = ""
            p_tokens = c_tokens = t_tokens = 0

            for line in response.iter_lines():
                if not line:
                    continue
                line_str = line.decode("utf-8", errors="ignore").strip()
                if not line_str.startswith("data:"):
                    continue
                data_str = line_str[5:].strip()
                if data_str == "[DONE]":
                    break
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

            total_prompt_tokens += p_tokens
            total_completion_tokens += c_tokens

            if t_tokens > 0:
                g = "\033[0;90m"
                z = "\033[0m"
                print(f"{g}┌─── Token 消耗面板 ─────────────────────────────────────┐{z}")
                print(
                    f"{g}│{z} \033[1;34m[本次] 输入: {p_tokens:<5} "
                    f"| 输出: {c_tokens:<5} | 总计: {t_tokens:<5}\033[0m"
                )
                print(
                    f"{g}│{z} \033[1;33m[累计] 输入: {total_prompt_tokens:<7} "
                    f"| 输出: {total_completion_tokens:<7} "
                    f"| 总和: "
                    f"{total_prompt_tokens + total_completion_tokens:<7}\033[0m"
                )
                print(
                    f"{g}└────────────────────────────────────────────────────────┘{z}\n"
                )

            history.append({"role": "assistant", "content": full_reply})

            # === 拦截器 1.1：目录探索 ===
            dir_match = re.search(r"\[\[LIST_DIR:(.+?)\]\]", full_reply)
            if dir_match:
                target_dir = dir_match.group(1).strip()
                print(
                    f"\033[0;33m⚙️ [Agent] 正在探索目录: {target_dir}...\033[0m"
                )
                try:
                    dir_contents = "\n".join(os.listdir(target_dir))
                    history.append({
                        "role": "user",
                        "content": (
                            f"【系统静默返回目录 {target_dir} 的内容】:\n"
                            f"```\n{dir_contents}\n```\n请继续分析或操作。"
                        ),
                    })
                    auto_trigger = True
                    continue
                except Exception as e:
                    history.append({
                        "role": "user",
                        "content": (
                            f"【系统报错】：无法读取目录 {target_dir}: {e}"
                        ),
                    })
                    auto_trigger = True
                    continue

            # === 拦截器 1.2：多文件批量读取 ===
            read_match = re.search(r"\[\[READ_FILES:(.+?)\]\]", full_reply)
            if read_match:
                filenames = [
                    f.strip() for f in read_match.group(1).split(",")
                ]
                print(
                    f"\033[0;33m⚙️ [Agent] 正在批量静默读取: "
                    f"{', '.join(filenames)}...\033[0m"
                )
                combined_content = ""
                for fname in filenames:
                    try:
                        with open(fname, "r", encoding="utf-8") as f:
                            combined_content += f"--- {fname} ---\n{f.read()}\n\n"
                    except Exception as e:
                        combined_content += f"--- {fname} ---\n读取失败: {e}\n\n"

                history.append({
                    "role": "user",
                    "content": (
                        f"【系统静默返回文件内容】:\n```\n{combined_content}"
                        f"```\n请继续。"
                    ),
                })
                auto_trigger = True
                continue

            # === 拦截器 2：修改/创建文件 ===
            edit_blocks = re.findall(
                r"\[\[EDIT_FILE:(.+?)\]\]\s*<<<SEARCH\n?(.*?)\n?===\n?"
                r"(.*?)\n?REPLACE>>>",
                full_reply,
                re.DOTALL,
            )
            for block in edit_blocks:
                filename = block[0].strip()
                search_text = block[1].strip()
                replace_text = block[2].strip("\n")

                print(
                    f"\033[0;33m⚙️ [Agent] 正在处理文件: {filename}...\033[0m"
                )
                try:
                    if not os.path.exists(filename) or not search_text:
                        with open(filename, "w", encoding="utf-8") as f:
                            f.write(replace_text + "\n")
                        print(
                            f"\033[1;32m✅ 成功创建/写入 {filename}！\033[0m\n"
                        )
                    else:
                        with open(filename, "r", encoding="utf-8") as f:
                            original_content = f.read()

                        if search_text in original_content:
                            new_content = original_content.replace(
                                search_text, replace_text, 1
                            )
                            with open(filename, "w", encoding="utf-8") as f:
                                f.write(new_content)
                            print(
                                f"\033[1;32m✅ 成功修改 {filename}！\033[0m\n"
                            )
                        else:
                            print(
                                "\033[1;31m❌ 修改失败：无法精确匹配原代码。\033[0m\n"
                            )
                            history.append({
                                "role": "user",
                                "content": (
                                    f"【系统报错】：尝试修改 {filename} 失败，"
                                    "原代码未精确匹配，请检查缩进或重新输出。"
                                ),
                            })
                            auto_trigger = True
                except Exception as e:
                    print(f"\033[1;31m❌ 文件操作报错: {e}\033[0m\n")

            # === 拦截器 3：安全沙箱 + 命令执行 ===
            cmd_match = re.search(r"\[\[RUN_CMD:(.+?)\]\]", full_reply)
            if cmd_match:
                cmd = cmd_match.group(1).strip()

                danger_keywords = (
                    r"\b(rm|dd|mkfs|chmod\s+777|chown|shutdown|reboot|sudo\s+rm)\b"
                )
                warn_keywords = (
                    r"\b(git\s+commit|git\s+push|mkdir|mv|kill|pkill|ufw|iptables)\b"
                )
                is_blocking = (
                    any(
                        k in cmd.lower()
                        for k in [
                            "server",
                            "listen",
                            "python3",
                            "node",
                            "npm start",
                        ]
                    )
                    or cmd.strip().endswith("&")
                )

                if re.search(danger_keywords, cmd):
                    print(
                        f"\n\033[1;41m🛑 [高危安全警报] AI 企图执行破坏性命令:\033[0m "
                        f"\033[1;31m{cmd}\033[0m"
                    )
                    confirm = input(
                        "\033[1;33m⚠️  警告：该操作可能导致系统损坏或数据丢失！"
                        "请输入大写 \033[1;31mYES\033[0;33m 确认执行: \033[0m"
                    ).strip()
                    is_allowed = confirm == "YES"
                elif re.search(warn_keywords, cmd):
                    print(
                        f"\n\033[1;33m⚠️  [敏感操作提示] AI 企图修改系统或代码库:\033[0m "
                        f"\033[1;36m{cmd}\033[0m"
                    )
                    confirm = (
                        input("\033[0;33m允许执行吗？(y/n) [默认 n]: \033[0m")
                        .strip()
                        .lower()
                    )
                    is_allowed = confirm in ("y", "yes")
                else:
                    print(
                        f"\n\033[1;32m🟢 [安全命令审查] AI 准备执行:\033[0m "
                        f"\033[1;36m{cmd}\033[0m"
                    )
                    confirm = (
                        input("\033[0;32m确认执行？(Y/n) [默认 Y]: \033[0m")
                        .strip()
                        .lower()
                    )
                    is_allowed = confirm in ("", "y", "yes")

                if is_allowed:
                    print("\033[0;90m[系统执行中...]\033[0m")
                    try:
                        if is_blocking and not cmd.strip().endswith("&"):
                            log_file = f".mimo_{int(time.time())}.log"
                            cmd_patched = f"{cmd} > {log_file} 2>&1 &"
                            subprocess.run(cmd_patched, shell=True)

                            print(
                                "\033[1;32m⚡ [智能接管] 检测到阻塞型服务，"
                                "已移至后台运行！\033[0m"
                            )
                            print(
                                f"\033[0;90m[提示] 日志: {log_file}\033[0m\n"
                            )

                            history.append({
                                "role": "user",
                                "content": (
                                    "【系统静默返回】：长耗时/服务端命令已在后台运行。"
                                    f"日志在 `{log_file}`。请继续。"
                                ),
                            })
                            auto_trigger = True
                            continue

                        result = subprocess.run(
                            cmd,
                            shell=True,
                            capture_output=True,
                            text=True,
                            timeout=30,
                        )
                        output = result.stdout + result.stderr

                        if result.returncode == 0:
                            print(f"\033[0;32m✅ [执行成功]\033[0m\n{output}")
                            history.append({
                                "role": "user",
                                "content": (
                                    f"【系统静默返回】：命令 `{cmd}` 执行成功。\n"
                                    f"输出:\n```\n{output}\n```\n请继续。"
                                ),
                            })
                            auto_fix_retries = 0
                            auto_trigger = True
                            continue

                        print(
                            f"\033[1;31m❌ [执行失败 (Exit {result.returncode})]"
                            f"\033[0m\n{output}"
                        )
                        auto_fix_retries += 1

                        if auto_fix_retries <= 3:
                            print(
                                f"\033[0;33m🔄 [Agent] 自动修复 "
                                f"({auto_fix_retries}/3)...\033[0m"
                            )
                            history.append({
                                "role": "user",
                                "content": (
                                    f"【系统报错】：命令 `{cmd}` 失败 "
                                    f"(Exit {result.returncode})。\n"
                                    f"```\n{output}\n```\n"
                                    "请用 [[EDIT_FILE]] 修复并重试 [[RUN_CMD]]。"
                                ),
                            })
                            auto_trigger = True
                            continue

                        print(
                            "\033[1;31m🛑 自动修复已达最大次数，交由人类接管。\033[0m"
                        )
                        history.append({
                            "role": "user",
                            "content": (
                                "【系统通知】：连续 3 次修复失败。"
                                "请向用户总结报错并给出手动排查建议。"
                            ),
                        })
                        auto_fix_retries = 0
                        auto_trigger = True
                        continue

                    except subprocess.TimeoutExpired:
                        print("\033[1;31m❌ 执行超时 (30s)\033[0m\n")
                        history.append({
                            "role": "user",
                            "content": f"【系统报错】：命令 `{cmd}` 执行超时。",
                        })
                        auto_trigger = True
                        continue
                else:
                    print("\033[0;33m[安全网关：用户拒绝执行该命令]\033[0m")
                    history.append({
                        "role": "user",
                        "content": (
                            f"【系统通知】：用户拒绝执行 `{cmd}`。"
                            "请换安全方法或向用户解释必要性。"
                        ),
                    })

        except KeyboardInterrupt:
            print("\n\n🤖 接收到中断信号，助手下线。\n")
            break
        except Exception as e:
            print(f"\n❌ 发生异常错误: {e}\n")


if __name__ == "__main__":
    main()
