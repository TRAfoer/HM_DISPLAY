import tkinter as tk
from tkinter import filedialog, messagebox
from PIL import Image, ImageTk, ImageEnhance
import numpy as np
import math
import os

class EinkGeneratorGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("Gemini Eink 16-Gray Pro (可调参数版)")
        self.root.geometry("1000x700")

        self.input_path = ""
        self.processed_img = None
        self.current_mode = "threshold"
        self.screen_w = 250
        self.screen_h = 122
        self.levels = [int(i * 255 / 15) for i in range(16)]

        # --- UI 布局 ---
        control_frame = tk.Frame(root, width=350, padx=20, pady=20)
        control_frame.pack(side=tk.LEFT, fill=tk.Y)

        tk.Button(control_frame, text="1. 选择图片", command=self.load_image, width=25).pack(pady=10)

        # 参数调节区
        tk.Label(control_frame, text="--- 参数实时调节 ---", fg="blue").pack(pady=5)
        
        tk.Label(control_frame, text="对比度 (Contrast):").pack(anchor="w")
        self.scale_contrast = tk.Scale(control_frame, from_=0.5, to=2.5, resolution=0.1, orient=tk.HORIZONTAL, command=self.auto_refresh)
        self.scale_contrast.set(1.0)
        self.scale_contrast.pack(fill=tk.X)

        tk.Label(control_frame, text="抖动强度 (Dither Strength):").pack(anchor="w")
        self.scale_strength = tk.Scale(control_frame, from_=0.0, to=1.0, resolution=0.05, orient=tk.HORIZONTAL, command=self.auto_refresh)
        self.scale_strength.set(0.5)
        self.scale_strength.pack(fill=tk.X)

        # 算法选择
        tk.Label(control_frame, text="--- 算法切换 ---").pack(pady=10)
        self.mode_var = tk.StringVar(value="threshold")
        tk.Radiobutton(control_frame, text="阈值判断 (无抖动)", variable=self.mode_var, value="threshold", command=self.refresh).pack(anchor="w")
        tk.Radiobutton(control_frame, text="8x8 Bayer 矩阵", variable=self.mode_var, value="bayer", command=self.refresh).pack(anchor="w")
        tk.Radiobutton(control_frame, text="Floyd-Steinberg 扩散", variable=self.mode_var, value="floyd", command=self.refresh).pack(anchor="w")

        tk.Button(control_frame, text="生成指令文件 (9a 93版)", command=self.generate_script, bg="#4CAF50", fg="white", height=2).pack(fill=tk.X, pady=20)

        self.log_text = tk.Text(control_frame, height=8, width=40, font=("Consolas", 9))
        self.log_text.pack()

        # 右侧预览
        self.preview_frame = tk.Frame(root, bg="#222", padx=10, pady=10)
        self.preview_frame.pack(side=tk.RIGHT, expand=True, fill=tk.BOTH)
        self.img_label = tk.Label(self.preview_frame, bg="#222")
        self.img_label.pack(expand=True)

    def log(self, msg):
        self.log_text.insert(tk.END, msg + "\n")
        self.log_text.see(tk.END)

    def load_image(self):
        file_path = filedialog.askopenfilename(filetypes=[("Images", "*.jpg *.png *.bmp *.jpeg")])
        if file_path:
            self.input_path = file_path
            self.refresh()

    def auto_refresh(self, _=None):
        if self.input_path: self.refresh()

    def refresh(self):
        mode = self.mode_var.get()
        strength = self.scale_strength.get()
        contrast = self.scale_contrast.get()

        # 1. 基础预处理
        img = Image.open(self.input_path).convert('L').resize((self.screen_w, self.screen_h), Image.Resampling.LANCZOS)
        
        # 2. 对比度增强
        enhancer = ImageEnhance.Contrast(img)
        img = enhancer.enhance(contrast)
        
        img_arr = np.array(img, dtype=float)

        if mode == "threshold":
            res_arr = np.array([min(self.levels, key=lambda x: abs(x - v)) for v in img_arr.flatten()]).reshape(img_arr.shape)
            
        elif mode == "bayer":
            bayer_matrix = np.array([
                [ 0, 32,  8, 40,  2, 34, 10, 42], [48, 16, 56, 24, 50, 18, 58, 26],
                [12, 44,  4, 36, 14, 46,  6, 38], [60, 28, 52, 20, 62, 30, 54, 22],
                [ 3, 35, 11, 43,  1, 33,  9, 41], [51, 19, 59, 27, 49, 17, 57, 25],
                [15, 47,  7, 39, 13, 45,  5, 37], [63, 31, 55, 23, 61, 29, 53, 21]
            ]) * (255 / 64)
            for y in range(self.screen_h):
                for x in range(self.screen_w):
                    old_v = img_arr[y, x]
                    # 强度介入：offset 乘上 strength
                    offset = (bayer_matrix[y % 8, x % 8] - 128) * strength
                    new_v = min(self.levels, key=lambda x: abs(x - (old_v + offset)))
                    img_arr[y, x] = new_v
            res_arr = img_arr

        elif mode == "floyd":
            for y in range(self.screen_h):
                for x in range(self.screen_w):
                    old_v = img_arr[y, x]
                    new_v = min(self.levels, key=lambda x: abs(x - old_v))
                    img_arr[y, x] = new_v
                    err = (old_v - new_v) * strength # 强度控制误差扩散比例
                    if x + 1 < self.screen_w: img_arr[y, x+1] += err * 7/16
                    if y + 1 < self.screen_h:
                        if x > 0: img_arr[y+1, x-1] += err * 3/16
                        img_arr[y+1, x] += err * 5/16
                        if x + 1 < self.screen_w: img_arr[y+1, x+1] += err * 1/16
            res_arr = np.clip(img_arr, 0, 255)

        self.processed_img = Image.fromarray(res_arr.astype(np.uint8))
        self.update_preview()

    def update_preview(self):
        # 放大预览
        display_img = self.processed_img.resize((self.screen_w*3, self.screen_h*3), Image.Resampling.NEAREST)
        tk_img = ImageTk.PhotoImage(display_img)
        self.img_label.config(image=tk_img)
        self.img_label.image = tk_img

    def generate_script(self):
        if not self.processed_img: return
        output_txt = "eink_16gray_commands.txt"
        thresholds = [int(255 - (i * 15.9)) for i in range(1, 16)]
        
        with open(output_txt, "w") as f:
            f.write("93\n95\nw1000\n93\n")
            for th in thresholds:
                for y in range(0, self.screen_h, 32):
                    for x in range(0, self.screen_w, 32):
                        cw, ch = min(32, self.screen_w - x), min(32, self.screen_h - y)
                        bpr = math.ceil(cw / 8)
                        data = bytearray(bpr * ch)
                        has_px = False
                        for cy in range(ch):
                            for cx in range(cw):
                                if self.processed_img.getpixel((x+cx, y+cy)) < th:
                                    has_px = True
                                    data[(cy*bpr) + (cx//8)] |= (1 << (7 - (cx%8)))
                        if has_px:
                            f.write(f"94 0f {x:02x} {y:02x} 00 00 {cw:02x} {ch:02x} {' '.join(f'{b:02x}' for b in data)}\n")
                f.write("9a\n93\n")
        self.log(f"保存成功: {output_txt}")
        messagebox.showinfo("完成", "指令文件已生成")

if __name__ == "__main__":
    root = tk.Tk()
    app = EinkGeneratorGUI(root)
    root.mainloop()
