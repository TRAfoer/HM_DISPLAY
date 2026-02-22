import sys
import os

try:
    import freetype
except ImportError:
    print("Error: freetype-py is not installed. Please run 'pip install freetype-py'")
    sys.exit(1)

# 全局变量
clist = [0] * 1114112
ctab = [None] * 1114112
total_chars = 0

pixel_size = 0
font_ascent = 0
base_adj = 0
font_size = 14

font_buf = bytearray(0x1000000)
font_buf_size = 0

ft_face = None

class GLYPH:
    def __init__(self):
        self.unicode = 0
        self.bw = 0
        self.bh = 0
        self.bx = 0
        self.by = 0
        self.advance = 0
        self.bitmap = None
        self.bsize = 0

def ucs2utf8(ucs):
    try:
        return chr(ucs)
    except ValueError:
        return ""

def load_list(name):
    global clist
    # --- 关键修改：默认全部设为 0，不抓取任何字符 ---
    for i in range(1114112):
        clist[i] = 0

    # 如果没有指定列表文件，为了防止导出空文件，
    # 我们可以默认只加载 ASCII (0-127)，或者报错提醒
    if name is None:
        print("警告: 未指定列表文件，将默认尝试加载基础 ASCII 字符")
        for i in range(32, 127):
            clist[i] = 1
        return

    try:
        with open(name, "rb") as fp:
            bom = fp.read(2)
            # 必须是 UTF-16 Little Endian (FF FE)
            if bom != b'\xff\xfe':
                print(f"错误: {name} 编码不是 UTF16-LE")
                return

            n = 0
            while True:
                data = fp.read(2)
                if len(data) < 2: break
                ucs = data[0] | (data[1] << 8)
                if ucs > 0x20: # 过滤空格和换行
                    clist[ucs] = 1
                    n += 1
            print(f"已成功从列表加载 {n} 个目标字符")
    except Exception as e:
        print(f"列表加载失败: {e}")

def ttf_load_char(ucs):
    global ft_face, font_size

    index = ft_face.get_char_index(ucs)
    if index == 0:
        print("FT_Get_Char_Index: not found ",index)
        return None

    try:
        ft_face.load_glyph(index, freetype.FT_LOAD_DEFAULT)
    except Exception as e:
        print(f"FT_Load_Glyph({ucs:04x}): error={e}")
        return None

    # 转为单色位图
    ft_face.glyph.render(freetype.FT_RENDER_MODE_MONO)
    bitmap = ft_face.glyph.bitmap

    pg = GLYPH()
    pg.unicode = ucs
    pg.bw = bitmap.width
    pg.bh = bitmap.rows
    pg.bx = ft_face.glyph.bitmap_left
    pg.by = font_size - ft_face.glyph.bitmap_top
    
    # advance 转换 (FT_LOAD_DEFAULT下 advance 是 26.6 格式，模拟 C 代码的 16.16 四舍五入机制)
    # C 代码: (glyph->advance.x + 0x00008000) >> 16
    adv_26_6 = ft_face.glyph.advance.x
    adv_16_16 = adv_26_6 << 10
    pg.advance = (adv_16_16 + 0x00008000) >> 16

    lsize = (pg.bw + 7) // 8
    pg.bsize = lsize * pg.bh
    pg.bitmap = bytearray(pg.bsize)

    # 拷贝单色像素数据，规避 pitch 和 lsize 潜在不一致
    pitch = abs(bitmap.pitch)
    buf = bitmap.buffer
    for y in range(pg.bh):
        src_idx = y * pitch
        dst_idx = y * lsize
        for i in range(lsize):
            if src_idx + i < len(buf):
                pg.bitmap[dst_idx + i] = buf[src_idx + i]

    return pg

def load_ttf(ttf_name):
    global ft_face, total_chars, font_size

    try:
        ft_face = freetype.Face(ttf_name)
    except Exception as e:
        print(f"FT_New_Face({ttf_name}): error")
        return -1

    print(f"FACE: num_fixed_sizes: {ft_face.num_fixed_sizes}")
    for i in range(ft_face.num_fixed_sizes):
        size_obj = ft_face.available_sizes[i]
        print(f"{i:2d}: {size_obj.size//64:2d} {size_obj.width:2d}x{size_obj.height:2d}")

    ft_face.set_pixel_sizes(font_size, font_size)

    total_chars = 0
    for i in range(1114112):
        if clist[i] == 0:
            continue
        pg = ttf_load_char(i)
        ctab[i] = pg
        if pg:
            total_chars += 1

    # 针对7段数字字体的空格，将其宽度处理成和数字一样。
    if font_size > 24 and ctab[0x20] is not None and ctab[0x30] is not None:
        ctab[0x20].advance = ctab[0x30].advance

    return 0

def print_glyph(pg):
    char_str = ucs2utf8(pg.unicode)
    print(f"\nchar {pg.unicode:04x} [{char_str}]")
    print(f"  bw={pg.bw:<2d} bh={pg.bh:<2d} bx={pg.bx:<2d} by={pg.by:<2d}  adv={pg.advance}")

    lsize = (pg.bw + 7) // 8
    for y in range(pg.bh):
        sys.stdout.write("    ")
        for x in range(pg.bw):
            byte_val = pg.bitmap[y * lsize + (x >> 3)]
            if byte_val & (0x80 >> (x % 8)):
                sys.stdout.write("*")
            else:
                sys.stdout.write(".")
        sys.stdout.write("\n")

def dump_glyph():
    for i in range(1114112):
        if ctab[i]:
            print_glyph(ctab[i])

def dump_list():
    for i in range(1114112):
        if ctab[i]:
            char_str = ucs2utf8(i)
            print(f"{i:04x}={char_str}")

# 注意：C代码原名叫 write_be16 但它执行的是 小端(Little Endian) 操作！这里维持相同的物理特性。
def write_be16(p, offset, val):
    p[offset] = val & 0xff
    p[offset + 1] = (val >> 8) & 0xff

def build_font():
    global font_buf, font_buf_size
    
    write_be16(font_buf, 0, total_chars)
    offset = total_chars * 4 + 2

    p = 2
    for i in range(1114112):
        if ctab[i]:
            pg = ctab[i]
            write_be16(font_buf, p, i)
            write_be16(font_buf, p + 2, offset)
            p += 4
            offset += pg.bsize + 5

    for i in range(1114112):
        if ctab[i]:
            pg = ctab[i]
            font_buf[p + 0] = pg.advance & 0xff
            font_buf[p + 1] = pg.bw & 0xff
            font_buf[p + 2] = pg.bh & 0xff
            font_buf[p + 3] = pg.bx & 0xff
            font_buf[p + 4] = pg.by & 0xff
            p += 5
            
            font_buf[p : p + pg.bsize] = pg.bitmap
            p += pg.bsize

    font_buf_size = p

def bin2c(buffer, size, file_name, label_name):
    try:
        with open(file_name, "w") as dest:
            dest.write(f"#ifndef __{label_name}__\n")
            dest.write(f"#define __{label_name}__\n\n")
            dest.write(f"#define {label_name}_size  {size}\n")
            dest.write(f"static const unsigned char {label_name}[] __attribute__((aligned(4))) = {{")

            for i in range(size):
                if (i % 16) == 0:
                    dest.write("\n\t")
                else:
                    dest.write(" ")
                dest.write(f"0x{buffer[i]:02x},")

            dest.write("\n};\n\n#endif\n")
    except Exception as e:
        print(f"Failed to open/create {file_name}.")
        return 1
    return 0

def main():
    global base_adj, font_size

    flags = 0
    bdf_name = None
    font_name = None
    list_name = None
    label_name = None

    if len(sys.argv) == 1:
        print("\nUsage:")
        print("\tbdfont [-dg] [-dl] [-l list] [-adj base] [-s size] [-c name] [-h name label] font_file")
        print("\t\t-dg          dump glyph")
        print("\t\t-dl          dump char list")
        print("\t\t-l   list    load char list")
        print("\t\t-adj base    adjust base line")
        print("\t\t-s   size    set font size(for ttf)")
        print("\t\t-c   name")
        print("\t\t             output binary font")
        print("\t\t-h   name label")
        print("\t\t             output c header font")
        return 0

    i = 1
    while i < len(sys.argv):
        arg = sys.argv[i]
        if arg == "-dg":
            flags |= 1
        elif arg == "-dl":
            flags |= 2
        elif arg == "-l":
            list_name = sys.argv[i+1]
            i += 1
        elif arg == "-adj":
            base_adj = int(sys.argv[i+1])
            i += 1
        elif arg == "-s":
            font_size = int(sys.argv[i+1])
            i += 1
        elif arg == "-c":
            flags |= 4
            font_name = sys.argv[i+1]
            i += 1
        elif arg == "-h":
            flags |= 8
            font_name = sys.argv[i+1]
            label_name = sys.argv[i+2]
            i += 2
        elif bdf_name is None:
            bdf_name = arg
        i += 1

    load_list(list_name)

    retv = load_ttf(bdf_name)
    if retv < 0:
        return -1

    if flags & 1:
        dump_glyph()
    elif flags & 2:
        dump_list()
    elif flags & 4:
        build_font()
        with open(font_name, "wb") as fp:
            fp.write(font_buf[:font_buf_size])
    elif flags & 8:
        build_font()
        bin2c(font_buf, font_buf_size, font_name, label_name)

    return 0

if __name__ == "__main__":
    sys.exit(main())
