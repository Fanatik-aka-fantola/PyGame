import pygame
import sys
import random
import os

FPS = 60

# Инициализация Pygame
pygame.init()

# Настройка окна
WIDTH, HEIGHT = 600, 800
screen = pygame.display.set_mode((WIDTH, HEIGHT))
pygame.display.set_caption("Blazing Rise!")  # Ничего умнее я не придумал ¯\_(ツ)_/¯
clock = pygame.time.Clock()
# Счетчик рекорда
score = 0
max_score = 0

# Цвета
WHITE = (255, 255, 255)
BLACK = (0, 0, 0)


class SpeedBoost(pygame.sprite.Sprite):
    def __init__(self):
        super().__init__()
        self.width = WIDTH
        self.height = HEIGHT
        self.image = load_image('x2boost.png')
        self.image = pygame.transform.scale(self.image, (30, 30))
        self.rect = self.image.get_rect()
        self.velocity_y = 0.5
        self.rect.center = (random.randint(50, WIDTH - 50), random.randint(50, HEIGHT // 3))

    def update(self, platforms, lava, boosts):
        self.rect.y += self.velocity_y

        if self.rect.colliderect(lava.rect):
            print("Буст уничтожен лавой!")
            self.kill()


class Lava(pygame.sprite.Sprite):
    def __init__(self):
        super().__init__()
        self.width = WIDTH
        self.height = HEIGHT
        self.image = load_image('lava.png')
        self.rect = self.image.get_rect()
        self.velocity_y = 3 * 1.5
        self.rect.center = (WIDTH // 2, self.height * 1.8)


class Camera:
    def __init__(self):
        self.dy = 0

    # Сдвинуть объект obj на смещение камеры
    def apply(self, obj):
        obj.rect.y += self.dy

    # Позиционировать камеру на объекте target
    def update(self, target):
        self.dy = -(target.rect.y + target.rect.h // 2 - HEIGHT // 2)


# Класс игрока
class Player(pygame.sprite.Sprite):
    def __init__(self):
        super().__init__()
        # Анимация и спрайты
        self.frames = []
        self.current_frame = 0
        self.animation_speed = 0.1  # Скорость анимации
        self.last_update = pygame.time.get_ticks()
        sprite_sheet = load_image("player.png")
        self.cut_sheet(sprite_sheet, columns=9, rows=1)
        self.run_frames = self.frames[1:7]
        self.idle_frame = self.frames[0]
        self.jump_front = self.frames[7]  # Прыжок фронтовой (7-й фрейм)
        self.jump_side = self.frames[8]  # Прыжок боковой (8-й фрейм)

        # Перемещение
        self.image = self.run_frames[0]
        self.rect = self.image.get_rect(center=(WIDTH // 2, HEIGHT - 150))
        self.rect.center = (WIDTH // 2, HEIGHT - 150)  # Начальная позиция игрока
        self.velocity_x = 5 * 1.5
        self.velocity_y = 0  # Скорость по вертикали
        self.gravity = 0.5 * 1.5 # Гравитация
        self.on_ground = True  # Игрок сразу на платформе
        self.last_platform = None  # Это флажок для счетчика рекорда
        self.is_boosted = False # Это флажок для буста (увелечение прыжка)
        self.boost_timer = 0

    def cut_sheet(self, sheet, columns, rows):
        frame_width = sheet.get_width() // columns
        frame_height = sheet.get_height() // rows

        for j in range(rows):
            for i in range(columns):
                # Определение текущего фрейма
                frame_location = (frame_width * i, frame_height * j)
                frame = sheet.subsurface(pygame.Rect(frame_location, (frame_width, frame_height)))
                frame = pygame.transform.scale(frame, (75 * 1.5, 75 * 1.5))

                # Обрезаем лишнее пространство слева и справа (спрайты кривовтые получились)
                frame = self.crop_frame(frame)

                # Добавляем обрезанный фрейм в список
                self.frames.append(frame)

    def crop_frame(self, frame):
        # Получаем кол-во строк и столбцов
        width, height = frame.get_size()

        # Определяем границы по оси X (первое и последнее место, где есть пиксели)
        min_x, max_x = width, 0
        for x in range(width):
            for y in range(height):
                if frame.get_at((x, y))[3] != 0:  # Если не прозрачный пиксель
                    min_x = min(min_x, x)
                    max_x = max(max_x, x)

        # Обрезаем фрейм по найденным границам
        cropped_frame = frame.subsurface(pygame.Rect(min_x, 0, max_x - min_x + 1, height))

        return cropped_frame

    def dead(self):
        global max_score, score
        # После завершения игры обновляем максимальный рекорд
        if score > max_score:
            max_score = score
            save_max_score(max_score)  # Сохраняем новый рекорд в файл
        score = 0

    def update(self, platforms, lava, boosts):
        # Применяем гравитацию
        self.velocity_y += self.gravity
        self.rect.y += self.velocity_y
        lava.rect.y -= lava.velocity_y

        for boost in boosts:
            if self.rect.colliderect(boost.rect):
                boost.kill()
                self.is_boosted = True
                self.boost_timer = pygame.time.get_ticks()

        if self.is_boosted and pygame.time.get_ticks() - self.boost_timer > 5000:
            self.is_boosted = False

        # Проверка вертикальных коллизий (с верхней и нижней частью платформ)
        self.on_ground = False
        # Проверка вертикальных коллизий
        for platform in platforms:
            if self.rect.colliderect(platform.rect):
                if self.velocity_y >= 0:  # Если игрок падает
                    self.rect.bottom = platform.rect.top
                    self.velocity_y = 0
                    self.on_ground = True
                    if self.last_platform != platform:
                        self.last_platform = platform
                        global score
                        score += 1  # Увеличиваем счет
                elif self.velocity_y < 0:  # Если игрок движется вверх
                    self.rect.top = platform.rect.bottom  # Останавливаем движение вверх
                    self.velocity_y = 0
                    # Игрок набрал очки при приземлении

        # Ограничиваем игрока в пределах экрана по вертикали
        if self.rect.bottom > HEIGHT:
            self.rect.bottom = HEIGHT
            self.velocity_y = 0
            self.on_ground = True

        # Горизонтальное движение
        keys = pygame.key.get_pressed()
        if keys[pygame.K_a]:  # Движение влево
            self.rect.x -= self.velocity_x
        if keys[pygame.K_d]:  # Движение вправо
            self.rect.x += self.velocity_x

        # Проверка горизонтальных коллизий
        keys = pygame.key.get_pressed()
        for platform in platforms:
            if self.rect.colliderect(platform.rect):
                if keys[pygame.K_a] and self.rect.left <= platform.rect.right:  # Движение влево
                    self.rect.left = platform.rect.right  # Останавливаем движение влево
                elif keys[pygame.K_d] and self.rect.right >= platform.rect.left:  # Движение вправо
                    self.rect.right = platform.rect.left  # Останавливаем движение вправо

        # Ограничиваем игрока в пределах экрана по горизонтали
        if self.rect.left < 0:
            self.rect.left = 0
        if self.rect.right > WIDTH:
            self.rect.right = WIDTH

        # Обновление анимации
        if not self.on_ground:  # Если игрок в воздухе
            if keys[pygame.K_d]:  # Если движется вправо
                self.image = self.jump_side  # Показываем боковой прыжок (фрейм 8)
            elif keys[pygame.K_a]:  # Если движется влево
                self.image = pygame.transform.flip(self.jump_side, True, False)  # Отзеркаливаем боковой прыжок
            else:  # Если не двигается вправо или влево
                self.image = self.jump_front  # Показываем фронтовой прыжок (фрейм 7)
                prev_center = self.rect.center  # Сохраняем центр перед изменением
                self.rect.size = self.image.get_size()  # Подстраиваем размер под новый спрайт
                self.rect.center = prev_center  # Возвращаем персонажа в то же место
        else:  # Если на земле
            if keys[pygame.K_d]:  # Движение вправо
                now = pygame.time.get_ticks()
                if now - self.last_update > 100:  # Меняем кадры каждые 100 мс
                    self.last_update = now
                    self.current_frame = (self.current_frame + 1) % len(self.run_frames)
                    self.image = self.run_frames[self.current_frame]
            elif keys[pygame.K_a]:  # Движение влево
                now = pygame.time.get_ticks()
                if now - self.last_update > 100:  # Меняем кадры каждые 100 мс
                    self.last_update = now
                    self.current_frame = (self.current_frame + 1) % len(self.run_frames)
                    self.image = pygame.transform.flip(self.run_frames[self.current_frame], True,
                                                       False)  # Отзеркаливаем
            else:  # Если не нажаты клавиши, используем idle
                self.image = self.idle_frame

    def jump(self):
        if self.on_ground:  # Если игрок на земле или на платформе
            if self.is_boosted:
                self.velocity_y = -17 * 1.5
            else:
                self.velocity_y = -13 * 1.5


# Класс смерти (анимации надписи смерти) Мне так захотелось xD
class Dead(pygame.sprite.Sprite):
    def __init__(self):
        super().__init__()
        self.frames = []
        self.current_frame = 0
        self.last_update = pygame.time.get_ticks()
        self.animation_time = 4000  # Анимация должна длиться 4 секунды
        self.total_frames = 67  # Всего 67 кадров
        self.frame_time = self.animation_time // self.total_frames  # Время одного кадра (≈ 60 мс)

        # Загружаем спрайт-лист
        sprite_sheet = load_image("dead.png")  # Путь к изображению
        self.cut_sheet(sprite_sheet, columns=self.total_frames, rows=1)

        self.image = self.frames[0]  # Устанавливаем первый кадр
        self.rect = self.image.get_rect(center=(WIDTH // 2, HEIGHT // 2))  # Центрируем

    def cut_sheet(self, sheet, columns, rows):
        """Разрезаем спрайт-лист на кадры."""
        frame_width = sheet.get_width() // columns
        frame_height = sheet.get_height() // rows

        for j in range(rows):
            for i in range(columns):
                x, y = frame_width * i, frame_height * j
                frame = sheet.subsurface(pygame.Rect(x, y, frame_width, frame_height))
                frame = pygame.transform.scale(frame, (WIDTH, frame_height))  # Растягиваем по ширине экрана
                self.frames.append(frame)

    def update(self):
        """Обновляем кадры анимации."""
        now = pygame.time.get_ticks()
        if now - self.last_update >= self.frame_time:  # Смена кадра каждые 60 мс
            self.last_update = now
            self.current_frame += 1

            if self.current_frame < self.total_frames:  # Если кадры ещё есть
                self.image = self.frames[self.current_frame]
            else:
                self.kill()  # Удаляем спрайт после анимации


# Класс платформы
class Platform(pygame.sprite.Sprite):
    def __init__(self, width, height, x, y):
        super().__init__()
        self.image = load_image('platform.png')
        self.image = pygame.transform.scale(self.image, (width, height))
        self.rect = self.image.get_rect()
        self.rect.x = x
        self.rect.y = y


# Загрузить максимальный рекорд
def load_max_score():
    try:
        with open("data/max_score.txt", "r") as file:
            return int(file.read())
    except FileNotFoundError:
        return 0


# Сохранить/обновить мааксимальный рекрод
def save_max_score(score):
    with open("data/max_score.txt", "w") as file:
        file.write(str(score))


# Остоновка программы
def terminate():
    pygame.quit()
    sys.exit()


# Загрузить изображение
def load_image(name, colorkey=None):  # Белый фон будет удалён
    fullname = os.path.join('data', name)
    if not os.path.isfile(fullname):
        print(f"Файл с изображением '{fullname}' не найден")
        sys.exit()
    image = pygame.image.load(fullname)
    if colorkey is not None:
        image = image.convert()
        image.set_colorkey(colorkey)  # Удаляем белый фон
    else:
        image = image.convert_alpha()
    return image


# Функция для генерации новой платформы
def generate_platform(platforms, all_sprites):
    platform_width = 100 * 1.5
    platform_height = 20 * 1.5

    max_horizontal_gap = 200 * 1.5 # Максимальное расстояние по горизонтали
    min_horizontal_gap = 50  * 1.5 # Минимальное расстояние по горизонтали
    min_vertical_gap = 100  * 1.5 # Минимальное расстояние по вертикали
    max_vertical_gap = 150 * 1.5  # Максимальное расстояние по вертикали

    if platforms:
        highest_platform = min(platforms, key=lambda p: p.rect.y)  # Самая высокая платформа
        while True:
            # Генерация случайной позиции для платформы
            new_x = random.randint(0, WIDTH - platform_width)
            new_y = highest_platform.rect.y - random.randint(min_vertical_gap, max_vertical_gap)

            # Проверка, чтобы платформа была достижима
            if abs(new_x - highest_platform.rect.x) >= min_horizontal_gap and \
               abs(new_x - highest_platform.rect.x) <= max_horizontal_gap:
                break  # Условие выполнено, можно генерировать платформу
    else:
        new_x = random.randint(0, WIDTH - platform_width)
        new_y = HEIGHT - 50  # Начальная платформа

    new_platform = Platform(platform_width, platform_height, new_x, new_y)
    platforms.add(new_platform)
    all_sprites.add(new_platform)


# Сама надпись 'рекорд' при игре
def score_count():
    global score
    global max_score
    font = pygame.font.Font(None, 30)

    # Отображение текущего счета
    text_surface = font.render(str(score), True, pygame.Color('black'))
    text_rect = text_surface.get_rect(topleft=(75, 10))  # Сдвигаем вправо, чтобы не наезжало на картинку

    # Отображение изображения "MAX SCORE"
    image_score = load_image('score.png')  # Заменил на нужное изображение
    image_score = pygame.transform.scale(image_score, (60, text_rect.height - 3))
    image_score_rect = image_score.get_rect(topleft=(10, 10))

    screen.blit(image_score, image_score_rect)  # Рисуем картинку
    screen.blit(text_surface, text_rect)  # Рисуем счет


# Основной игровой цикл
def main():
    global clock, score, max_score, FPS
    running = True
    game_over = False  # Флаг для отслеживания состояния игры

    start_screen()
    fon = pygame.transform.scale(load_image('fon.png'), (WIDTH, HEIGHT))  # Масштабируем под размер окна

    # Создаем игрока и камеру
    camera = Camera()
    lava = Lava()
    player = Player()

    # Группы спрайтов
    all_sprites = pygame.sprite.Group()
    platforms = pygame.sprite.Group()
    boosts = pygame.sprite.Group()

    # Добавляем игрока в группу спрайтов
    all_sprites.add(player)
    all_sprites.add(lava)

    # Создаем начальную платформу под игроком
    start_platform = Platform(100 * 1.5, 20 * 1.5, WIDTH // 2 - 50, HEIGHT - 100)
    platforms.add(start_platform)
    all_sprites.add(start_platform)

    # Создаем дополнительные платформы
    for i in range(2):
        generate_platform(platforms, all_sprites)

    last_score = 0
    while running:
        screen.blit(fon, (0, 0))

        # Обработка событий
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_SPACE:
                    player.jump()

        # Если игра завершена, не обновляем объекты
        if not game_over:
            # Обновление камеры
            camera.update(player)
            for sprite in all_sprites:
                camera.apply(sprite)  # Двигаем все объекты, включая игрока

            # Обновление спрайтов
            all_sprites.update(platforms, lava, boosts)

            # Генерация новой платформы, если самая высокая платформа близко к верхней границе
            if platforms:
                highest_platform = min(platforms, key=lambda p: p.rect.y)
                if highest_platform.rect.y > HEIGHT // 4:  # Если самая высокая платформа близко к верху
                    generate_platform(platforms, all_sprites)

            # Удаление платформ, которые ушли за пределы экрана
            for platform in platforms:
                if platform.rect.y > HEIGHT:
                    platform.kill()

            # Проверка на смерть игрока
            if player.rect.bottom >= lava.rect.top:
                game_over = True  # Игра завершена
                player.dead()
                # Вызываем метод смерти

        # Отрисовка спрайтов
        all_sprites.draw(screen)

        # Отображение счета
        score_count()

        if score % 15 == 0 and score != last_score: # каждую 15 платформу будет спавниться бустер
            boost = SpeedBoost()
            boosts.add(boost)
            all_sprites.add(boost)
        # Со временем игра будет становится сложнее - общая скорость увеличится, а спустя время лава
        # будет становится быстрее
        if score % 3 == 0 and score != last_score:
            FPS *= 1.005
            last_score = score  # Обновляем last_score, чтобы не ускоряться снова
        if score % 30 == 0 and score != last_score and score <= 100:
            lava.velocity_y += 1
            last_score = score
        if score % 100 == 0 and score != last_score:
            lava.velocity_y += 2
            last_score = score

        # Если игра завершена, отображаем экран проигрыша
        if game_over:
            running = False  # Завершаем игровой цикл
            FPS = 60
            new_screen()
        # Обновление экрана
        pygame.display.flip()
        clock.tick(FPS)


def start_screen():
    global max_score
    max_score = load_max_score()  # Загружаем максимальный рекорд

    fon = pygame.transform.scale(load_image('fon.png'), (WIDTH, HEIGHT))  # Масштабируем под размер окна
    screen.blit(fon, (0, 0))

    # Отображение максимального рекорда
    font = pygame.font.Font(None, 100)
    text_surface = font.render(str(max_score), True, pygame.Color('black'))
    text_rect = text_surface.get_rect(topleft=(WIDTH // 2 + 145, HEIGHT // 2))
    screen.blit(text_surface, text_rect)

    # Отображение изображения "MAX SCORE"
    image_score = load_image('max_score.png')  # Заменил на нужное изображение
    image_score = pygame.transform.scale(image_score, (300, text_rect.height - 5))
    image_score_rect = image_score.get_rect(topleft=(WIDTH // 2 - 160, HEIGHT // 2))
    screen.blit(image_score, image_score_rect)  # Рисуем картинку

    # Отображение изображения "Blazing rise"
    image_name = load_image('name.png')  # Заменил на нужное изображение
    image_name = pygame.transform.scale(image_name, (350, 250))
    image_name_rect = image_score.get_rect(topleft=(WIDTH // 2 - 160, 0))
    screen.blit(image_name, image_name_rect)  # Рисуем картинку

    # Отображение надписи 'Press any key for start game'
    font = pygame.font.Font(None, 25)
    text_surface = font.render('Press any key for start game', True, pygame.Color('black'))
    text_rect = text_surface.get_rect(topleft=(WIDTH // 2 - 115, HEIGHT // 2 + 200))
    screen.blit(text_surface, text_rect)



    while True:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                terminate()
            if event.type == pygame.KEYDOWN or event.type == pygame.MOUSEBUTTONDOWN:
                return  # Начинаем игру
        pygame.display.flip()
        clock.tick(FPS)


def new_screen():
    dead_sprite = Dead()
    all_sprites = pygame.sprite.Group()
    all_sprites.add(dead_sprite)

    # Проигрываем анимацию смерти на чёрном фоне
    running = True
    while running:
        screen.fill((4, 2, 4))  # Чёрный фон (в гифке не чистый черный, пришлось подстравиваться)
        all_sprites.update()
        all_sprites.draw(screen)

        pygame.display.flip()
        clock.tick(FPS)

        # Проверяем, закончилась ли анимация (если спрайт исчез, значит, `self.kill()` в самом классе сработал)
        if not dead_sprite.alive():
            running = False  # Выходим из цикла, анимация смерти завершена

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                terminate()
            if event.type == pygame.KEYDOWN or event.type == pygame.MOUSEBUTTONDOWN:
                running = False  # Выходим из цикла

    # Показываем экран с рекордом
    global max_score
    max_score = load_max_score()  # Загружаем максимальный рекорд


    pygame.display.flip()
    clock.tick(FPS)

    main()


if __name__ == "__main__":
    main()
