import pygame
import random
import math
import datetime
import sys

# ================= 配置区域 (你可以修改这里) =================
# 你们在一起的开始时间：年, 月, 日, 时, 分, 秒
# 默认设置为 2024年11月5日0点0分0秒 (如果是其他年份请修改 2024)
START_DATE = datetime.datetime(2024, 11, 5, 0, 0, 0)

# 女朋友的名字（显示在动画结尾）
GIRLFRIEND_NAME = "亲爱的"

# 窗口大小
WIDTH, HEIGHT = 1000, 700
# ==========================================================

# 颜色定义
BLACK = (0, 0, 0)
MIDNIGHT_BLUE = (10, 10, 35)  # 深邃夜空
STAR_WHITE = (255, 255, 255)
PINK = (255, 105, 180)  # 浅粉色
GOLD = (255, 223, 0)  # 金色
HEART_COLOR = (220, 20, 60)  # 猩红

# 初始化 Pygame
pygame.init()
pygame.display.set_caption("星空下的告白 - To " + GIRLFRIEND_NAME)
screen = pygame.display.set_mode((WIDTH, HEIGHT))
clock = pygame.time.Clock()


# 尝试加载中文字体
def get_font(size):
    # 尝试常见的中文系统字体
    font_names = ["simhei", "microsoftyahei", "pingfangsc", "stheiti", "arial"]
    for name in font_names:
        try:
            return pygame.font.SysFont(name, size)
        except:
            continue
    return pygame.font.Font(None, size)  # 英文兜底


font_small = get_font(20)
font_medium = get_font(32)
font_large = get_font(64)


# --- 粒子类：背景星星 ---
class Star:
    def __init__(self):
        self.x = random.randint(0, WIDTH)
        self.y = random.randint(0, HEIGHT)
        self.radius = random.randint(1, 2)
        self.brightness = random.randint(0, 255)
        self.change = random.choice([-2, 2])

    def update(self):
        self.brightness += self.change
        if self.brightness > 255:
            self.brightness = 255
            self.change = -2
        elif self.brightness < 100:
            self.brightness = 100
            self.change = 2

    def draw(self, surface):
        # 绘制带透明度的星星
        s = pygame.Surface((self.radius * 2, self.radius * 2), pygame.SRCALPHA)
        pygame.draw.circle(s, (255, 255, 255, self.brightness), (self.radius, self.radius), self.radius)
        surface.blit(s, (self.x - self.radius, self.y - self.radius))


# --- 粒子类：流星 ---
class Meteor:
    def __init__(self):
        self.x = random.randint(WIDTH // 2, WIDTH)
        self.y = 0
        self.speed_x = random.randint(-10, -5)
        self.speed_y = random.randint(5, 10)
        self.length = random.randint(10, 20)
        self.active = True

    def update(self):
        self.x += self.speed_x
        self.y += self.speed_y
        if self.x < 0 or self.y > HEIGHT:
            self.active = False

    def draw(self, surface):
        if self.active:
            start_pos = (self.x, self.y)
            end_pos = (self.x - self.speed_x * 2, self.y - self.speed_y * 2)
            pygame.draw.line(surface, STAR_WHITE, start_pos, end_pos, 2)


# --- 粒子类：组成爱心的粒子 ---
class HeartParticle:
    def __init__(self, target_x, target_y):
        # 初始位置在屏幕边缘随机
        self.x = random.choice([random.randint(-100, 0), random.randint(WIDTH, WIDTH + 100)])
        self.y = random.choice([random.randint(-100, 0), random.randint(HEIGHT, HEIGHT + 100)])
        self.target_x = target_x
        self.target_y = target_y
        self.speed = random.uniform(0.02, 0.05)  # 移动速度插值系数
        self.radius = random.randint(1, 3)
        self.color = random.choice([PINK, HEART_COLOR, (255, 192, 203)])
        self.arrived = False

    def update(self):
        # 缓动效果 (Lerp)
        self.x += (self.target_x - self.x) * self.speed
        self.y += (self.target_y - self.y) * self.speed

        # 检查是否到达目标附近
        if abs(self.x - self.target_x) < 1 and abs(self.y - self.target_y) < 1:
            self.arrived = True

    def draw(self, surface, scale_factor=1.0):
        # 根据心跳缩放调整位置
        dx = self.x - WIDTH // 2
        dy = self.y - HEIGHT // 2
        draw_x = WIDTH // 2 + dx * scale_factor
        draw_y = HEIGHT // 2 + dy * scale_factor
        pygame.draw.circle(surface, self.color, (int(draw_x), int(draw_y)), self.radius)


# --- 数学函数：生成爱心坐标 ---
def get_heart_points(num_points, scale=12):
    points = []
    for _ in range(num_points):
        t = random.uniform(0, 2 * math.pi)
        # 爱心方程
        x = 16 * math.sin(t) ** 3
        y = -(13 * math.cos(t) - 5 * math.cos(2 * t) - 2 * math.cos(3 * t) - math.cos(4 * t))

        # 缩放并居中
        x = x * scale + WIDTH // 2
        y = y * scale + HEIGHT // 2 - 20  # 稍微上移一点
        points.append((x, y))
    return points


# --- 辅助函数：绘制居中文字 ---
def draw_centered_text(surface, text, font, color, y_offset=0, alpha=255):
    text_obj = font.render(text, True, color)
    text_obj.set_alpha(alpha)
    rect = text_obj.get_rect(center=(WIDTH // 2, HEIGHT // 2 + y_offset))
    surface.blit(text_obj, rect)


# --- 主程序逻辑 ---
def main():
    running = True
    start_ticks = pygame.time.get_ticks()

    # 实例化对象
    stars = [Star() for _ in range(100)]
    meteors = []

    # 生成爱心粒子目标点 (800个粒子)
    heart_targets = get_heart_points(800)
    heart_particles = [HeartParticle(tx, ty) for tx, ty in heart_targets]

    # 动画阶段控制
    # 0-8s: 寂静
    # 8-20s: 流星 & 文字1
    # 20-30s: 文字2
    # 30-40s: 汇聚
    # 40s+: 告白 & 计时器

    while running:
        # 1. 基础设置
        current_time = pygame.time.get_ticks() - start_ticks
        dt = clock.tick(60) / 1000.0  # 帧率限制
        screen.fill(MIDNIGHT_BLUE)  # 绘制背景

        # 处理退出事件
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            if event.type == pygame.MOUSEBUTTONDOWN:
                # 结束时点击屏幕退出或放烟花(这里简单处理为退出)
                if current_time > 45000:
                    pass

                    # 2. 绘制背景星星 (始终存在)
        for star in stars:
            star.update()
            star.draw(screen)

        # 3. 动画分镜逻辑

        # [第一幕：寂静] (0 - 8秒)
        if current_time < 8000:
            alpha = min(255, int((current_time / 2000) * 255))
            draw_centered_text(screen, "在遇见你之前...", font_medium, (200, 200, 255), -50)
            if current_time > 3000:
                draw_centered_text(screen, "我的世界是一片寂静的夜空", font_medium, (200, 200, 255), 50)

        # [第二幕：流星] (8 - 22秒)
        elif current_time < 22000:
            # 生成流星
            if random.randint(0, 50) == 0:
                meteors.append(Meteor())

            # 更新和绘制流星
            for meteor in meteors:
                meteor.update()
                meteor.draw(screen)
            meteors = [m for m in meteors if m.active]  # 清理消失的流星

            draw_centered_text(screen, "看过无数风景", font_medium, (200, 200, 255), -50)
            draw_centered_text(screen, "却依然觉得孤单", font_medium, (200, 200, 255), 50)

        # [第三幕：铺垫] (22 - 32秒)
        elif current_time < 32000:
            draw_centered_text(screen, "直到星光落入眼底", font_medium, GOLD, -20)
            draw_centered_text(screen, "也就是遇见你的那一刻", font_medium, GOLD, 40)

        # [第四幕：汇聚] (32 - 40秒)
        elif current_time < 40000:
            # 粒子飞入
            for p in heart_particles:
                p.update()
                p.draw(screen)

            draw_centered_text(screen, "万物开始汇聚...", font_small, PINK, 250)

        # [第五幕：告白 & 计时] (40秒以后)
        else:
            # 心跳效果
            beat_time = pygame.time.get_ticks() / 500
            scale = 1.0 + 0.05 * math.sin(beat_time * math.pi)  # 模拟心跳缩放

            # 绘制爱心
            for p in heart_particles:
                # 稍微让粒子在原位颤动，增加灵动感
                p.x += random.uniform(-0.5, 0.5)
                p.y += random.uniform(-0.5, 0.5)
                p.draw(screen, scale)

            # 计算时间差
            now = datetime.datetime.now()
            diff = now - START_DATE
            days = diff.days
            seconds = diff.seconds
            hours = seconds // 3600
            minutes = (seconds % 3600) // 60
            secs = seconds % 60

            # 绘制中心文字
            draw_centered_text(screen, f"I Love You, {GIRLFRIEND_NAME}", font_large, STAR_WHITE, -40)

            # 绘制底部计时文字
            timer_text = f"我们已经相爱了: {days}天 {hours}小时 {minutes}分 {secs}秒"
            draw_centered_text(screen, timer_text, font_medium, PINK, 250)

            # 闪烁提示
            if (pygame.time.get_ticks() // 500) % 2 == 0:
                draw_centered_text(screen, "愿 岁岁年年 共此时", font_small, (150, 150, 150), 300)

        pygame.display.flip()

    pygame.quit()
    sys.exit()


if __name__ == "__main__":
    main()