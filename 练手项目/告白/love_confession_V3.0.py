import pygame
import random
import math
import sys

# ================= ⚙️ 参数调优 (为复刻视频效果) =================
WIDTH, HEIGHT = 800, 800
CENTER_X, CENTER_Y = WIDTH // 2, HEIGHT // 2 - 60  # 爱心悬空

# 颜色：视频中的冷艳紫
COLORS = [
    (255, 255, 255),  # 核心白亮
    (255, 150, 255),  # 浅粉紫
    (200, 50, 255),  # 霓虹紫
    (140, 20, 220),  # 深紫
]

# 粒子数量控制 (为了达到视频的“绵密感”，数量要多，但粒子要小)
HEART_POINTS = 3000  # 构成爱心轮廓的粒子数
FALLING_RATE = 30  # 每帧掉落的粒子数
GRAVITY = 0.2  # 下落加速度
FLOOR_Y = 280  # 地面高度
# =============================================================

pygame.init()
screen = pygame.display.set_mode((WIDTH, HEIGHT))
pygame.display.set_caption("Purple Sand Heart - Exact Replica")
clock = pygame.time.Clock()


# --- 💜 核心算法1：生成完美的爱心点云 ---
def generate_heart_shape(num_points):
    points = []
    for _ in range(num_points):
        # 1. 在 0 到 2pi 之间随机采样，但为了均匀，可以稍微抖动
        t = random.uniform(0, 2 * math.pi)

        # 2. 经典爱心方程
        x = 16 * math.sin(t) ** 3
        y = -(13 * math.cos(t) - 5 * math.cos(2 * t) - 2 * math.cos(3 * t) - math.cos(4 * t))

        # 3. 赋予一定的“壁厚”，视频里的爱心是有厚度的壳
        # 我们不仅在一个平面，而是在 z 轴也就是厚度方向有随机分布
        # 同时在 x, y 方向也微调，让它看起来是毛茸茸的
        scale = 12  # 大小系数
        thickness = random.uniform(-4, 4)  # Z轴厚度

        # 在轮廓周围随机扩散一点点，形成“星尘”感
        spread = random.uniform(0.95, 1.05)

        px = x * scale * spread
        py = y * scale * spread
        pz = thickness * scale * 0.5  # 厚度系数

        # 预先计算好颜色索引
        c_idx = random.randint(0, len(COLORS) - 1)

        points.append([px, py, pz, c_idx])
    return points


# 预生成爱心结构 (这是静态的骨架，旋转时使用)
BASE_HEART_POINTS = generate_heart_shape(HEART_POINTS)


# --- 💜 核心算法2：粒子系统 ---
class ParticleSystem:
    def __init__(self):
        self.falling_particles = []  # 正在下落的粒子
        self.floor_particles = []  # 地上的粒子

    def spawn_drop(self, heart_rotated_points):
        # 从当前旋转后的爱心上，随机挑几个点作为“掉落源”
        for _ in range(FALLING_RATE):
            # 随机选一个爱心上的点
            src = random.choice(heart_rotated_points)
            x, y, z, c_idx = src

            # 生成下落粒子: [x, y, z, vx, vy, vz, color_idx]
            # vy 初始为 0，受重力加速
            # 给一点随机的水平初速度，模拟“散落”
            vx = random.uniform(-0.5, 0.5)
            vz = random.uniform(-0.5, 0.5)

            self.falling_particles.append([x, y, z, vx, 0, vz, c_idx])

    def update(self):
        # --- A. 更新下落粒子 ---
        # 倒序遍历以便删除
        for i in range(len(self.falling_particles) - 1, -1, -1):
            p = self.falling_particles[i]
            # p = [x, y, z, vx, vy, vz, c]

            # 重力作用
            p[4] += GRAVITY  # vy 增加

            # 移动
            p[0] += p[3]  # x
            p[1] += p[4]  # y
            p[2] += p[5]  # z

            # 撞击地面检测
            if p[1] >= FLOOR_Y:
                # 变成地面粒子
                # 撞击后，向四周溅射 (Splash)
                splash_angle = random.uniform(0, 6.28)
                splash_speed = random.uniform(0.5, 3.0)  # 溅射速度

                fx = p[0]
                fz = p[2]
                fv_x = math.cos(splash_angle) * splash_speed
                fv_z = math.sin(splash_angle) * splash_speed

                # 地面粒子结构: [x, z, vx, vz, life, color_idx]
                # 注意：地面粒子只需要 x, z 坐标，y 固定为 FLOOR_Y
                self.floor_particles.append([fx, fz, fv_x, fv_z, 255, p[6]])

                # 从下落列表中移除
                self.falling_particles.pop(i)

        # --- B. 更新地面粒子 ---
        for i in range(len(self.floor_particles) - 1, -1, -1):
            fp = self.floor_particles[i]
            # fp = [x, z, vx, vz, life, c]

            # 扩散
            fp[0] += fp[2]  # x
            fp[1] += fp[3]  # z

            # 摩擦力 (慢慢停下来)
            fp[2] *= 0.9
            fp[3] *= 0.9

            # 寿命衰减 (视频里地面的光点会闪烁消失)
            fp[4] -= 4  # 衰减速度

            if fp[4] <= 0:
                self.floor_particles.pop(i)


# --- 渲染辅助 ---
# 3D 投影公式
def project(x, y, z, fov=600, viewer_dist=1000):
    if z + viewer_dist == 0: return None
    factor = fov / (viewer_dist + z)
    screen_x = x * factor + CENTER_X
    screen_y = y * factor + CENTER_Y
    # 粒子大小随距离变化
    size = max(1, 3 * factor)
    return screen_x, screen_y, size, factor


# --- 主程序 ---
def main():
    running = True
    angle_y = 0
    system = ParticleSystem()

    # 预渲染发光粒子纹理 (性能优化)
    # 我们画圆点，但用 BLEND_ADD 模式
    # 视频里的粒子很小，是粉尘状的

    while running:
        # 1. 清屏 (纯黑背景，带微弱紫光)
        screen.fill((5, 0, 10))

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False

        # 2. 旋转爱心
        angle_y += 0.015
        cos_a = math.cos(angle_y)
        sin_a = math.sin(angle_y)

        # 存储这一帧所有要画的点 [z_depth, x, y, size, color]
        render_list = []

        # --- A. 处理爱心本体 ---
        # 旋转并计算爱心上的所有点
        current_heart_points = []  # 暂存旋转后的坐标用于生成掉落

        for p in BASE_HEART_POINTS:
            x, y, z, c = p
            # 绕 Y 轴旋转
            rx = x * cos_a - z * sin_a
            ry = y
            rz = x * sin_a + z * cos_a

            current_heart_points.append((rx, ry, rz, c))

            # 投影
            res = project(rx, ry, rz)
            if res:
                sx, sy, size, _ = res
                render_list.append((rz, sx, sy, size, COLORS[c], "heart"))

        # --- B. 生成掉落粒子 ---
        system.spawn_drop(current_heart_points)
        system.update()

        # --- C. 处理下落粒子 ---
        for p in system.falling_particles:
            x, y, z, _, _, _, c = p
            # 下落粒子也要跟着相机视角旋转吗？
            # 视频中看起来下落的粒子是独立于爱心旋转的，但相机在转。
            # 这里我们假设相机不动，爱心在转，所以下落粒子一旦脱离爱心，
            # 它的 x, z 坐标是世界坐标，但也需要应用“相机旋转”来观察它（如果是相机转）
            # 或者简单点：粒子生成时的坐标就是世界坐标，我们只对爱心做旋转。
            # 为了效果更像视频，让粒子保持生成时的绝对位置，只做投影

            # 为了让画面协调，我们假设是摄像机在围着物体转，
            # 所以所有粒子（包括空中的）都需要逆向旋转一下，或者直接复用旋转逻辑
            # 这里为了简单，我们让落下的粒子也接受旋转矩阵（仿佛物体整体在转台转）
            rx = x * cos_a - z * sin_a
            rz = x * sin_a + z * cos_a

            res = project(rx, y, rz)
            if res:
                sx, sy, size, _ = res
                render_list.append((rz, sx, sy, size, COLORS[c], "drop"))

        # --- D. 处理地面粒子 ---
        for p in system.floor_particles:
            x, z, _, _, life, c = p
            y = FLOOR_Y

            rx = x * cos_a - z * sin_a
            rz = x * sin_a + z * cos_a

            res = project(rx, y, rz)
            if res:
                sx, sy, size, _ = res
                # 地面粒子颜色受 life 影响 (透明度)
                base_c = COLORS[c]
                # 简单的变暗处理
                fade = life / 255.0
                final_c = (base_c[0] * fade, base_c[1] * fade, base_c[2] * fade)

                render_list.append((rz, sx, sy, size, final_c, "floor"))

        # --- E. 渲染 (关键步骤) ---
        # 1. 排序：Z-Sort (画家算法)，从远到近
        render_list.sort(key=lambda x: x[0], reverse=True)

        # 2. 绘制
        for item in render_list:
            _, sx, sy, size, color, p_type = item

            # 视频风格复刻关键：
            # 不用贴图，用 draw.circle 或者 draw.rect(1像素)
            # 因为视频里是“沙砾感”，不是柔光球

            # 限制范围
            if 0 <= sx < WIDTH and 0 <= sy < HEIGHT:
                if p_type == "floor":
                    # 地面粒子画扁一点，模拟圆盘
                    pygame.draw.ellipse(screen, color, (sx - size, sy - size * 0.3, size * 2, size * 0.6))
                else:
                    # 空中粒子和爱心粒子
                    # 使用 BLEND_ADD 实现高亮叠加
                    # 但 Pygame 的 draw 函数不直接支持 blend。
                    # 我们用一个小技巧：如果颜色很亮，就画实心；

                    # 简单绘制：
                    # pygame.draw.circle(screen, color, (int(sx), int(sy)), max(1, int(size/2)))

                    # 进阶绘制 (为了辉光)：
                    # 如果粒子很近(size大)，画个光晕
                    if size > 2:
                        s = pygame.Surface((int(size * 2), int(size * 2)), pygame.SRCALPHA)
                        # 核心
                        pygame.draw.circle(s, color, (int(size), int(size)), int(size / 2))
                        # 光晕
                        pygame.draw.circle(s, (*color[:3], 100), (int(size), int(size)), int(size))
                        screen.blit(s, (sx - size, sy - size), special_flags=pygame.BLEND_ADD)
                    else:
                        screen.set_at((int(sx), int(sy)), color)  # 单像素绘制，最快且最像沙子

        pygame.display.flip()
        clock.tick(60)

    pygame.quit()
    sys.exit()


if __name__ == "__main__":
    main()