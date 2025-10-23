# calibrate.py
# 节奏游戏坐标采集器 - 最终版

import tkinter as tk
from tkinter import ttk, messagebox
import json
import time
from pynput import mouse
import os

# 要采集的 14 个点击点（按顺序）
POINTS = [
    "1. 登陆界面进入游戏",
    "2. 登陆错误是确认位置（1的右边一些）",
    "3. 干掉公告(如果没有弹出公告，请使用get_position.py手动确认后修改json内enter_steps的最后一项)",
    "4. 右上角菜单",
    "5. 返回主页面",
    "6. 开始演出",
    "7. 左上角返回",
    "8. 同6，开始演出",
    "9. 单人Live",
    "10. 确认",
    "11. 开始演奏",
    "12. 游戏内 - 最左边轨道点击位置",
    "13. 游戏内 - 最右边轨道点击位置",
    "14. 结算界面 - '返回主菜单' 按钮（将连续点10次）"
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
            text="请按顺序在游戏内点击以下 14 个位置,推荐先登陆把当日登陆内容点掉，然后返回标题界面后开始",
            fg="red",
            font=("Arial", 10)
        )
        desc.pack(pady=5)

        # 列表框显示14个点
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
            text="🔴 开始录制接下来的14次点击",
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
            return  # 仅记录14次

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
            # === 第14次点击完成 → 自动保存 ===
            self.status.config(text="🎉 全部14个点已记录，正在保存...", fg="blue")
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
            messagebox.showinfo("提示", "✅ 已记录全部14个点！")
            return

        # 确认开始
        confirm = messagebox.askokcancel(
            "🎮 准备开始录制",
            "即将开始录制接下来的 14 次鼠标左键点击。\n\n"
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
        # 把登陆步骤放到进入歌曲后面，防止在主界面误触
        tmp_pos = self.positions[:11]
        game_pos = self.positions[11:]
        starts = tmp_pos[3:] + tmp_pos[:3] 
        self.positions = starts + game_pos
        structured = {
            "enter_steps": self.positions[:11],
            "track_left":  self.positions[11],
            "track_right": self.positions[12],
            "return_pos":  self.positions[13],
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
            if messagebox.askyesno("⚠️ 未完成记录", "已记录部分坐标但未完成14次点击。\n是否保存当前数据？"):
                self.save_positions()
        elif len(self.positions) == len(POINTS):
            if messagebox.askyesno("💾 保存坐标", "已记录全部14个点，是否保存？"):
                self.save_positions()
        self.root.destroy()

    def run(self):
        """启动 GUI"""
        # self.root.protocol("WM_DELETE_WINDOW", self.on_closing)
        self.root.mainloop()


# ============ 运行 ============
if __name__ == "__main__":
    app = Calibrator()
    app.run()