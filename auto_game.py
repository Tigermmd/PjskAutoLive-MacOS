# auto_game.py

import tkinter as tk
from tkinter import ttk, messagebox, Text
import pyautogui
import time
import random
import json
import threading
import os

# ==================== 关键优化：关闭 PyAutoGUI 默认延迟 ====================
pyautogui.PAUSE = 0  # ⚠️ 必须设置为 0，否则每次操作自动 sleep 0.1 秒！
pyautogui.FAILSAFE = True

# 默认参数
DEFAULT_CONFIG = {
    "click_interval_enter": 0.7,
    "load_time_before_game": 15.0,
    "game_duration": 80.0,
    "load_time_after_game": 12.0,
    "click_interval_return": 1.5,
    "click_interval_in_game": 0.167,  # 每轮“全按”间隔（秒）
    "click_jitter": 2,               # 推荐 2 像素扰动，更自然
    "time_jitter": 0.005,
    "max_loops": 10,
}

CONFIG_FILE = "config.json"

# 自定义提示
CUSTOM_TIPS = """
使用提示：请确定已设置为0火
不保证不死，尽量多带奶卡
把鼠标移出屏幕外可中断
"""

WORK_DURATION = 30 * 60   # 工作时间：210 分钟 → 秒
REST_DURATION = 1 * 60    # 休息时间：15 分钟 → 秒


class RhythmGameBot:
    def __init__(self):
        self.running = False
        self.start_time = None
        self.loop_count = 0
        self.enter_steps = []
        self.game_tracks = []
        self.return_pos = None
        self.config = DEFAULT_CONFIG.copy()
        self.load_saved_config()
        self.load_positions()
        self.setup_gui()

    def load_saved_config(self):
        if os.path.exists(CONFIG_FILE):
            try:
                with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                    saved = json.load(f)
                for k in self.config.keys():
                    if k in saved:
                        self.config[k] = float(saved[k])
            except Exception as e:
                messagebox.showwarning("⚠️ 配置加载失败", f"使用默认值：\n{e}")

    def save_config(self):
        try:
            with open(CONFIG_FILE, "w", encoding="utf-8") as f:
                json.dump(self.config, f, indent=2, ensure_ascii=False)
        except Exception as e:
            print(f"⚠️ 无法保存配置: {e}")

    def load_positions(self):
        try:
            with open("positions.json", "r", encoding="utf-8") as f:
                data = json.load(f)

            if "enter_steps" not in data:
                raise KeyError("缺少 'enter_steps'")
            self.enter_steps = [tuple(pos) for pos in data["enter_steps"]]
            if len(self.enter_steps) != 7:
                raise ValueError(f"enter_steps 应为7个点，实际有 {len(self.enter_steps)} 个")

            if "track_left" not in data or "track_right" not in data:
                raise KeyError("缺少 'track_left' 或 'track_right'")
            left = data["track_left"]
            right = data["track_right"]
            x_left, y_left = left
            x_right, y_right = right
            y = y_left
            x_step = (x_right - x_left) / 3
            self.game_tracks = [(int(x_left + i * x_step), y) for i in range(4)]

            if "return_pos" not in data:
                raise KeyError("缺少 'return_pos'")
            self.return_pos = tuple(data["return_pos"])

            print("✅ 坐标加载成功")

        except FileNotFoundError:
            messagebox.showerror("❌ 文件未找到", "未找到 positions.json\n请先运行 calibrate.py")
            exit()
        except Exception as e:
            messagebox.showerror("❌ 加载失败", f"坐标文件错误：\n{e}")
            exit()

    def setup_gui(self):
        self.root = tk.Tk()
        self.root.title("🎵 节奏游戏自动化 - 终极版")
        self.root.geometry("400x700")
        self.root.resizable(False, False)
        self.root.configure(bg="#1e1e1e")

        font_label = ("Arial", 10, "bold")
        font_entry = ("Arial", 10)
        font_tip = ("Arial", 9)

        title = tk.Label(
            self.root,
            text="节奏游戏自动化",
            font=("Arial", 14, "bold"),
            fg="white",
            bg="#1e1e1e"
        )
        title.pack(pady=(10, 5))

        subtitle = tk.Label(
            self.root,
            text="带完整参数控制 + 安全保护",
            font=("Arial", 9),
            fg="#cccccc",
            bg="#1e1e1e"
        )
        subtitle.pack(pady=(0, 20))

        param_frame = tk.Frame(self.root, bg="#1e1e1e")
        param_frame.pack(fill="x", padx=10, pady=5)

        self.entries = {}

        params = [
            ("click_interval_enter", "进入流程点击间隔 (秒)"),
            ("load_time_before_game", "进入后加载时间 (秒)"),
            ("game_duration", "游戏内持续时间 (秒)"),
            ("load_time_after_game", "结算前等待时间 (秒)"),
            ("click_interval_return", "返回点击间隔 (秒)"),
            ("click_interval_in_game", "🎮 每轮全按间隔 (秒)"),
            ("click_jitter", "🎮 点击坐标扰动 (±像素)"),
            ("time_jitter", "🎮 时间扰动范围 (±秒)"),
            ("max_loops", "⏹️ 最大循环次数 (0=无限)"),
        ]

        for i, (key, desc) in enumerate(params):
            label = tk.Label(
                param_frame,
                text=desc,
                font=font_label,
                fg="white",
                bg="#1e1e1e",
                anchor="w"
            )
            label.grid(row=i, column=0, sticky="w", padx=5, pady=3)

            v = tk.StringVar(value=str(self.config[key]))
            entry = tk.Entry(
                param_frame,
                textvariable=v,
                width=10,
                font=font_entry,
                justify="center",
                bg="#2d2d2d",
                fg="white",
                relief="flat",
                bd=0
            )
            entry.grid(row=i, column=1, padx=5, pady=3)
            self.entries[key] = v

        self.status = tk.Label(
            self.root,
            text="状态: 等待启动",
            font=("Arial", 9),
            fg="#cccccc",
            bg="#1e1e1e",
            anchor="w"
        )
        self.status.pack(pady=(10, 5))

        self.info_text = tk.Text(
            self.root,
            height=5,
            width=45,
            font=("Courier", 9),
            bg="#2d2d2d",
            fg="white",
            wrap="word",
            relief="sunken",
            bd=1
        )
        self.info_text.pack(pady=5)
        self.info_text.insert("end", "运行信息：\n")
        self.info_text.config(state="disabled")

        btn_frame = tk.Frame(self.root, bg="#1e1e1e")
        btn_frame.pack(pady=10)

        self.btn_start = ttk.Button(
            btn_frame,
            text="▶️ 开始自动化",
            command=self.start,
            style="TButton"
        )
        self.btn_start.pack(side="left", padx=5)

        self.btn_stop = ttk.Button(
            btn_frame,
            text="⏹️ 停止",
            command=self.stop,
            state="disabled",
            style="TButton"
        )
        self.btn_stop.pack(side="left", padx=5)

        tip_label = tk.Label(
            self.root,
            text="📌 使用提示",
            font=("Arial", 9, "bold"),
            fg="#ff6b6b",
            bg="#1e1e1e"
        )
        tip_label.pack(anchor="w", pady=(10, 5))

        tip_text = Text(
            self.root,
            height=5,
            width=45,
            font=font_tip,
            bg="#2d2d2d",
            fg="white",
            wrap="word",
            relief="sunken",
            bd=1
        )
        tip_text.pack(pady=5)
        tip_text.insert("end", CUSTOM_TIPS)
        tip_text.config(state="disabled")

        tk.Label(
            self.root,
            text="© rhythm bot v2.0",
            font=("Arial", 8),
            fg="#666",
            bg="#1e1e1e"
        ).pack(side="bottom", pady=5)

        style = ttk.Style()
        style.theme_use("clam")
        style.configure("TButton", background="#3a3a3a", foreground="white", font=("Arial", 10))
        style.map("TButton", background=[('active', '#4a4a4a')])

    # ==================== 核心优化：快速点击 + 极小延迟 ====================
    def safe_click(self, pos):
        x, y = pos
        jitter_px = int(self.config["click_jitter"])
        dx = random.randint(-jitter_px, jitter_px)
        dy = random.randint(-jitter_px, jitter_px)
        final_pos = (x + dx, y + dy)
        pyautogui.click(final_pos)

    def update_config_from_gui(self):
        try:
            for key in self.config.keys():
                self.config[key] = float(self.entries[key].get())
            self.save_config()
            return True
        except ValueError:
            messagebox.showerror("❌ 输入错误", "所有参数必须是数字")
            return False

    def start(self):
        if self.running:
            return
        if not self.update_config_from_gui():
            return

        self.btn_start.config(state="disabled")
        self.btn_stop.config(state="normal")
        self.update_status("3秒后开始，切回游戏窗口！", "orange")
        self.running = True
        self.loop_count = 0
        self.start_time = time.time()

        self.countdown(3)

    def countdown(self, n):
        if n > 0:
            self.update_status(f"倒计时 {n} 秒... 切回游戏！", "orange")
            self.root.after(1000, self.countdown, n - 1)
        else:
            self.update_status("🎮 自动化已启动", "green")
            thread = threading.Thread(target=self.main_control_loop, daemon=True)
            thread.start()

    def stop(self):
        self.running = False
        self.btn_start.config(state="normal")
        self.btn_stop.config(state="disabled")
        self.update_status("🛑 已停止", "red")

    def update_status(self, text, color="black"):
        self.status.config(text=f"状态: {text}", fg=color)

    def update_info(self, text):
        self.info_text.config(state="normal")
        self.info_text.delete("1.0", "end")
        self.info_text.insert("end", text)
        self.info_text.config(state="disabled")

    def should_take_rest(self):
        """判断是否应该进入休息（仅在本轮结束后）"""
        elapsed = time.time() - self.start_time
        return elapsed >= WORK_DURATION

    def check_max_loops(self):
        max_loops = int(self.config["max_loops"])
        if max_loops > 0 and self.loop_count >= max_loops:
            self.running = False
            self.update_status(f"✅ 已完成 {max_loops} 轮", "green")
            messagebox.showinfo("✅", f"已完成 {max_loops} 轮，自动停止")
            return True
        return False

    def main_control_loop(self):
        """主控制循环：完成当前轮次后再决定是否休息"""
        while self.running:
            # 检查是否达到最大循环次数
            if self.check_max_loops():
                break

            # 检查是否需要休息（但先完成本轮）
            if self.should_take_rest():
                self.update_status("😴 准备休息：完成当前轮后将休息15分钟", "blue")
                self.run_single_cycle()  # 执行完当前轮
                if not self.running:
                    break

                # 进入休息
                self.update_status("⏸️ 正在休息 (15分钟)", "blue")
                rest_end = time.time() + REST_DURATION
                while self.running and time.time() < rest_end:
                    time.sleep(1)
                # 休息结束，重置开始时间，进入下一个工作周期
                self.start_time = time.time()
                continue

            # 正常执行一轮
            self.run_single_cycle()

        self.stop()

    def run_single_cycle(self):
        """执行一次完整的进入-游戏-返回流程"""
        if not self.running:
            return

        self.loop_count += 1
        info = f"🔄 第 {self.loop_count} 轮\n"
        info += f"⏱️  已运行: {int((time.time()-self.start_time)//60)} 分钟"
        self.update_info(info)

        try:
            self.update_status(f"➡️ 第 {self.loop_count} 轮: 进入流程")
            for pos in self.enter_steps:
                if not self.running:
                    return
                self.safe_click(pos)
                time.sleep(self.config["click_interval_enter"])
            time.sleep(self.config["load_time_before_game"])

            self.update_status(f"🎮 第 {self.loop_count} 轮: 游戏中")
            end_time = time.time() + self.config["game_duration"]

            while time.time() < end_time and self.running:
                for track in self.game_tracks:
                    if not self.running:
                        return
                    self.safe_click(track)
                    time.sleep(0.001)

                base = self.config["click_interval_in_game"]
                jitter = self.config["time_jitter"]
                sleep_time = random.uniform(base - jitter, base + jitter)
                time.sleep(max(0.001, sleep_time))

            self.update_status(f"🔚 第 {self.loop_count} 轮: 返回主菜单")
            time.sleep(self.config["load_time_after_game"])
            for _ in range(10):
                if not self.running:
                    return
                self.safe_click(self.return_pos)
                time.sleep(self.config["click_interval_return"])

            time.sleep(1)

        except Exception as e:
            print(f"❌ 第 {self.loop_count} 轮出错: {e}")
            time.sleep(5)


    def run(self):
        self.root.mainloop()


# ============ 启动 ============
if __name__ == "__main__":
    print("📌 请确保已为终端/IDE 添加辅助功能权限")
    bot = RhythmGameBot()
    bot.run()