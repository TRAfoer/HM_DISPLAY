import math
import os
import numpy as np
from PIL import Image

def ordered_dithering_8_levels(img):
    """
    使用 Bayer Matrix (Ordered Dithering) 将图片量化为 8 阶灰度。
    这种算法点位固定，在墨水屏上表现比误差扩散更稳。
    """
    width, height = img.size
    # 定义 8 个目标灰度级
    levels = [int(i * 255 / 7) for i in range(8)]
    
    # 8x8 Bayer Matrix 阈值矩阵
    bayer_matrix = np.array([
        [ 0, 32,  8, 40,  2, 34, 10, 42],
        [48, 16, 56, 24, 50, 18, 58, 26],
        [12, 44,  4, 36, 14, 46,  6, 38],
        [60, 28, 52, 20, 62, 30, 54, 22],
        [ 3, 35, 11, 43,  1, 33,  9, 41],
        [51, 19, 59, 27, 49, 17, 57, 25],
        [15, 47,  7, 39, 13, 45,  5, 37],
        [63, 31, 55, 23, 61, 29, 53, 21]
    ]) * (255 / 64) # 缩放到 0-255

    # 处理图像
    img_array = np.array(img, dtype=float)
    for y in range(height):
        for x in range(width):
            # 获取当前像素对应的矩阵阈值
            threshold = bayer_matrix[y % 8, x % 8]
            old_val = img_array[y, x]
            
            # 根据阈值决定落入哪个阶梯（让图片稍微偏亮处理，给物理层留裕量）
            # 我们在原像素上加一个微小的扰动
            adjusted_val = old_val + (threshold - 128) * 0.5 
            new_val = min(levels, key=lambda v: abs(v - adjusted_val))
            img_array[y, x] = new_val
    
    new_img = Image.fromarray(img_array.astype(np.uint8))
    new_img.save("dithered_8level_debug.jpg", "JPEG", quality=95)
    print("Debug图已保存: dithered_8level_debug.jpg")
    return new_img

def generate_8gray_script(image_path, output_txt="eink_8gray_cmds.txt", screen_w=250, screen_h=122):
    try:
        img = Image.open(image_path).convert('L').resize((screen_w, screen_h), Image.Resampling.LANCZOS)
        # 1. 执行 8 阶有序抖动
        img = ordered_dithering_8_levels(img)
    except Exception as e:
        print(f"错误: {e}")
        return

    # 2. 8阶对应 7 个阈值图层 (因为 0 是纯黑，我们不需要为纯白发位图)
    levels = [int(i * 255 / 7) for i in range(8)]
    thresholds = []
    for i in range(len(levels)-1):
        thresholds.append((levels[i] + levels[i+1]) // 2)
    thresholds.sort(reverse=True) # 自浅至深
    
    with open(output_txt, "w") as f:
        f.write("93\n95\nw1000\n93\n")
        
        for layer_idx, threshold in enumerate(thresholds):
            layer_count = 0
            for y in range(0, screen_h, 32):
                for x in range(0, screen_w, 32):
                    chunk_w, chunk_h = min(32, screen_w - x), min(32, screen_h - y)
                    bytes_per_row = math.ceil(chunk_w / 8)
                    chunk_data = bytearray(bytes_per_row * chunk_h)
                    has_black = False
                    
                    for cy in range(chunk_h):
                        for cx in range(chunk_w):
                            if img.getpixel((x + cx, y + cy)) < threshold:
                                has_black = True
                                chunk_data[(cy * bytes_per_row) + (cx // 8)] |= (1 << (7 - (cx % 8)))
                    
                    if has_black:
                        header = f"94 0f {x:02x} {y:02x} 00 00 {chunk_w:02x} {chunk_h:02x}"
                        f.write(f"{header} {' '.join(f'{b:02x}' for b in chunk_data)}\n")
                        layer_count += 1
            f.write("9a\n93\n")
            print(f"层级 {layer_idx+1}/7 (阈值 {threshold}) 完成，块数: {layer_count}")

if __name__ == "__main__":
    generate_8gray_script("input.jpg")
