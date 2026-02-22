#include "epd.h"

const short sin_table_90[] = {
    0, 18, 36, 54, 71, 89, 107, 125, 143, 160, 178, 195, 213, 230, 248, 265, 
    282, 299, 316, 333, 350, 367, 384, 400, 417, 433, 449, 465, 481, 496, 512, 
    527, 543, 558, 573, 587, 602, 616, 630, 644, 658, 672, 685, 698, 711, 724, 
    737, 749, 761, 773, 784, 796, 807, 818, 828, 839, 849, 859, 868, 878, 887, 
    896, 904, 912, 920, 928, 935, 943, 950, 957, 964, 970, 977, 983, 989, 994, 
    1000, 1005, 1010, 1014, 1018, 1022, 1025, 1028, 1031, 1033, 1035, 1037, 1038, 1039, 1040
};
int get_sin(int angle) {
    angle %= 360;
    if (angle < 0) angle += 360;
    
    if (angle <= 90) return sin_table_90[angle];
    if (angle <= 180) return sin_table_90[180 - angle];
    if (angle <= 270) return -sin_table_90[angle - 180];
    return -sin_table_90[360 - angle];
}

// cos(x) = sin(x + 90)
int get_cos(int angle) {
    return get_sin(angle + 90);
}

/**
 * ???????????????
 * @param cx, cy: ???(??)
 * @param px, py: ?????
 * @param angle:  ???????? (0-360)
 */
Point get_rotate_point(int cx, int cy, int px, int py, int angle) {
    Point p;
    
    // 1. ???????(???????)
    int x = px - cx;
    int y = py - cy;
    
    // 2. ?? sin ? cos (?? 1024 ???)
    int s = get_sin(angle);
    int c = get_cos(angle);
    
    // 3. ????:
    // x' = x*cos - y*sin
    // y' = x*sin + y*cos
    // ??????? 10 ?(?? 1024)????
    p.x = cx + ((x * c - y * s) >> 10);
    p.y = cy + ((x * s + y * c) >> 10);
    
    return p;
}