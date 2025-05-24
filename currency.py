import pygame
import random
import os

# Инициализация Pygame
pygame.init()
win = pygame.display.set_mode((400, 600))
pygame.display.set_caption("Flappy Bird")
font = pygame.font.SysFont("Arial", 30)

# Параметры птички
bird_x = 50
bird_y = 300
bird_radius = 20
velocity = 0
gravity = 0.5
jump = -8

# Трубы
pipes = []
gap = 200
pipe_frequency = 1500  # миллисекунды между трубами
last_pipe = pygame.time.get_ticks()

# Счёт
score = 0
high_score = 0

# Загрузка рекорда
if os.path.exists("highscore.txt"):
    with open("highscore.txt", "r") as f:
        high_score = int(f.read())

# Игровой цикл
run = True
clock = pygame.time.Clock()

while run:
    clock.tick(60)
    
    # Обработка событий
    for e in pygame.event.get():
        if e.type == pygame.QUIT:
            run = False
        if e.type == pygame.KEYDOWN and e.key == pygame.K_SPACE:
            velocity = jump
    
    # Гравитация
    velocity += gravity
    bird_y += velocity
    
    # Генерация труб
    time_now = pygame.time.get_ticks()
    if time_now - last_pipe > pipe_frequency:
        h = random.randint(100, 400)
        pipes.append([400, h])
        last_pipe = time_now
    
    # Движение труб
    for pipe in pipes:
        pipe[0] -= 3
    
    # Удаление труб за экраном
    pipes = [pipe for pipe in pipes if pipe[0] > -70]
    
    # Столкновения с трубами
    for x, h in pipes:
        if bird_x + bird_radius > x and bird_x - bird_radius < x + 70:
            if bird_y - bird_radius < h or bird_y + bird_radius > h + gap:
                run = False
    
    # Счёт
    for x, h in pipes:
        if x + 70 == bird_x:
            score += 1
            if score > high_score:
                high_score = score
                # Сохраняем рекорд
                with open("highscore.txt", "w") as f:
                    f.write(str(high_score))
    
    # Границы экрана
    if bird_y > 600 or bird_y < 0:
        run = False
    
    # Отрисовка
    win.fill((0, 0, 0))
    
    # Рисуем трубы
    for x, h in pipes:
        pygame.draw.rect(win, (0, 200, 0), (x, 0, 70, h))
        pygame.draw.rect(win, (0, 200, 0), (x, h + gap, 70, 600))
    
    # Рисуем птичку
    pygame.draw.circle(win, (255, 255, 255), (bird_x, int(bird_y)), bird_radius)
    
    # Рисуем счёт
    score_text = font.render(f"Score: {score}", True, (255, 255, 255))
    high_score_text = font.render(f"High Score: {high_score}", True, (255, 255, 255))
    win.blit(score_text, (10, 10))
    win.blit(high_score_text, (10, 50))
    
    pygame.display.update()

pygame.quit()  