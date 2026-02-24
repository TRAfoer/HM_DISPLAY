import tkinter as tk
from tkinter import scrolledtext
from PIL import Image, ImageTk
import numpy as np

# 屏幕参数：250x122
WIDTH = 250
HEIGHT = 122

class EPDSimulator:
    def __init__(self, root):
        self.root = root
        self.root.title("EPD 灰度指令流模拟器 (250x122)")
        self.root.geometry("800x600")

        # 1. 初始化虚拟缓冲区 (fb_bw)
        # 单片机侧 FB_SIZE = (122+7)/8 * 250 = 16 * 250 = 4000 字节
        self.line_bytes = (HEIGHT + 7) // 8  # 16 字节对齐
        self.fb_size = self.line_bytes * WIDTH
        self.fb_bw = bytearray([0xFF] * self.fb_size)

        # 2. 模拟物理屏幕灰度 (255=白, 0=黑)
        self.physical_screen = np.full((HEIGHT, WIDTH), 255, dtype=np.int16)

        # UI 构建
        self.setup_ui()

    def setup_ui(self):
        # 顶部预览
        self.canvas_label = tk.Label(self.root, text="物理屏幕模拟预览 (放大2倍)")
        self.canvas_label.pack()
        self.canvas = tk.Canvas(self.root, width=WIDTH*2, height=HEIGHT*2, bg="#ddd", highlightthickness=1)
        self.canvas.pack(pady=5)

        # 指令输入
        self.input_label = tk.Label(self.root, text="输入指令流 (一行一条，支持 93, 94 0f, 9a, 95):")
        self.input_label.pack()
        self.text_area = scrolledtext.ScrolledText(self.root, width=90, height=15, font=("Consolas", 10))
        self.text_area.pack(pady=5)
        
        # 默认填充示例指令
        example_cmds = "// 示例指令\n95\n93\n// 在0,0画一个32x32黑块\n94 0f 00 00 00 00 20 20 " + ("00 " * 128) + "\n9a\nw100"
        self.text_area.insert(tk.END, example_cmds)

        # 按钮
        self.btn_frame = tk.Frame(self.root)
        self.btn_frame.pack(pady=10)
        self.run_btn = tk.Button(self.btn_frame, text="▶ 执行指令流", command=self.parse_commands, bg="#4CAF50", fg="white", padx=20)
        self.run_btn.pack(side=tk.LEFT, padx=5)
        self.clear_btn = tk.Button(self.btn_frame, text="🗑 清空文本", command=lambda: self.text_area.delete(1.0, tk.END))
        self.clear_btn.pack(side=tk.LEFT, padx=5)

        self.status = tk.Label(self.root, text="就绪", fg="blue")
        self.status.pack()

        # 初始渲染
        self.refresh_canvas()

    def draw_pixel(self, x, y, color):
        """模拟单片机 draw_pixel 逻辑 (ROTATE_3)"""
        if x < 0 or x >= WIDTH or y < 0 or y >= HEIGHT:
            return

        # 旋转逻辑: nx = y; ny = scr_h - 1 - x;
        nx = y
        ny = WIDTH - 1 - x 

        byte_pos = ny * self.line_bytes + (nx >> 3)
        bit_mask = 0x80 >> (nx & 7)

        if byte_pos < self.fb_size:
            if color == 0: # BLACK
                self.fb_bw[byte_pos] &= ~bit_mask
            else: # WHITE
                self.fb_bw[byte_pos] |= bit_mask

    def simulate_draw_bitmap(self, x, y, w, h, data_hex_list):
        """解析 94 0f 的位图数据并写入 fb_bw"""
        try:
            data = [int(b, 16) for b in data_hex_list]
            bytes_per_row = (w + 7) // 8
            for row in range(h):
                for col in range(w):
                    byte_val = data[row * bytes_per_row + (col >> 3)]
                    color = 0 if not (byte_val & (0x80 >> (col & 7))) else 1
                    self.draw_pixel(x + col, y + row, color)
        except Exception as e:
            print(f"解析位图数据错误: {e}")

    def parse_commands(self):
        self.status.config(text="正在执行...", fg="red")
        lines = self.text_area.get("1.0", tk.END).split('\n')
        
        for line in lines:
            line = line.strip()
            if not line or line.startswith("//"): continue
            
            # 处理延时指令 wXXX (模拟器直接跳过)
            if line.startswith('w'): continue

            parts = line.split()
            cmd = parts[0].lower()

            if cmd == "93":
                # 93: 清空缓冲区 fb_bw
                self.fb_bw = bytearray([0xFF] * self.fb_size)
            
            elif cmd == "95":
                # 95: 物理屏幕刷白
                self.physical_screen.fill(255)

            elif cmd == "94" and len(parts) > 2:
                sub_cmd = parts[1].lower()
                if sub_cmd == "0f":
                    # 94 0f x y idxX idxY w h data...
                    x = int(parts[2], 16)
                    y = int(parts[3], 16)
                    w = int(parts[6], 16)
                    h = int(parts[7], 16)
                    data = parts[8:]
                    self.simulate_draw_bitmap(x, y, w, h, data)
                elif sub_cmd == "0d":
                    # 94 0d x1 y1 x2 y2 color (实心框)
                    x1, y1 = int(parts[2], 16), int(parts[3], 16)
                    x2, y2 = int(parts[4], 16), int(parts[5], 16)
                    color = int(parts[6], 16)
                    for i in range(x1, x2 + 1):
                        for j in range(y1, y2 + 1):
                            self.draw_pixel(i, j, color)

            elif cmd == "9a":
                # 9a: 灰度叠加刷新 (将当前 fb_bw 状态作用于 physical_screen)
                self.apply_grayscale_step()

        self.refresh_canvas()
        self.status.config(text="执行完毕", fg="green")

    def apply_grayscale_step(self):
        """核心：模拟微脉冲。fb 中为黑的点，物理屏幕加深一步灰度"""
        for y in range(HEIGHT):
            for x in range(WIDTH):
                # 逆向解析 fb_bw 检查该像素是否为黑
                nx = y
                ny = WIDTH - 1 - x
                byte_pos = ny * self.line_bytes + (nx >> 3)
                bit_mask = 0x80 >> (nx & 7)
                
                if not (self.fb_bw[byte_pos] & bit_mask):
                    # 黑色像素使物理屏幕变深 32 级 (共 8 阶)
                    self.physical_screen[y, x] = max(0, self.physical_screen[y, x] - 32)

    def refresh_canvas(self):
        """将物理屏幕矩阵转为 Tkinter 图片"""
        img = Image.fromarray(self.physical_screen.astype('uint8'), mode='L')
        img = img.resize((WIDTH*2, HEIGHT*2), Image.NEAREST)
        self.tk_img = ImageTk.PhotoImage(img)
        self.canvas.create_image(0, 0, anchor="nw", image=self.tk_img)

if __name__ == "__main__":
    root = tk.Tk()
    # 尝试解决高清屏模糊问题
    try:
        from ctypes import windll
        windll.shcore.SetProcessDpiAwareness(1)
    except:
        pass
    app = EPDSimulator(root)
    root.mainloop()
