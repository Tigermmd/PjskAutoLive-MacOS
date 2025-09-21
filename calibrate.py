# calibrate.py
# 节奏游戏坐标采集器 - 最终版

import tkinter as tk
from tkinter import ttk, messagebox
import json
import time
from pynput import mouse
import os

# 要采集的 10 个点击点（按顺序）
POINTS = [
    "1. 主界面 - '演出' 按钮",
    "2. 选择单人演出",
    "3. 选择左侧歌单",
    "4. 选择🦐",
    "5. 选择easy难度",
    "6. 确定",
    "7. 点击 '开始演奏'",
    "8. 游戏内 - 最左边轨道点击位置",
    "9. 游戏内 - 最右边轨道点击位置",
    "10. 结算界面 - '返回主菜单' 按钮（将连续点5次）"
]


class Calibrator:
    def __init__(self):
        self.positions = []
        self.current_count = 0
        self.listener = None

        # GUI
        self.root = tk.Tk()
        self.root.title("🎵 节奏游戏坐标校准器")
        self.root.geometry("550x450")
        self.root.resizable(False, False)
        self.root.configure(padx=10, pady=10)

        self.setup_ui()

    def setup_ui(self):
        # 标题
        title = tk.Label(
            self.root,
            text="节奏游戏坐标校准器",
            font=("Arial", 16, "bold")
        )
        title.pack(pady=10)

        desc = tk.Label(
            self.root,
            text="请按顺序在游戏内点击以下 10 个位置",
            fg="blue",
            font=("Arial", 10)
        )
        desc.pack(pady=5)

        # 列表框显示10个点
        frame = tk.Frame(self.root)
        frame.pack(pady=10, fill="both", expand=True)

        self.listbox = tk.Listbox(frame, height=10, width=70, font=("Courier", 10))
        scrollbar = tk.Scrollbar(frame, orient="vertical", command=self.listbox.yview)
        self.listbox.configure(yscrollcommand=scrollbar.set)

        for i, point in enumerate(POINTS):
            self.listbox.insert("end", f"{i+1:2d}. {point}")

        self.listbox.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")

        # 状态栏
        self.status = tk.Label(
            self.root,
            text="准备就绪",
            fg="green",
            font=("Arial", 10),
            wraplength=500,
            anchor="w"
        )
        self.status.pack(pady=5, fill="x")

        # 按钮区
        btn_frame = tk.Frame(self.root)
        btn_frame.pack(pady=10)

        self.btn_start = ttk.Button(
            btn_frame,
            text="🔴 开始录制接下来的10次点击",
            command=self.start_listening,
            width=30
        )
        self.btn_start.pack(side="left", padx=5)

        self.btn_clear = ttk.Button(
            btn_frame,
            text="🗑️ 清除记录",
            command=self.clear_records
        )
        self.btn_clear.pack(side="left", padx=5)

    def on_click(self, x, y, button, pressed):
        if not pressed or button != mouse.Button.left:
            return  # 只记录左键按下

        if self.current_count >= len(POINTS):
            return  # 仅记录10次

        # 记录点击
        self.current_count += 1
        self.positions.append((int(x), int(y)))

        # 更新状态
        self.status.config(
            text=f"✅ 第{self.current_count}步完成: ({x}, {y})",
            fg="green"
        )
        self.listbox.itemconfig(self.current_count - 1, fg="gray")

        if self.current_count < len(POINTS):
            self.listbox.itemconfig(self.current_count, fg="red")
            self.status.config(
                text=f"请进行第 {self.current_count + 1} 步: {POINTS[self.current_count].split(' - ')[-1]}",
                fg="orange"
            )
        else:
            # === 第10次点击完成 → 自动保存 ===
            self.status.config(text="🎉 全部10个点已记录，正在保存...", fg="blue")
            self.btn_start.config(state="disabled")
            self.save_positions()
            if self.listener:
                self.listener.stop()
            self.listener = None

    def countdown(self, n):
        """非阻塞倒计时"""
        if n > 0:
            self.status.config(text=f"⏳ 倒计时 {n} 秒... 请切换到游戏界面", fg="orange")
            self.root.after(1000, self.countdown, n - 1)
        else:
            self.status.config(text="✅ 开始记录第一次点击！", fg="green")
            self.listener = mouse.Listener(on_click=self.on_click)
            self.listener.start()

    def start_listening(self):
        if self.current_count >= len(POINTS):
            messagebox.showinfo("提示", "✅ 已记录全部10个点！")
            return

        # 确认开始
        confirm = messagebox.askokcancel(
            "🎮 准备开始录制",
            "即将开始录制接下来的 10 次鼠标左键点击。\n\n"
            "请做好准备：\n"
            "1. 点击【确定】\n"
            "2. 快速切换到游戏窗口\n"
            "3. 等待倒计时结束\n\n"
            "倒计时 5 秒后开始记录第一次点击。"
        )
        if not confirm:
            return

        self.btn_start.config(state="disabled")
        self.clear_records()  # 重置状态（避免残留）
        self.status.config(text="5秒后开始记录...", fg="orange")
        for i in range(len(POINTS)):
            self.listbox.itemconfig(i, fg="black")
        self.listbox.itemconfig(0, fg="red")

        # 启动倒计时
        self.countdown(5)

    def save_positions(self):
        """保存坐标到 positions.json"""
        structured = {
            "enter_steps": self.positions[:7],
            "track_left":  self.positions[7],
            "track_right": self.positions[8],
            "return_pos":  self.positions[9],
            "_note": "自动生成: rhythm game calibrator",
            "_timestamp": time.strftime("%Y-%m-%d %H:%M:%S")
        }

        try:
            with open("positions.json", "w", encoding="utf-8") as f:
                json.dump(structured, f, indent=2, ensure_ascii=False)
            # 提示音（macOS）
            os.system('afplay /System/Library/Sounds/Pop.aiff &')
            messagebox.showinfo(
                "✅ 保存成功",
                "所有坐标已成功保存到：\npositions.json\n"
                "现在可以启动主程序了！"
            )
        except Exception as e:
            messagebox.showerror("❌ 保存失败", f"无法保存文件：\n{e}")

    def clear_records(self):
        """清除当前记录"""
        self.positions.clear()
        self.current_count = 0
        self.status.config(text="已清除所有记录", fg="black")
        self.btn_start.config(state="normal")
        for i in range(len(POINTS)):
            self.listbox.itemconfig(i, fg="black")
        if self.listener:
            self.listener.stop()
            self.listener = None

    def on_closing(self):
        """关闭窗口时处理未保存数据"""
        if 0 < len(self.positions) < len(POINTS):
            if messagebox.askyesno("⚠️ 未完成记录", "已记录部分坐标但未完成10次点击。\n是否保存当前数据？"):
                self.save_positions()
        elif len(self.positions) == len(POINTS):
            if messagebox.askyesno("💾 保存坐标", "已记录全部10个点，是否保存？"):
                self.save_positions()
        self.root.destroy()

    def run(self):
        """启动 GUI"""
        self.root.protocol("WM_DELETE_WINDOW", self.on_closing)
        self.root.mainloop()


# ============ 运行 ============
if __name__ == "__main__":
    app = Calibrator()
    app.run()