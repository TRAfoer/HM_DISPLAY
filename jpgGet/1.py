import tkinter as tk
from tkinter import filedialog, messagebox
from PIL import Image, ImageTk, ImageOps
import os

class InkScreenTool:
    def __init__(self, root):
        self.root = root
        self.root.title("墨水屏取模助手 - Gemini版")
        self.root.geometry("600x750")

        self.file_path = ""
        self.processed_image = None
        self.tk_image = None

        # --- 第一部分：文件选择 ---
        frame_file = tk.LabelFrame(root, text=" 1. 选择图片 ", padx=10, pady=10)
        frame_file.pack(fill="x", padx=20, pady=10)
        
        self.btn_browse = tk.Button(frame_file, text="打开图片", command=self.load_image)
        self.btn_browse.pack(side="left")
        
        self.lbl_filename = tk.Label(frame_file, text="请选择 JPG/PNG/BMP...")
        self.lbl_filename.pack(side="left", padx=10)

        # --- 第二部分：参数设置 ---
        frame_para = tk.LabelFrame(root, text=" 2. 导出参数 ", padx=10, pady=10)
        frame_para.pack(fill="x", padx=20, pady=10)

        tk.Label(frame_para, text="目标宽度:").grid(row=0, column=0)
        self.ent_w = tk.Entry(frame_para, width=10)
        self.ent_w.insert(0, "250")
        self.ent_w.grid(row=0, column=1, padx=5)

        tk.Label(frame_para, text="目标高度:").grid(row=0, column=2)
        self.ent_h = tk.Entry(frame_para, width=10)
        self.ent_h.insert(0, "122")
        self.ent_h.grid(row=0, column=3, padx=5)

        self.mode_var = tk.StringVar(value="dither")
        tk.Radiobutton(frame_para, text="抖动 (适合照片)", variable=self.mode_var, value="dither").grid(row=1, column=0, columnspan=2, pady=5)
        tk.Radiobutton(frame_para, text="阈值 (适合图标)", variable=self.mode_var, value="threshold").grid(row=1, column=2, columnspan=2)

        # --- 第三部分：预览 ---
        frame_view = tk.LabelFrame(root, text=" 3. 预览 (黑色代表墨水屏黑点) ", padx=10, pady=10)
        frame_view.pack(fill="both", expand=True, padx=20, pady=10)

        self.btn_preview = tk.Button(frame_view, text="生成预览", bg="#2196F3", fg="white", command=self.update_preview)
        self.btn_preview.pack(pady=5)

        self.canvas = tk.Label(frame_view, bg="#f0f0f0")
        self.canvas.pack(fill="both", expand=True)

        # --- 第四部分：导出 ---
        self.btn_export = tk.Button(root, text="导出 C 语言数组 (.h)", bg="#4CAF50", fg="white", font=("Arial", 12, "bold"), command=self.export_c_array)
        self.btn_export.pack(fill="x", padx=20, pady=20)

    def load_image(self):
        path = filedialog.askopenfilename(filetypes=[("Images", "*.jpg *.png *.jpeg *.bmp")])
        if path:
            self.file_path = path
            self.lbl_filename.config(text=os.path.basename(path))

    def process_logic(self, target_w, target_h):
        """核心处理逻辑：等比例缩放 + 居中填充"""
        img = Image.open(self.file_path).convert('L')
        
        # 使用 ImageOps.contain 保持比例缩放到框内
        # 或者手动计算：
        img.thumbnail((target_w, target_h), Image.Resampling.LANCZOS)
        
        # 创建底色为白色的画布
        new_img = Image.new('L', (target_w, target_h), 255)
        # 居中粘贴
        offset = ((target_w - img.size[0]) // 2, (target_h - img.size[1]) // 2)
        new_img.paste(img, offset)

        # 转为单色
        if self.mode_var.get() == "dither":
            final = new_img.convert('1', dither=Image.FLOYDSTEINBERG)
        else:
            final = new_img.point(lambda x: 0 if x < 128 else 255, '1')
        
        return final

    def update_preview(self):
        if not self.file_path:
            messagebox.showwarning("提示", "请先打开一张图片")
            return
        
        try:
            tw, th = int(self.ent_w.get()), int(self.ent_h.get())
            self.processed_image = self.process_logic(tw, th)
            
            # 放大预览以防看不清，使用 NEAREST 保持像素感
            render_img = self.processed_image.resize((tw*2, th*2), Image.NEAREST)
            self.tk_image = ImageTk.PhotoImage(render_img)
            self.canvas.config(image=self.tk_image)
        except Exception as e:
            messagebox.showerror("错误", str(e))

    def export_c_array(self):
        if not self.processed_image:
            messagebox.showwarning("提示", "请先生成预览")
            return

        save_path = filedialog.asksaveasfilename(defaultextension=".h", filetypes=[("Header file", "*.h")])
        if not save_path: return

        w, h = self.processed_image.size
        bytes_per_line = (w + 7) // 8
        
        lines = []
        lines.append(f"// Image: {os.path.basename(self.file_path)}")
        lines.append(f"// Resolution: {w}x{h}")
        lines.append(f"const unsigned char image_{w}x{h}[{h}][{bytes_per_line}] = {{")

        for y in range(h):
            row = []
            for b in range(bytes_per_line):
                byte_val = 0
                for bit in range(8):
                    x = b * 8 + bit
                    if x < w:
                        # Pillow '1' 模式下，0为黑，255为白
                        pixel = self.processed_image.getpixel((x, y))
                        if pixel == 0: # 黑色
                            byte_val |= (1 << (7 - bit))
                row.append(f"0x{byte_val:02X}")
            
            comma = "," if y < h - 1 else ""
            lines.append(f"\t{{{', '.join(row)}}}{comma}")
        
        lines.append("};")

        with open(save_path, "w", encoding="utf-8") as f:
            f.write("\n".join(lines))
        messagebox.showinfo("成功", "导出成功！")

if __name__ == "__main__":
    root = tk.Tk()
    app = InkScreenTool(root)
    root.mainloop()
