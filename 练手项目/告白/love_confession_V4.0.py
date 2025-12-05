import pygame
import random
import math
import sys

# ================= ⚙️ 剧场版配置 =================
WIDTH, HEIGHT = 1000, 700  # 宽屏影院感
CENTER_X, CENTER_Y = WIDTH // 2, HEIGHT // 2

# 💜 赛博紫配色方案
COLORS = [
    (255, 255, 255),  # 核心亮白
    (238, 130, 238),  # 紫罗兰
    (255, 0, 255),  # 霓虹紫
    (147, 112, 219),  # 中紫
    (75, 0, 130)  # 靛青 (深邃背景)
]

# 粒子规模
HEART_POINTS = 3500  # 爱心骨架粒子数
FALLING_RATE = 40  # 瀑布流速
FLOOR_Y = 250  # 地面高度

# =================================================

pygame.init()
# 开启抗锯齿和硬件加速标志
screen = pygame.display.set_mode((WIDTH, HEIGHT), pygame.HWSURFACE | pygame.DOUBLEBUF)
pygame.display.set_caption("Universe Confession - Final Cut")
clock = pygame.time.Clock()


# --- 📝 资源加载 ---
def get_font(size):
    font_names = ["simhei", "microsoftyahei", "pingfangsc", "stsong", "arial"]
    for name in font_names:
        try:
            return pygame.font.SysFont(name, size)
        except:
            continue
    return pygame.font.Font(None, size)


font_sub = get_font(30)
font_main = get_font(60)


# --- 💜 核心算法：爱心几何 ---
def generate_heart_shape(num_points):
    points = []
    for _ in range(num_points):
        t = random.uniform(0, 2 * math.pi)
        # 经典方程
        x = 16 * math.sin(t) ** 3
        y = -(13 * math.cos(t) - 5 * math.cos(2 * t) - 2 * math.cos(3 * t) - math.cos(4 * t))

        # 3D 造型
        scale = 13
        thickness = random.uniform(-5, 5)
        spread = random.uniform(0.95, 1.05)

        px = x * scale * spread
        py = y * scale * spread
        pz = thickness * scale * 0.4

        c_idx = random.randint(0, len(COLORS) - 1)
        points.append([px, py, pz, c_idx])  # [x, y, z, color]
    return points


# 预生成目标形状
TARGET_HEART = generate_heart_shape(HEART_POINTS)


# --- ✨ 粒子系统类 ---
class StoryParticle:
    def __init__(self, target_idx):
        # 目标是爱心上的哪一个点
        self.tx, self.ty, self.tz, self.c_idx = TARGET_HEART[target_idx]

        # 1. 初始状态：宇宙大爆炸 (随机散布在远处)
        dist = random.uniform(500, 2000)
        theta = random.uniform(0, 2 * math.pi)
        phi = random.uniform(0, math.pi)

        self.x = dist * math.sin(phi) * math.cos(theta)
        self.y = dist * math.sin(phi) * math.sin(theta)
        self.z = dist * math.cos(phi)

        # 动画控制
        self.locked = False  # 是否已归位

    def update_intro(self, progress):
        # 阶段1 & 2：从混乱汇聚成爱心
        # 使用缓动函数 (Ease Out)
        ease = 1 - (1 - progress) ** 3

        # 螺旋汇聚效果
        if progress < 0.95:
            # 还未完全到达时，加一点旋转噪音
            rot_speed = (1 - progress) * 5
            old_x = self.x
            self.x = self.x * math.cos(rot_speed * 0.05) - self.z * math.sin(rot_speed * 0.05)
            self.z = old_x * math.sin(rot_speed * 0.05) + self.z * math.cos(rot_speed * 0.05)

        # 线性插值趋向目标
        self.x += (self.tx - self.x) * 0.05
        self.y += (self.ty - self.y) * 0.05
        self.z += (self.tz - self.z) * 0.05


# --- 💧 落沙系统 (复刻之前的逻辑) ---
class DropSystem:
    def __init__(self):
        self.falling = []
        self.floor = []

    def spawn(self, rotated_heart_points):
        # 从旋转后的爱心上随机剥落粒子
        for _ in range(FALLING_RATE):
            src = random.choice(rotated_heart_points)
            # [x, y, z, vx, vy, vz, color_idx]
            self.falling.append(
                [src[0], src[1], src[2], random.uniform(-0.5, 0.5), 0, random.uniform(-0.5, 0.5), src[3]])

    def update(self):
        # 更新下落
        for i in range(len(self.falling) - 1, -1, -1):
            p = self.falling[i]
            p[4] += 0.25  # 重力
            p[0] += p[3];
            p[1] += p[4];
            p[2] += p[5]

            if p[1] > FLOOR_Y:
                # 变成地面粒子 [x, z, vx, vz, life, color]
                angle = random.uniform(0, 6.28)
                speed = random.uniform(1, 4)
                self.floor.append([p[0], p[2], math.cos(angle) * speed, math.sin(angle) * speed, 255, p[6]])
                self.falling.pop(i)

        # 更新地面
        for i in range(len(self.floor) - 1, -1, -1):
            p = self.floor[i]
            p[0] += p[2]  # 扩散
            p[1] += p[3]
            p[2] *= 0.9;
            p[3] *= 0.9  # 摩擦
            p[4] -= 5  # 消失速度
            if p[4] <= 0: self.floor.pop(i)


# --- 📽️ 投影函数 ---
def project(x, y, z, fov, viewer_dist):
    if z + viewer_dist <= 1: return None
    factor = fov / (viewer_dist + z)
    sx = x * factor + CENTER_X
    sy = y * factor + CENTER_Y
    size = max(1, 3 * factor)
    return sx, sy, size, factor


# --- 🖋️ 字幕绘制 ---
def draw_subtitle(surface, text, font, y_pos, alpha):
    if alpha <= 0: return
    s = font.render(text, True, (255, 255, 255))
    s.set_alpha(alpha)
    rect = s.get_rect(center=(WIDTH // 2, y_pos))
    # 文字辉光
    glow = pygame.transform.smoothscale(s, (int(rect.width * 1.1), int(rect.height * 1.1)))
    glow.fill((200, 100, 255), special_flags=pygame.BLEND_RGB_ADD)
    glow.set_alpha(alpha // 3)
    glow_rect = glow.get_rect(center=(WIDTH // 2, y_pos))

    surface.blit(glow, glow_rect)
    surface.blit(s, rect)


# --- 🚀 主程序 ---
def main():
    running = True
    start_ticks = pygame.time.get_ticks()

    # 实例化
    particles = [StoryParticle(i) for i in range(HEART_POINTS)]
    drop_system = DropSystem()

    # 摄像机/动画状态
    heart_angle = 0

    while running:
        # 0. 基础设置
        dt = clock.tick(60)
        current_time = pygame.time.get_ticks() - start_ticks
        seconds = current_time / 1000.0

        # 动态背景色 (随着时间变暗变深)
        bg_blue = max(5, int(20 - seconds * 0.5))
        screen.fill((5, 0, bg_blue))

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False

        # ================= 🎬 剧本分镜逻辑 =================

        # 渲染列表 [z, x, y, size, color, type]
        render_list = []

        # 视角控制 (Zoom)
        # 0-10s: 远景 -> 15s: 特写 -> 50s: 极特写
        viewer_dist = 1200
        if seconds < 10:
            viewer_dist = 2500 - (seconds / 10) * 1300  # 2500 -> 1200
        elif seconds > 50:
            viewer_dist = 1200 - ((seconds - 50) / 10) * 400  # 1200 -> 800

        # --- 第一幕 & 第二幕：混沌与汇聚 (0s - 15s) ---
        if seconds < 15:
            # 进度 0.0 -> 1.0
            progress = min(1.0, seconds / 12.0)

            # 旋转整个宇宙
            global_rot = seconds * 0.5
            cos_g, sin_g = math.cos(global_rot), math.sin(global_rot)

            for p in particles:
                p.update_intro(progress)

                # 整体旋转
                rx = p.x * cos_g - p.z * sin_g
                rz = p.x * sin_g + p.z * cos_g

                res = project(rx, p.y, rz, 600, viewer_dist)
                if res:
                    render_list.append((rz, res[0], res[1], res[2], COLORS[p.c_idx], "star"))

        # --- 第三幕 & 第四幕：落沙爱心 (15s - 60s) ---
        else:
            heart_angle += 0.015
            cos_a, sin_a = math.cos(heart_angle), math.sin(heart_angle)

            current_heart_geometry = []  # 用于生成落沙

            # 1. 处理爱心本体 (此时粒子已归位，直接用 Target 坐标计算旋转)
            for i, p in enumerate(particles):
                # 引入微弱的呼吸浮动
                breath = 1.0 + 0.03 * math.sin(seconds * 2)

                base_x, base_y, base_z, c_idx = TARGET_HEART[i]

                # 旋转
                rx = base_x * breath * cos_a - base_z * breath * sin_a
                ry = base_y * breath
                rz = base_x * breath * sin_a + base_z * breath * cos_a

                current_heart_geometry.append((rx, ry, rz, c_idx))

                res = project(rx, ry, rz, 600, viewer_dist)
                if res:
                    render_list.append((rz, res[0], res[1], res[2], COLORS[c_idx], "heart"))

            # 2. 处理落沙与地面 (Drop System)
            drop_system.spawn(current_heart_geometry)
            drop_system.update()

            # 下落粒子渲染
            for p in drop_system.falling:
                # 也要随爱心旋转视角吗？视频里似乎是独立下落的，这里保持独立下落视角
                # 但为了立体感，我们让落下的粒子也接受同样的 Y 轴旋转
                rx = p[0] * cos_a - p[2] * sin_a
                rz = p[0] * sin_a + p[2] * cos_a

                res = project(rx, p[1], rz, 600, viewer_dist)
                if res:
                    render_list.append((rz, res[0], res[1], res[2], COLORS[p[6]], "drop"))

            # 地面粒子渲染
            for p in drop_system.floor:
                rx = p[0] * cos_a - p[1] * sin_a  # p[1]这里其实存的是z
                rz = p[0] * sin_a + p[1] * cos_a

                res = project(rx, FLOOR_Y, rz, 600, viewer_dist)
                if res:
                    # 地面透明度
                    alpha_factor = p[4] / 255.0
                    base_c = COLORS[p[5]]
                    final_c = (base_c[0] * alpha_factor, base_c[1] * alpha_factor, base_c[2] * alpha_factor)
                    render_list.append((rz, res[0], res[1], res[2], final_c, "floor"))

        # ================= 🎨 渲染管线 =================

        # Z-Sort
        render_list.sort(key=lambda x: x[0], reverse=True)

        for item in render_list:
            z, sx, sy, size, color, p_type = item

            if 0 <= sx < WIDTH and 0 <= sy < HEIGHT:
                if p_type == "floor":
                    pygame.draw.ellipse(screen, color, (sx - size, sy - size * 0.4, size * 2, size * 0.8))

                elif p_type == "star":
                    # 开场特效：画亮一点
                    if size > 2:
                        pygame.draw.circle(screen, color, (int(sx), int(sy)), int(size))
                    else:
                        screen.set_at((int(sx), int(sy)), color)

                else:  # heart, drop
                    # 主体粒子：为了性能和效果平衡
                    # 近处画光晕，远处画点
                    if size > 2:
                        # 简单的辉光模拟
                        s = pygame.Surface((int(size * 2), int(size * 2)), pygame.SRCALPHA)
                        pygame.draw.circle(s, (*color[:3], 150), (int(size), int(size)), int(size / 1.5))
                        screen.blit(s, (sx - size, sy - size), special_flags=pygame.BLEND_ADD)
                    else:
                        screen.set_at((int(sx), int(sy)), color)

        # ================= 📝 字幕脚本 (时间轴) =================

        # 计算淡入淡出 Alpha (0-255)
        def get_alpha(start, end, fade_dur=1.0):
            if seconds < start or seconds > end: return 0
            if seconds < start + fade_dur: return int((seconds - start) / fade_dur * 255)
            if seconds > end - fade_dur: return int((end - seconds) / fade_dur * 255)
            return 255

        # 剧本内容
        # 0-5s
        draw_subtitle(screen, "在 浩 瀚 的 宇 宙 中", font_sub, HEIGHT - 150, get_alpha(1, 5))
        # 5-10s
        draw_subtitle(screen, "星 辰 本 是 散 落 的 沙", font_sub, HEIGHT - 150, get_alpha(6, 11))
        # 12-17s (爱心刚汇聚)
        draw_subtitle(screen, "直 到 遇 见 了 引 力", font_sub, HEIGHT - 150, get_alpha(12, 17))
        # 20-30s
        draw_subtitle(screen, "我 的 世 界 开 始 旋 转", font_sub, HEIGHT - 150, get_alpha(20, 28))
        # 30-40s
        draw_subtitle(screen, "万 物 汇 聚 成 你 的 模 样", font_sub, HEIGHT - 150, get_alpha(30, 38))
        # 42-50s
        draw_subtitle(screen, "愿 时 光 停 驻 此 刻", font_sub, HEIGHT - 150, get_alpha(42, 50))

        # 52s+ (高潮：大标题)
        final_alpha = 0
        if seconds > 52:
            final_alpha = min(255, int((seconds - 52) * 100))

            # 绘制中心大字
            t_surf = font_main.render("I LOVE YOU", True, (255, 255, 255))
            t_surf.set_alpha(final_alpha)
            t_rect = t_surf.get_rect(center=(CENTER_X, CENTER_Y))

            # 字幕背景光
            glow = pygame.Surface((WIDTH, 100), pygame.SRCALPHA)
            glow.fill((0, 0, 0, max(0, int(final_alpha * 0.5))))
            screen.blit(glow, (0, CENTER_Y - 50))

            screen.blit(t_surf, t_rect)

            # 底部小字
            draw_subtitle(screen, "For Forever", font_sub, CENTER_Y + 60, final_alpha)

        pygame.display.flip()

        # 65秒后自动退出 (可选)
        if seconds > 65:
            running = False

    pygame.quit()
    sys.exit()


if __name__ == "__main__":
    main()