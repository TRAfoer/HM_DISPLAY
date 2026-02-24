import math
import os
from PIL import Image

def dither_to_16_levels(img):
    """
    使用 Floyd-Steinberg 抖动算法将图片量化为 16 阶灰度。
    """
    width, height = img.size
    # 定义 16 个标准灰度级 (0, 17, 34 ... 255)
    levels = [int(i * 255 / 15) for i in range(16)]
    
    # 转换为浮点型数据以便在计算误差时不丢失精度
    # 实际上直接操作灰度对象的像素点
    pixels = img.load()
    
    print("开始执行 Floyd-Steinberg 误差扩散...")
    for y in range(height):
        for x in range(width):
            old_val = pixels[x, y]
            # 找到最接近的标准灰度级
            new_val = min(levels, key=lambda v: abs(v - old_val))
            pixels[x, y] = new_val
            
            # 计算量化误差
            err = old_val - new_val
            
            # 将误差扩散到相邻像素
            if x + 1 < width:
                pixels[x + 1, y] = max(0, min(255, int(pixels[x + 1, y] + err * 7 / 16)))
            if y + 1 < height:
                if x > 0:
                    pixels[x - 1, y + 1] = max(0, min(255, int(pixels[x - 1, y + 1] + err * 3 / 16)))
                pixels[x, y + 1] = max(0, min(255, int(pixels[x, y + 1] + err * 5 / 16)))
                if x + 1 < width:
                    pixels[x + 1, y + 1] = max(0, min(255, int(pixels[x + 1, y + 1] + err * 1 / 16)))
    
    # 保存调试预览图
    debug_name = "dithered_debug.jpg"
    img.save(debug_name, "JPEG", quality=95)
    print(f"Debug图已保存至: {debug_name}")
    return img

def generate_dynamic_eink_script(image_path, output_txt="eink_16gray_dithered.txt", screen_w=250, screen_h=122):
    try:
        # 1. 加载图片并缩放到屏幕物理尺寸
        img = Image.open(image_path).convert('L')
        img = img.resize((screen_w, screen_h), Image.Resampling.LANCZOS)
        
        # 2. 执行抖动处理并输出 Debug JPG
        img = dither_to_16_levels(img)
        
    except Exception as e:
        print(f"错误: {e}")
        return

    # 3. 定义 15 个阈值图层
    # 既然图像已经被量化为固定的 16 个值，我们取两级之间的中间值作为阈值
    # 这样可以完美隔离每一层像素
    levels = [int(i * 255 / 15) for i in range(16)]
    thresholds = []
    for i in range(len(levels)-1):
        thresholds.append((levels[i] + levels[i+1]) // 2)
    
    # 排序：从最大的阈值开始（包含最广的浅色层）到最小的阈值（仅最黑层）
    # 这样符合你“从浅到深顺序”发送位图的要求
    thresholds.sort(reverse=True)
    
    with open(output_txt, "w") as f:
        # 写入起始自定义命令
        f.write("93\n95\nw1000\n93\n")
        
        for layer_idx, threshold in enumerate(thresholds):
            layer_count = 0
            for y in range(0, screen_h, 32):
                for x in range(0, screen_w, 32):
                    chunk_w = min(32, screen_w - x)
                    chunk_h = min(32, screen_h - y)
                    bytes_per_row = math.ceil(chunk_w / 8)
                    chunk_data = bytearray(bytes_per_row * chunk_h)
                    has_black_pixel = False
                    
                    for cy in range(chunk_h):
                        for cx in range(chunk_w):
                            px, py = x + cx, y + cy
                            if img.getpixel((px, py)) < threshold:
                                has_black_pixel = True
                                byte_idx = (cy * bytes_per_row) + (cx // 8)
                                bit_shift = 7 - (cx % 8)
                                chunk_data[byte_idx] |= (1 << bit_shift)
                    
                    if not has_black_pixel:
                        continue
                    
                    header = f"94 0f {x:02x} {y:02x} 00 00 {chunk_w:02x} {chunk_h:02x}"
                    data_hex = " ".join(f"{b:02x}" for b in chunk_data)
                    f.write(f"{header} {data_hex}\n")
                    layer_count += 1
            
            # 发完一层插一个 9a
            f.write("9a\n93\n")
            print(f"层级 {layer_idx+1}/15 (阈值 {threshold}) 处理完成，包含 {layer_count} 个数据块")

    print(f"\n全部指令已生成: {output_txt}")

if __name__ == "__main__":
    image_file = "input.jpg"
    if os.path.exists(image_file):
        generate_dynamic_eink_script(image_file)
    else:
        print(f"未找到 {image_file}，请确保图片与脚本在同一目录。")
