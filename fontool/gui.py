import tkinter as tk
from tkinter import filedialog, messagebox, ttk
import bdfont

class BDFontGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("Gemini 字体转换工具 - 输入框版")
        self.root.geometry("1000x700")

        # 变量存储
        self.ttf_path = tk.StringVar()
        self.font_size = tk.StringVar(value="32")
        self.base_adj = tk.StringVar(value="0")
        self.label_name = tk.StringVar(value="my_font")
        self.out_type = tk.StringVar(value="bin")

        self.setup_ui()

    def setup_ui(self):
        # 主布局：左侧控制 + 右侧预览
        main_paned = ttk.Panedwindow(self.root, orient=tk.HORIZONTAL)
        main_paned.pack(fill="both", expand=True, padx=5, pady=5)

        # --- 左侧控制区 ---
        left_frame = ttk.Frame(main_paned)
        main_paned.add(left_frame, weight=1)

        # 1. 字体选择
        f_font = ttk.LabelFrame(left_frame, text="1. 字体选择", padding=10)
        f_font.pack(fill="x", padx=5, pady=5)
        ttk.Entry(f_font, textvariable=self.ttf_path).pack(side="left", fill="x", expand=True)
        ttk.Button(f_font, text="浏览", width=5, command=self.select_ttf).pack(side="left", padx=5)

        # 2. 字符输入框 (核心修改点)
        f_chars = ttk.LabelFrame(left_frame, text="2. 要生成的字符 (直接在此输入)", padding=10)
        f_chars.pack(fill="both", expand=True, padx=5, pady=5)
        
        # 使用 Text 组件实现多行输入
        self.char_text_area = tk.Text(f_chars, height=8, wrap="char", font=("Microsoft YaHei", 12))
        self.char_text_area.pack(fill="both", expand=True)
        # 默认填入一些常用字符
        self.char_text_area.insert("1.0", "0123456789:.- ")

        # 3. 转换参数
        f_params = ttk.LabelFrame(left_frame, text="3. 转换参数", padding=10)
        f_params.pack(fill="x", padx=5, pady=5)
        
        grid_p = ttk.Frame(f_params)
        grid_p.pack(fill="x")
        ttk.Label(grid_p, text="大小:").grid(row=0, column=0)
        ttk.Entry(grid_p, textvariable=self.font_size, width=8).grid(row=0, column=1, padx=5)
        ttk.Label(grid_p, text="基线调整:").grid(row=0, column=2)
        ttk.Entry(grid_p, textvariable=self.base_adj, width=8).grid(row=0, column=3, padx=5)

        # 4. 输出与执行
        f_out = ttk.LabelFrame(left_frame, text="4. 导出设置", padding=10)
        f_out.pack(fill="x", padx=5, pady=5)
        ttk.Radiobutton(f_out, text=".bin", variable=self.out_type, value="bin").pack(side="left")
        ttk.Radiobutton(f_out, text=".h", variable=self.out_type, value="header").pack(side="left", padx=10)
        ttk.Label(f_out, text="数组名:").pack(side="left")
        ttk.Entry(f_out, textvariable=self.label_name, width=12).pack(side="left", padx=5)

        btn_run = tk.Button(left_frame, text="开始导出字体文件", bg="#2196F3", fg="white", 
                           font=("Arial", 12, "bold"), command=self.run_conversion)
        btn_run.pack(fill="x", padx=5, pady=10, ipady=5)

        # --- 右侧预览区 ---
        right_frame = ttk.LabelFrame(main_paned, text="单字点阵预览", padding=10)
        main_paned.add(right_frame, weight=1)

        f_pre_ctrl = ttk.Frame(right_frame)
        f_pre_ctrl.pack(fill="x")
        ttk.Label(f_pre_ctrl, text="输入字符预览:").pack(side="left")
        self.preview_input = ttk.Entry(f_pre_ctrl, width=5)
        self.preview_input.pack(side="left", padx=5)
        self.preview_input.insert(0, "8")
        ttk.Button(f_pre_ctrl, text="刷新预览", command=self.update_preview).pack(side="left")

        self.canvas = tk.Canvas(right_frame, bg="white", highlightthickness=1)
        self.canvas.pack(fill="both", expand=True, pady=5)

    def select_ttf(self):
        path = filedialog.askopenfilename(filetypes=[("Font Files", "*.ttf *.otf")])
        if path: self.ttf_path.set(path)

    def update_preview(self):
        if not self.ttf_path.get():
            messagebox.showwarning("提示", "请先选择字体文件")
            return
        try:
            char = self.preview_input.get()
            if not char: return
            ucs = ord(char[0])
            bdfont.font_size = int(self.font_size.get())
            bdfont.load_ttf(self.ttf_path.get())
            pg = bdfont.ttf_load_char(ucs)
            self.draw_glyph(pg)
        except Exception as e:
            messagebox.showerror("预览失败", str(e))

    def draw_glyph(self, pg):
        self.canvas.delete("all")
        if not pg: return
        p_size = 10
        off_x, off_y = 30, 30
        self.canvas.create_line(0, off_y + pg.by*p_size, 400, off_y + pg.by*p_size, fill="#ffcccc")
        lsize = (pg.bw + 7) // 8
        for y in range(pg.bh):
            for x in range(pg.bw):
                if pg.bitmap[y * lsize + (x >> 3)] & (0x80 >> (x % 8)):
                    x1, y1 = off_x + x*p_size, off_y + y*p_size
                    self.canvas.create_rectangle(x1, y1, x1+p_size, y1+p_size, fill="black", outline="#eee")
        self.canvas.create_text(off_x, 10, anchor="nw", text=f"Size: {pg.bw}x{pg.bh} | Adv: {pg.advance}", fill="blue")

    def run_conversion(self):
        if not self.ttf_path.get():
            messagebox.showerror("错误", "请选择字体文件")
            return

        # 1. 获取输入框内的所有字符，并去重
        input_content = self.char_text_area.get("1.0", tk.END).strip()
        if not input_content:
            messagebox.showwarning("警告", "请输入要转换的字符")
            return
        
        unique_chars = sorted(list(set(input_content))) # 去重并排序
        
        # 2. 设置 bdfont 的 clist
        for i in range(65536): bdfont.clist[i] = 0
        print(len(unique_chars));
        for char in unique_chars:
            bdfont.clist[ord(char)] = 1

        try:
            # 3. 清理旧缓存并执行
            for i in range(65536): bdfont.ctab[i] = None
            bdfont.font_size = int(self.font_size.get())
            bdfont.load_ttf(self.ttf_path.get())
            bdfont.build_font()
            
            save_ext = ".bin" if self.out_type.get() == "bin" else ".h"
            save_path = filedialog.asksaveasfilename(defaultextension=save_ext)
            if not save_path: return

            if self.out_type.get() == "bin":
                with open(save_path, "wb") as f: f.write(bdfont.font_buf[:bdfont.font_buf_size])
            else:
                bdfont.bin2c(bdfont.font_buf, bdfont.font_buf_size, save_path, self.label_name.get())
            
            messagebox.showinfo("成功", f"导出完成！\n实际包含去重字符数: {len(unique_chars)}\n文件大小: {bdfont.font_buf_size} 字节")
        except Exception as e:
            messagebox.showerror("错误", str(e))

if __name__ == "__main__":
    root = tk.Tk()
    app = BDFontGUI(root)
    root.mainloop()
