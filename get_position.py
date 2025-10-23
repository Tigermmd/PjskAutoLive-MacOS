from pynput import mouse, keyboard
import threading

# 用于控制监听是否继续
stop = False

def on_click(x, y, button, pressed):
    if pressed and not stop:
        print(f"Clicked at: ({x}, {y})")

def on_press(key):
    global stop
    try:
        if key == keyboard.Key.esc:
            print("Esc pressed. Exiting...")
            stop = True
            return False  # 停止键盘监听
    except AttributeError:
        pass

def main():
    print("🖱️  点击任意位置，将打印坐标。按 Esc 键退出。")

    # 启动鼠标监听器（非阻塞）
    mouse_listener = mouse.Listener(on_click=on_click)
    mouse_listener.start()

    # 启动键盘监听器（用于检测 Esc 退出）
    with keyboard.Listener(on_press=on_press) as kb_listener:
        kb_listener.join()  # 阻塞主线程，直到键盘监听结束

    # 停止鼠标监听
    mouse_listener.stop()
    mouse_listener.join()

if __name__ == "__main__":
    main()