

#include "epd.h"

/******************************************************************************/

// FB参数
int fb_w;
int fb_h;

#define FB_SIZE 4736
u8 fb_bw[FB_SIZE];
u8 fb_rr[FB_SIZE];

/******************************************************************************/
void draw_pixel(int x, int y, int color)
{
	int nx, ny;
	int rmode = scr_mode&0x03;
	
	if(rmode==0){
		nx = x;
		ny = y;
	}else if(rmode==1){
		nx = scr_w-1-y;
		ny = x;
	}else if(rmode==2){
		nx = scr_w-1-x;
		ny = scr_h-1-y;
	}else if(rmode==3){
		nx = y;
		ny = scr_h-1-x;
	}
	//if(scr_mode&MIRROR_H)nx += scr_padding;

	// 2. 核心计算：确保 nx=0 对应字节最高位 0x80
  int byte_pos = ny * line_bytes + (nx >> 3);
  int bit_mask = 0x80 >> (nx & 7);
	switch (color) {
        case BLACK: // 0
            fb_bw[byte_pos] &= ~bit_mask; // 清零变黑
            break;

        case WHITE: // 1
            fb_bw[byte_pos] |= bit_mask;  // 置位变白
            break;

        case RED:   // 2
            if (scr_mode & EPD_BWR) {
                fb_rr[byte_pos] |= bit_mask;
            }
            break;

        case SWAP:  // 3
            fb_bw[byte_pos] ^= bit_mask; // 异或翻转
            break;

        default:
            // 未定义的颜色不进行操作
            break;
    }
	
}

void draw_hline(int y, int x1, int x2, int color)
{
	int x;
	if (x1 > x2)
	{
		x = x1;
		x1 = x2;
		x2 = x;
	}

	for (x = x1; x <= x2; x += 1)
	{
		draw_pixel(x, y, color);
	}
}

void draw_vline(int x, int y1, int y2, int color)
{
	int y;
	if (y1 > y2)
	{
		x = y1;
		y1 = y2;
		y2 = x;
	}

	for (y = y1; y <= y2; y += 1)
	{
		draw_pixel(x, y, color);
	}
}
void draw_line(int x1, int y1, int x2, int y2, int color)
{
    int dx =  abs(x2 - x1);
    int dy = -abs(y2 - y1);
    int sx = x1 < x2 ? 1 : -1;
    int sy = y1 < y2 ? 1 : -1;
    int err = dx + dy;
    int e2;

    while (1) {
        // 调用你刚刚改好的带 switch 和越界检查的 draw_pixel
        draw_pixel(x1, y1, color);

        if (x1 == x2 && y1 == y2) break;

        e2 = 2 * err;
        if (e2 >= dy) {
            err += dy;
            x1 += sx;
        }
        if (e2 <= dx) {
            err += dx;
            y1 += sy;
        }
    }
}
void draw_rect(int x1, int y1, int x2, int y2, int color)
{
	draw_hline(y1, x1, x2, color);
	draw_hline(y2, x1, x2, color);
	draw_vline(x1, y1, y2, color);
	draw_vline(x2, y1, y2, color);
}

void draw_box(int x1, int y1, int x2, int y2, int color)
{
	if(x2-x1>y2-y1){
	int y;

	for (y = y1; y <= y2; y++)
	{
		draw_hline(y, x1, x2, color);
	}
	}else{
	int x;

	for (x = x1; x <= x2; x++)
	{
		draw_vline(x,y1,y2,color);
	}
	}
}

/**
 * @brief 绘制空心三角形
 * @param x1, y1  顶点1
 * @param x2, y2  顶点2
 * @param x3, y3  顶点3
 * @param color   颜色 (BLACK, WHITE, RED, SWAP)
 */
void draw_triangle(int x1, int y1, int x2, int y2, int x3, int y3, int color)
{
    draw_line(x1, y1, x2, y2, color);
    draw_line(x2, y2, x3, y3, color);
    draw_line(x3, y3, x1, y1, color);
}
/**
 * @brief 快速绘制实心三角形（填充）
 * 使用扫描线算法，利用定点数运算避开浮点开销，并调用已有的 draw_hline
 */
void draw_filled_triangle(int x1, int y1, int x2, int y2, int x3, int y3, int color)
{
    // 1. 排序：确保 y1 <= y2 <= y3
    if (y1 > y2) { int t; t=y1;y1=y2;y2=t; t=x1;x1=x2;x2=t; }
    if (y1 > y3) { int t; t=y1;y1=y3;y3=t; t=x1;x1=x3;x3=t; }
    if (y2 > y3) { int t; t=y2;y2=y3;y3=t; t=x2;x2=x3;x3=t; }

    if (y1 == y3) return; // 零高度三角形直接返回

    // 2. 扫描线计算
    // 使用 16 位左移作为定点数，避免 float 运算
    int dx13 = (y3 != y1) ? ((x3 - x1) << 16) / (y3 - y1) : 0;
    int dx12 = (y2 != y1) ? ((x2 - x1) << 16) / (y2 - y1) : 0;
    int dx23 = (y3 != y2) ? ((x3 - x2) << 16) / (y3 - y2) : 0;

    int curx1 = x1 << 16;
    int curx2 = x1 << 16;

    // 绘制平底部分 (从 y1 到 y2)
    for (int y = y1; y < y2; y++) {
        draw_hline(y, curx1 >> 16, curx2 >> 16, color);
        curx1 += dx13;
        curx2 += dx12;
    }

    // 绘制平顶部分 (从 y2 到 y3)
    curx2 = x2 << 16; // 切换到第二条边的起点
    for (int y = y2; y <= y3; y++) {
        draw_hline(y, curx1 >> 16, curx2 >> 16, color);
        curx1 += dx13;
        curx2 += dx23;
    }
}



/**
 * 绘制二维码到墨水屏
 *
 * @param start_x   绘制起始X位置
 * @param start_y   绘制起始Y位置
 * @param pix_size  每个二维码像素点的宽高（单位像素）
 * @param img       二维码C数组，尺寸31x4，每行4字节
 */
void draw_qr_code(
	int start_x,
	int start_y,
	int pix_size,
	const unsigned char img[31][4])
{
	for (int y = 0; y < 31; y++)
	{
		for (int x = 0; x < 31; x++)
		{

			int byte_idx = x / 8;	   // 每4字节一行，8bit一个字节
			int bit_idx = 7 - (x % 8); // 图像从高位到低位存储
			int bit = (img[y][byte_idx] >> bit_idx) & 1;
			int color = (bit == 0) ? WHITE : BLACK;

			// 放大绘制
			int x1 = start_x + x * pix_size;
			int y1 = start_y + y * pix_size;
			int x2 = x1 + pix_size - 1;
			int y2 = y1 + pix_size - 1;

			draw_box(x1, y1, x2, y2, color);
		}
	}
}

/**
 * @brief 绘制通用位图
 * @param start_x 绘制起点的 X 坐标
 * @param start_y 绘制起点的 Y 坐标
 * @param width   图片的像素宽度
 * @param height  图片的像素高度
 * @param img     图片数据指针 (每行字节数 = ceil(width/8))
 */
void draw_bitmap(int start_x, int start_y, int width, int height, const unsigned char *img)
{
    // 计算每一行占用的字节数
    int bytes_per_line = (width + 7) / 8;

    for (int y = 0; y < height; y++)
    {
        for (int x = 0; x < width; x++)
        {
            // 找到当前像素在 img 数组中的字节索引
            // img + y * bytes_per_line 定位到当前行
            int byte_idx = x / 8;
            int bit_idx = 7 - (x % 8); // 假设高位在前
            
            // 提取对应位 (0 或 1)
            int bit = (img[y * bytes_per_line + byte_idx] >> bit_idx) & 1;
            
            
            int percolor = (bit == 0) ? WHITE : BLACK;
					
            // 调用画像素点函数
            draw_pixel(start_x + x, start_y + y, percolor);
        }
    }
}
/******************************************************************************/

#include "sfont.h"
#include "sfont16.h"
#include "font50.h"
#include "font66.h"
#include "KH_Dot_Hatcyoubori_16.h"
//typedef unsigned  char  u8;写在头文件
const u8 *font_list[6] = {
	sfont,
	F_DSEG7_50,
	sfont16,
	F_DSEG7_66,
	KH_Dot_Hatcyoubori_16,
};

const u8 *current_font = (u8 *)sfont;
static int font_scale = 1; // 默认为 1 倍

void fb_set_scale(int scale)
{
    if (scale < 1) scale = 1;
    font_scale = scale;
}

int select_font(int id)
{
	if(id>=sizeof(font_list))return 0;
	current_font = font_list[id];
	return 0;
}

static const u8 *find_font(const u8 *font, int ucs)
{
	int total = *(u16 *)font;
	int i;

	for (i = 0; i < total; i++)
	{
		if (*(u16 *)(font + 2 + i * 4 + 0) == ucs)
		{
			int offset = *(u16 *)(font + 2 + i * 4 + 2);
			// printk("  %04x at %04x\n", ucs, offset);
			return font + offset;
		}
	}

	return find_font(font_list[0],ucs);
}

int fb_draw_font_info(int x, int y, const u8 *font_data, int color)
{
	int r, c, sr, sc; // 增加缩放循环变量

	int ft_adv = font_data[0];
	int ft_bw  = font_data[1];
	int ft_bh  = font_data[2];
	int ft_bx  = (signed char)font_data[3];
	int ft_by  = (signed char)font_data[4];
	int ft_lsize = (ft_bw + 7) / 8;
	font_data += 5;

	// 坐标和偏移也要乘以缩放倍数
	x += ft_bx * font_scale;
	y += ft_by * font_scale;

	for (r = 0; r < ft_bh; r++)
	{
		for (c = 0; c < ft_bw; c++)
		{
			int b = font_data[c >> 3];
			int mask = 0x80 >> (c % 8);
			if (b & mask)
			{
				// 原本画一个点 draw_pixel(x + c, y, color);
				// 现在画一个 scale * scale 的矩形块
				for (sr = 0; sr < font_scale; sr++)
				{
					for (sc = 0; sc < font_scale; sc++)
					{
						draw_pixel(x + c * font_scale + sc, y + r * font_scale + sr, color);
					}
				}
			}
		}
		font_data += ft_lsize;
		// y轴跳步不需要手动 y+=1 了，由外层的 r * font_scale 控制逻辑
	}

	return ft_adv * font_scale; // 返回值也要缩放，确保下一个字符位置正确
}

int fb_draw_font(int x, int y, int ucs, int color)
{
	const u8 *font_data = find_font(current_font, ucs);
	if (font_data == NULL)
	{
		printf("fb_draw %04x: not found!\n", ucs);
		return -1;
	}

	return fb_draw_font_info(x, y, font_data, color);
}

// 获取指定字符的宽度 (Advance)
int fb_get_font_width(int ucs)
{
    const u8 *font_data = find_font(current_font, ucs);
    if (font_data == NULL) return 0;
    
    return font_data[0]; // 返回 ft_adv
}

// 获取当前字库的通用高度
// 逻辑：字库本身不存储全局高度，通常取某个常用字符（如 'A' 或 '0'）的高度作为参考
int fb_get_font_height()
{
    // 尝试获取数字 '0' 的高度
    const u8 *font_data = find_font(current_font, '0');
    if (font_data == NULL) return 0; // 默认保底值
    
    return font_data[2]; // 返回 ft_bh
}

static int utf8_to_ucs(char **ustr)
{
	u8 *str = (u8 *)*ustr;
	int ucs = 0;

	if (*str == 0)
	{
		return 0;
	}
	else if (*str < 0x80)
	{
		*ustr = (char *)str + 1;
		return *str;
	}
	else if (*str < 0xe0)
	{
		ucs = ((str[0] & 0x1f) << 6) | (str[1] & 0x3f);
		*ustr = (char *)str + 2;
		return ucs;
	}
	else
	{
		ucs = ((str[0] & 0x0f) << 12) | ((str[1] & 0x3f) << 6) | (str[2] & 0x3f);
		*ustr = (char *)str + 3;
		return ucs;
	}
}
/**
 * @brief 计算多行文本的实际显示宽高
 * @param str    输入的UTF-8字符串
 * @param out_w  输出总宽度
 * @param out_h  输出总高度
 */
void get_text_dimension(const char *str, int *out_w, int *out_h)
{
    int curr_w = 0;
    int max_w = 0;
    int line_cnt = 1;
    int line_h = fb_get_font_height() * font_scale;
    
    char *ptr = (char *)str;
    while (1)
    {
        int ch = utf8_to_ucs(&ptr);
        if (ch == 0) break;

        if (ch == '\n') {
            if (curr_w > max_w) max_w = curr_w;
            curr_w = 0;
            line_cnt++;
        } else {
            int adv = fb_get_font_width(ch) * font_scale;
					curr_w += adv<=0?8:adv;
        }
    }
    if (curr_w > max_w) max_w = curr_w;

    *out_w = max_w;
    *out_h = line_cnt * line_h;
}
void draw_text(int x, int y, char *str, int color)
{
    int ch;
    int sx = x; // 记录起始 X 坐标，用于换行
    
    // 动态获取当前字体的行高，并考虑缩放倍数
    // 这里的 fb_get_font_height() 是我们上一条建议中添加的函数
    int line_height = fb_get_font_height() * font_scale; 

    while (1)
    {
        ch = utf8_to_ucs(&str);
        if (ch == 0)
            break;

        // 处理换行符
        if (ch == '\n') {
            y += line_height; // 使用动态行高跳转到下一行
            x = sx;           // 回到初始水平位置
            continue;
        }

        // 绘制字符
        // fb_draw_font 返回的是字符宽度（已包含缩放）
        int adv = fb_draw_font(x, y, ch, color);
        
        // 如果字符没找到，fb_draw_font 返回 -1，这里做一个容错处理
        if (adv > 0) {
            x += adv;
        }else{
					return;
				}
    }
}
/**
 * @brief 绘制带背景色的文字
 * @param x      起始X
 * @param y      起始Y
 * @param str    字符串
 * @param color  文字颜色 (BLACK, WHITE, RED)
 */
void draw_text_filled(int x, int y, char *str, int color)
{
    int tw, th;
    
    // 1. 获取文字实际占用的宽高
    get_text_dimension(str, &tw, &th);

    // 2. 确定背景色
    // 如果文字是黑色(0)，背景设为白色(1)；反之亦然。
    // 如果是 RED 或 SWAP，则根据需要设定，这里默认为取反
    int bg_color;
    if (color == BLACK)      bg_color = WHITE;
    else if (color == WHITE) bg_color = BLACK;
    else                     bg_color = WHITE; // 默认背景

    // 3. 计算边距 (Padding)
    // 建议边距随字号缩放，或者固定为一个视觉舒适的值
    int pad_x = 4 * font_scale; 
    int pad_y = 8 * font_scale;

    // 4. 绘制背景矩形
    // 注意：draw_box 通常需要左上角和右下角坐标
    draw_box(x - pad_x/2, 
             y, 
             x + tw + pad_x, 
             y + th + pad_y, 
             bg_color);

    // 5. 绘制文字 (文字在背景之上)
    draw_text(x, y, str, color);
}

/******************************************************************************/
#if 0
char *wday_str[] = {
	"一",
	"二",
	"三",
	"四",
	"五",
	"六",
	"日",
};


static int wday = 0;
void fb_test(void)
{
	memset(fb_bw, 0xff, scr_h*line_bytes);
	if(scr_mode&EPD_BWR){
		memset(fb_rr, 0x00, scr_h*line_bytes);
	}

	draw_rect(0, 0, fb_w-1, fb_h-1, BLACK);
	draw_rect(1, 1, fb_w-2, fb_h-2, BLACK);

#if 0
	for(int i=0; i<3; i++){
		int x = 8+i*38;
		int y = 30;
		draw_rect(x, y, x+29, y+29, BLACK);
		//draw_rect(x+1, y+1, x+29-1, y+29-1, BLACK);
		draw_box(x+2, y+2, x+29-2, y+29-2, i);
	}
#endif

	select_font(0);

	char tbuf[64];
	sprintk(tbuf, "%4d年%2d月%2d日 星期%s", 2025, 4, 29, wday_str[wday]);
	draw_text(15, 85, tbuf, BLACK);
	
	wday += 1;
	if(wday==7)
		wday = 0;

	select_font(1);
	sprintk(tbuf, "%02d:%02d", 2+wday, 30+wday);
	draw_text(12, 20, tbuf, BLACK);

	epd_screen_update();
}
#endif

/******************************************************************************/
