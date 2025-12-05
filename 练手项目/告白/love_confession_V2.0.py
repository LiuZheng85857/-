import pygame
import random
import math
import datetime
import sys

# ================= 💖 配置区域 💖 =================
# 1. 你们在一起的开始时间
START_DATE = datetime.datetime(2024, 11, 5, 0, 0, 0)

# 2. 你的名字和她的名字
GIRLFRIEND_NAME = "亲爱的"

# 3. 颜色配置
GALAXY_COLORS = [
    (255, 255, 255),  # 白
    (255, 192, 203),  # 粉
    (238, 130, 238),  # 紫罗兰
    (255, 105, 180),  # 亮粉
    (255, 215, 0),  # 金
    (138, 43, 226)  # 深紫
]

# 窗口大小
WIDTH, HEIGHT = 1000, 700
CENTER_X, CENTER_Y = WIDTH // 2, HEIGHT // 2
# ===================================================

# 初始化
pygame.init()
pygame.display.set_caption(f"To {GIRLFRIEND_NAME}")
screen = pygame.display.set_mode((WIDTH, HEIGHT))
clock = pygame.time.Clock()


# 字体加载
def get_font(size):
    font_names = ["simhei", "microsoftyahei", "pingfangsc", "stsong", "arial"]
    for name in font_names:
        try:
            return pygame.font.SysFont(name, size)
        except:
            continue
    return pygame.font.Font(None, size)


font_small = get_font(20)
font_medium = get_font(32)
font_large = get_font(70)  # 字体也调大一点


# --- 🌟 类：背景星星 (升级版：支持流动) ---
class Star:
    def __init__(self):
        # 让星星分布在一个比屏幕大的圆内，这样旋转时四角不会空
        r = random.uniform(0, WIDTH * 0.8)
        theta = random.uniform(0, 2 * math.pi)
        self.x = CENTER_X + r * math.cos(theta)
        self.y = CENTER_Y + r * math.sin(theta)

        # 升级点1：星星变大
        self.base_size = random.uniform(1.5, 4.0)
        self.blink_speed = random.uniform(0.05, 0.1)
        self.angle = random.uniform(0, 6.28)
        self.color_base = random.randint(180, 255)  # 基础亮度

    def update(self, rotate=False):
        self.angle += self.blink_speed
        # 升级点2：闪烁更明显 (Sine wave amplitude increased)
        blink = math.sin(self.angle)
        self.current_alpha = max(50, min(255, self.color_base + 100 * blink))

        # 升级点4：背景流动特效
        if rotate:
            # 简单的 2D 旋转算法
            # 计算当前相对于中心的角度
            dx = self.x - CENTER_X
            dy = self.y - CENTER_Y
            dist = math.sqrt(dx * dx + dy * dy)
            curr_angle = math.atan2(dy, dx)

            # 稍微转动一点点
            curr_angle += 0.002

            self.x = CENTER_X + dist * math.cos(curr_angle)
            self.y = CENTER_Y + dist * math.sin(curr_angle)

    def draw(self, surface):
        # 绘制
        s_surf = pygame.Surface((int(self.base_size * 2) + 4, int(self.base_size * 2) + 4), pygame.SRCALPHA)
        color = (255, 255, 255, int(self.current_alpha))
        # 画一个柔和的光晕
        pygame.draw.circle(s_surf, (255, 255, 255, int(self.current_alpha / 2)),
                           (int(self.base_size) + 2, int(self.base_size) + 2), self.base_size + 1)
        # 画实心核
        pygame.draw.circle(s_surf, color,
                           (int(self.base_size) + 2, int(self.base_size) + 2), self.base_size / 2)
        surface.blit(s_surf, (self.x, self.y))


# --- 🌠 类：流星 (升级版：更亮更大) ---
class Meteor:
    def __init__(self):
        self.x = random.randint(WIDTH // 2 - 100, WIDTH + 100)
        self.y = random.randint(-100, -10)
        # 升级点2：速度加快
        self.speed_x = random.randint(-15, -8)
        self.speed_y = random.randint(8, 15)
        self.length = random.randint(30, 60)  # 尾巴更长
        self.thickness = random.randint(2, 4)  # 尾巴更粗
        self.active = True

    def update(self):
        self.x += self.speed_x
        self.y += self.speed_y
        if self.x < -100 or self.y > HEIGHT + 100:
            self.active = False

    def draw(self, surface):
        if self.active:
            start_pos = (self.x, self.y)
            end_pos = (self.x - self.speed_x * 1.5, self.y - self.speed_y * 1.5)

            # 画尾巴
            pygame.draw.line(surface, (255, 255, 255), start_pos, end_pos, self.thickness)
            # 画头部 (发光球体)
            pygame.draw.circle(surface, (255, 255, 200), (int(self.x), int(self.y)), self.thickness + 2)
            # 头部光晕
            s = pygame.Surface((20, 20), pygame.SRCALPHA)
            pygame.draw.circle(s, (255, 255, 255, 100), (10, 10), 8)
            surface.blit(s, (int(self.x) - 10, int(self.y) - 10))


# --- 💖 类：3D 银河粒子 (升级版：巨大化) ---
class GalaxyParticle:
    def __init__(self):
        self.reset()

    def reset(self):
        t = random.uniform(0, 2 * math.pi)
        # 爱心方程
        base_x = 16 * math.sin(t) ** 3
        base_y = -(13 * math.cos(t) - 5 * math.cos(2 * t) - 2 * math.cos(3 * t) - math.cos(4 * t))

        # 升级点3：Spread 更大，更有星云感
        spread = random.uniform(0.6, 1.8)

        # 升级点3：坐标系数从 12 改为 17 (巨大化)
        scale_mult = 17
        self.x = base_x * scale_mult * spread + random.uniform(-6, 6)
        self.y = base_y * scale_mult * spread + random.uniform(-6, 6)
        # 增加 Z 轴深度，旋转时更立体
        self.z = random.uniform(-40, 40)

        self.color = random.choice(GALAXY_COLORS)
        self.base_size = random.randint(1, 3)

    def rotate(self, angle_y):
        cos_a = math.cos(angle_y)
        sin_a = math.sin(angle_y)
        new_x = self.x * cos_a - self.z * sin_a
        new_z = self.x * sin_a + self.z * cos_a
        return new_x, self.y, new_z


# --- 辅助：绘制居中文字 ---
def draw_text_centered(text, font, color, y_offset, alpha=255):
    surf = font.render(text, True, color)
    surf.set_alpha(alpha)
    rect = surf.get_rect(center=(WIDTH // 2, HEIGHT // 2 + y_offset))
    screen.blit(surf, rect)


# --- 主程序 ---
def main():
    running = True

    # 初始化背景星空 (300颗，更多)
    bg_stars = [Star() for _ in range(300)]
    meteors = []
    # 初始化银河爱心 (1600颗，更密)
    galaxy_particles = [GalaxyParticle() for _ in range(1600)]

    angle = 0
    start_ticks = pygame.time.get_ticks()

    while running:
        # 时间控制
        current_time = pygame.time.get_ticks() - start_ticks
        screen.fill((5, 5, 25))  # 背景色稍微亮一点点的深蓝

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False

        # --- 1. 背景层：星星 (处理流动逻辑) ---
        is_rotating = current_time > 18000  # 18秒后背景开始旋转
        for star in bg_stars:
            star.update(rotate=is_rotating)
            star.draw(screen)

        # --- 2. 剧情层 ---

        # 0-6s: 寂静闪烁
        if current_time < 6000:
            alpha = min(255, int(current_time / 1000 * 100))
            if current_time > 4000: alpha = max(0, 255 - int((current_time - 4000) / 1000 * 200))
            draw_text_centered("在遇见你之前...", font_medium, (200, 200, 255), -30, alpha)

        # 6-12s: 流星雨 (加大频率)
        elif current_time < 12000:
            # 增加生成概率
            if random.randint(0, 25) == 0: meteors.append(Meteor())

            relative_time = current_time - 6000
            alpha = min(255, int(relative_time / 1000 * 100))
            if relative_time > 4000: alpha = max(0, 255 - int((relative_time - 4000) / 1000 * 200))

            draw_text_centered("我的世界", font_medium, (200, 200, 255), -50, alpha)
            draw_text_centered("是无尽的等待", font_medium, (200, 200, 255), 0, alpha)

        # 12-18s: 铺垫结束
        elif current_time < 18000:
            relative_time = current_time - 12000
            alpha = min(255, int(relative_time / 1000 * 100))
            if relative_time > 4000: alpha = max(0, 255 - int((relative_time - 4000) / 1000 * 200))

            draw_text_centered("直到星光汇聚成河", font_medium, (255, 215, 0), -20, alpha)

        # --- 3. 绘制流星 ---
        if current_time < 18000:
            for meteor in meteors:
                meteor.update()
                meteor.draw(screen)
            meteors = [m for m in meteors if m.active]

        # --- 4. 高潮层：3D银河爱心 ---
        if current_time >= 16000:
            angle += 0.012  # 旋转速度
            fov = 500
            viewer_distance = 1000

            projected_points = []

            for p in galaxy_particles:
                rx, ry, rz = p.rotate(angle)
                if rz + viewer_distance != 0:
                    scale = fov / (viewer_distance + rz)
                    x_2d = rx * scale + WIDTH // 2
                    y_2d = ry * scale + HEIGHT // 2
                    size = p.base_size * scale

                    if -50 <= x_2d <= WIDTH + 50 and -50 <= y_2d <= HEIGHT + 50:
                        projected_points.append([rz, x_2d, y_2d, size, p.color])

            projected_points.sort(key=lambda p: p[0], reverse=True)

            # 爱心渐显逻辑
            heart_alpha_ratio = 1.0
            if current_time < 20000:
                heart_alpha_ratio = (current_time - 16000) / 4000

            for p in projected_points:
                rz, x, y, s, c = p

                # 深度计算 (Color Clamp 防止报错)
                depth_ratio = max(0.5, min(1.3, 1000 / (1000 + rz)))

                r = min(255, max(0, int(c[0] * depth_ratio * heart_alpha_ratio)))
                g = min(255, max(0, int(c[1] * depth_ratio * heart_alpha_ratio)))
                b = min(255, max(0, int(c[2] * depth_ratio * heart_alpha_ratio)))

                if s > 0:
                    pygame.draw.circle(screen, (r, g, b), (int(x), int(y)), int(s))

        # --- 5. UI层 ---
        if current_time >= 19000:
            now = datetime.datetime.now()
            diff = now - START_DATE
            days = diff.days
            seconds = diff.seconds
            hours = seconds // 3600
            minutes = (seconds % 3600) // 60
            secs = seconds % 60
            timer_text = f"{days}天 {hours}小时 {minutes}分 {secs}秒"

            text_alpha = min(255, int((current_time - 19000) / 2000 * 255))

            # 主标题位置上移一点，避开巨大的爱心
            draw_text_centered(f"I Love You, {GIRLFRIEND_NAME}", font_large, (255, 255, 255), -80, text_alpha)
            # 计时器下移
            draw_text_centered(f"我们相爱了: {timer_text}", font_medium, (255, 182, 193), 280, text_alpha)

            if (current_time // 800) % 2 == 0:
                draw_text_centered("你是我唯一的引力", font_small, (150, 150, 255), 330, text_alpha)

        pygame.display.flip()
        clock.tick(60)

    pygame.quit()
    sys.exit()


if __name__ == "__main__":
    main()