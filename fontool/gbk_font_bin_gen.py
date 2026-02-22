import freetype
import struct

# 配置参数
FONT_FILE = 'XiuZhenXiangSuTi.ttf' # 替换为你的 6x8 字体文件路径
OUTPUT_BIN = 'font_gb2312_6x8.bin'
FONT_SIZE = 8  # 字体点阵高度

def generate_gb2312_bin():
    face = freetype.Face(FONT_FILE)
    face.set_pixel_sizes(0, FONT_SIZE)

    # GB2312 范围：高位 0xA1-0xF7, 低位 0xA1-0xFE
    # 这包含了所有常用汉字、全角标点、希腊字母等
    start_h, end_h = 0xA1, 0xF7
    start_l, end_l = 0xA1, 0xFE

    total_chars = 0
    with open(OUTPUT_BIN, 'wb') as f:
        for h in range(start_h, end_h + 1):
            for l in range(start_l, end_l + 1):
                # 拼接 GBK 字节并转为字符
                try:
                    char_bytes = bytes([h, l])
                    char = char_bytes.decode('gbk')
                except UnicodeDecodeError:
                    # 如果该编码无效，填充 8 字节空数据保持对齐
                    f.write(b'\x00' * 8)
                    continue

                # 提取位图
                face.load_char(char, freetype.FT_LOAD_RENDER | freetype.FT_LOAD_TARGET_MONO)
                bitmap = face.glyph.bitmap
                
                # 将 6x8 像素转为 8 字节 (每行 1 字节)
                # 即使是 6 像素宽，我们也占 8 位，方便单片机处理
                char_data = bytearray(8)
                
                # 只有当位图存在时才处理
                if bitmap.buffer:
                    rows = bitmap.rows
                    width = bitmap.width
                    pitch = bitmap.pitch
                    
                    for y in range(min(rows, 8)):
                        # 简单的位图转换
                        for x in range(min(width, 8)):
                            byte_idx = y * pitch + (x >> 3)
                            if bitmap.buffer[byte_idx] & (0x80 >> (x & 7)):
                                char_data[y] |= (0x80 >> x)

                f.write(char_data)
                total_chars += 1

    print(f"转换完成！")
    print(f"生成的字库包含: {total_chars} 个编码位置")
    print(f"文件大小: {os.path.getsize(OUTPUT_BIN) / 1024:.2f} KB")
    print(f"建议烧录地址: 0x30000")

import os
if __name__ == "__main__":
    generate_gb2312_bin()
