import os
import sys

import pygame

from core import *


def resource_path(relative_path):
    """Получить абсолютный путь"""
    try:
        # если скомпилирован .exe файл
        base_path = sys._MEIPASS
    except Exception:
        base_path = os.path.abspath(".")

    return os.path.join(base_path, relative_path)


def terminate():
    """Завершить работу"""
    pygame.quit()
    sys.exit()


def load_image(name, colorkey=None, size=None):
    """Загрузить изображение"""
    fullname = os.path.join('data', name)

    fullname = resource_path(fullname)

    if not os.path.isfile(fullname):
        print(f"Файл с изображением '{fullname}' не найден")
        sys.exit()
    image = pygame.image.load(fullname)

    if colorkey is not None:
        image = image.convert()
        if colorkey == -1:
            colorkey = image.get_at((0, 0))
        image.set_colorkey(colorkey)
    else:
        image = image.convert_alpha()

    if size is not None:
        image = pygame.transform.scale(image, size)

    return image


def gen_piece_image_name(image_name, color):
    """Сгенерировать путь к изображению"""
    color_name = "black" if color == BLACK else "white"
    return f"{color_name}_{image_name}.png"


def human_format(coordinates):
    """Преобразование координат в читаемый вид"""
    row, col = coordinates
    return chr(ord('A') + col) + str(row + 1)


def start_screen():
    """Заставка"""
    screen.fill(BACKGROUND_COLOR)
    image = load_image(START_SCREEN_IMAGE, size=SIZE)
    screen.blit(image, (0, 0))
    pygame.display.flip()

    while True:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                terminate()
            elif event.type == pygame.KEYDOWN or event.type == pygame.MOUSEBUTTONDOWN:
                return


def start_new_game():
    global game
    game = Game()


def flip_board():
    global board_reversed
    board_reversed = not board_reversed


class Game:
    """Класс игры"""

    def __init__(self):
        self.board = Board()
        self.history = []
        self.selected_cell = None

        self.promoting_cell = None
        self.new_promoting_piece = None

        self.locked = False

        self.winner = None
        self.is_check = False

        self.left_indent = 70
        self.top_indent = 90
        self.cell_size = 50
        self.border_width = 30

        self.width, self.height = 8, 8

        selector_indent = 30
        self.selector_left = self.left_indent + selector_indent
        self.selector_width = self.cell_size * self.width - selector_indent * 2
        self.selector_height = self.selector_cell_size = self.selector_width // len(SELECTOR_PIECES)
        self.selector_top = int(self.top_indent + self.cell_size * self.height / 2 - self.selector_height / 2)

        self.pieces = dict()
        for piece, name in PIECES_IMAGES_NAMES.items():
            item = dict()
            for color in BLACK, WHITE:
                item[color] = load_image(gen_piece_image_name(name, color))
            self.pieces[piece] = item

        self.buttons = self.get_buttons()

    def get_buttons(self):
        """Получить информацию о кнопках"""
        horizontal_indent = 40
        left = self.left_indent + self.cell_size * self.width + self.border_width + horizontal_indent
        right = left + 130 + horizontal_indent * 2
        bottom = self.top_indent + self.cell_size * self.height + self.border_width
        vertical_indent = 55
        height = 40
        buttons = []
        for i, (title, size, func) in enumerate(BUTTONS[::-1]):
            item = {
                "title": title,
                "size": size,
                "func": func,
                "left": left,
                "right": right,
                "bottom": bottom - vertical_indent * i,
                "top": bottom - vertical_indent * i - height
            }
            buttons.append(item)
        return buttons

    def get_coords(self, pos):
        """Получить координаты клетки по позиции"""
        row = (pos[1] - self.top_indent) // self.cell_size
        row = 7 - row if not board_reversed else row
        col = (pos[0] - self.left_indent) // self.cell_size

        if col not in range(self.width) or row not in range(self.height):
            return None
        return row, col

    def get_position(self, coordinates):
        """Получить позицию по координатам клетки"""
        row, col = coordinates
        row = 7 - row if not board_reversed else row
        x = self.left_indent + self.cell_size * col
        y = self.top_indent + self.cell_size * row
        return x, y

    def render(self, screen):
        def write_text(string, x, y, size):
            """Написать текст"""
            font = pygame.font.Font(None, size)
            text = font.render(string, True, MAIN_COLOR)
            text_x = x - text.get_width() // 2
            text_y = y - text.get_height() // 2
            screen.blit(text, (text_x, text_y))

        def draw_borders():
            """Нарисовать границы доски"""
            color = MAIN_COLOR

            inner_rect = (self.left_indent - 1, self.top_indent - 1,
                          self.cell_size * self.width + 2, self.cell_size * self.height + 2)
            outer_rect = (inner_rect[0] - self.border_width, inner_rect[1] - self.border_width,
                          inner_rect[2] + self.border_width * 2, inner_rect[3] + self.border_width * 2)

            pygame.draw.rect(screen, color, inner_rect, 1)
            pygame.draw.rect(screen, color, outer_rect, 1)

        def draw_scales():
            """Нарисовать линейки рядом с доской"""
            size = 30

            for i in range(self.height):
                number = i if not board_reversed else 7 - i
                y = self.top_indent + self.cell_size * (self.height - i - 0.5)
                for x in (self.left_indent - self.border_width // 2,
                          self.left_indent + self.cell_size * self.width + self.border_width // 2):
                    write_text(str(number + 1), x, y, size)

            for i in range(self.width):
                x = self.left_indent + self.cell_size * (i + 0.5)
                for y in (self.top_indent - self.border_width // 2,
                          self.top_indent + self.cell_size * self.height + self.border_width // 2):
                    write_text(chr(ord('A') + i), x, y, size)

        def draw_move():
            """Написать чей ход"""
            side = "БЕЛЫХ" if self.board.color == WHITE else "ЧЁРНЫХ"
            size = 40
            x = self.left_indent + self.cell_size * (self.width / 2)
            y = self.top_indent - self.border_width - 30
            write_text("ХОД " + side, x, y, size)

        def draw_winner():
            """Написать информацию о шахе/победителе"""
            text = None
            if self.winner in (BLACK, WHITE):
                side = "БЕЛЫЕ" if self.winner == WHITE else "ЧЁРНЫЕ"
                text = "ПОБЕДИЛИ " + side
            elif self.is_check:
                text = "ШАХ"

            if not text:
                return

            size = 40
            x = self.left_indent + self.cell_size * (self.width / 2)
            y = self.top_indent + self.cell_size * self.height + self.border_width + 30
            write_text(text, x, y, size)

        def draw_cells():
            """Нарисовать сетку"""
            mod = {
                0: MAIN_COLOR,
                1: BACKGROUND_COLOR
            }
            for y in range(self.height):
                for x in range(self.width):
                    rect = (self.left_indent + self.cell_size * x, self.top_indent + self.cell_size * y,
                            self.cell_size, self.cell_size)
                    color = mod[(x + y) % 2]
                    pygame.draw.rect(screen, color, rect, 0)

        def draw_pieces():
            """Отрисовать фигуры"""

            def draw_piece():
                orig_image = self.pieces[piece.__class__][piece.color]
                image = pygame.transform.scale(orig_image, (self.cell_size, self.cell_size))
                rect = image.get_rect().move(*self.get_position((row, col)))
                screen.blit(image, rect)

            for row, line in enumerate(self.board.field):
                for col, piece in enumerate(line):
                    if isinstance(piece, Figure):
                        draw_piece()

        def draw_selected_cells_borders():
            """Выделить выбранную и доступные для хода клетки"""

            def draw_cell_borders(coordinates, color):
                """Выделить клетку"""
                x, y = self.get_position(coordinates)
                width = 3
                indent = 4
                rect = (x + indent, y + indent,
                        self.cell_size - indent * 2, self.cell_size - indent * 2)
                pygame.draw.rect(screen, color, rect, width)

            if not self.selected_cell:
                return

            draw_cell_borders(self.selected_cell, SELECTED_CELL_COLOR)
            for coords in self.board.move_options(*self.selected_cell):
                draw_cell_borders(coords, AVAILABLE_MOVES_COLOR)

        def draw_history():
            """Отобразить историю ходов"""
            indent = 40

            x_first = self.left_indent + self.cell_size * self.width + self.border_width + 80
            x_second = x_first + 130
            y = self.top_indent - self.border_width - 30
            write_text("ИСТОРИЯ", (x_first + x_second) // 2, y, 40)
            y += 5

            count = 9 * 2
            last_records = self.history[-count:] if len(self.history) % 2 == 0 else self.history[-count + 1:]
            for i, record in enumerate(last_records):
                if i % 2 == 0:
                    x = x_first
                    y += indent
                else:
                    x = x_second
                write_text(record, x, y, 30)

        def draw_buttons():
            """Отрисовать кнопки"""
            for button in self.buttons:
                left, top, right, bottom = button["left"], button["top"], button["right"], button["bottom"]
                width, height = right - left, bottom - top
                rect = (left, top, width, height)
                pygame.draw.rect(screen, MAIN_COLOR, rect, 1)
                write_text(button["title"], left + width // 2, top + height // 2, button["size"])

        def draw_pieces_selector():
            """Отрисовать окно выбора фигур для превращения пешки"""
            text_height = 40

            def draw_background():
                color = BACKGROUND_COLOR
                rect = (self.selector_left, self.selector_top - text_height,
                        self.selector_width, self.selector_height + text_height)
                pygame.draw.rect(screen, color, rect, 0)

            def draw_borders():
                color = MAIN_COLOR
                width = 1

                rect = (self.selector_left, self.selector_top - text_height,
                        self.selector_width, self.selector_height + text_height)
                pygame.draw.rect(screen, color, rect, width)

                for i in range(len(SELECTOR_PIECES)):
                    rect = (self.selector_left + i * self.selector_cell_size,
                            self.selector_top, self.selector_cell_size, self.selector_height)
                    pygame.draw.rect(screen, color, rect, width)

            def draw_title():
                x = self.selector_left + self.selector_width // 2
                y = self.selector_top - text_height // 2
                title = "Выберите фигуру"
                size = 30
                write_text(title, x, y, size)

            def draw_selector_pieces():
                for i, piece in enumerate(SELECTOR_PIECES):
                    orig_image = self.pieces[piece][self.board.color]
                    image = pygame.transform.scale(orig_image, (self.selector_cell_size,) * 2)
                    x = self.selector_left + i * self.selector_cell_size
                    y = self.selector_top
                    rect = image.get_rect().move(x, y)
                    screen.blit(image, rect)

            if not self.promoting_cell:
                return
            draw_background()
            draw_borders()
            draw_title()
            draw_selector_pieces()

        screen.fill(BACKGROUND_COLOR)

        draw_borders()
        draw_scales()
        draw_cells()
        draw_selected_cells_borders()
        draw_move()
        draw_winner()
        draw_pieces()
        draw_history()
        draw_buttons()
        draw_pieces_selector()

    def check_winner(self, row, col):
        """Проверка, может ли фигура поставить шах/мат"""
        result = self.board.check_and_mate(row, col)
        if result is None:
            self.is_check = False
            return
        if result == CHECK:
            self.is_check = True
            return
        if result == MATE:
            self.winner = opponent(self.board.color)
            self.locked = True

    def add_to_history(self, row1, col1, row2, col2):
        """Добавить запись в историю"""
        self.history.append(human_format((row1, col1)) + ' -> ' + human_format((row2, col2)))

    def get_piece_from_selector(self, mouse_pos):
        """Обработать клик по окну выбора фигур"""
        if not self.selector_top <= mouse_pos[1] <= self.selector_top + self.selector_height:
            return None
        index = (mouse_pos[0] - self.selector_left) // self.selector_cell_size
        if index not in range(len(SELECTOR_PIECES)):
            return None
        return SELECTOR_PIECES[index]

    def get_button_func(self, mouse_pos):
        """Обработать клик по кнопкам"""
        x, y = mouse_pos
        for button in self.buttons:
            if x in range(button["left"], button["right"] + 1) \
                    and y in range(button["top"], button["bottom"]):
                return button["func"]

    def on_click(self, cell_coordinates):
        """Обработка выбранной фигуры"""
        row2, col2 = cell_coordinates

        # Если ранее не была выбрана фигура
        if self.selected_cell is None:
            cell = self.board.field[row2][col2]
            if isinstance(cell, Figure) and cell.color == self.board.color:
                self.selected_cell = cell_coordinates
            return

        # Если пользователь выбрал ту же фигуру, что и ранее
        if cell_coordinates == self.selected_cell:
            self.selected_cell = None
            return

        row1, col1 = self.selected_cell
        cell = self.board.field[row1][col1]

        if self.board.try_promote_pawn(row1, col1, row2, col2):
            self.promoting_cell = row1, col1, row2, col2
            return

        if isinstance(cell, Figure) and self.board.try_move(row1, col1, row2, col2):
            self.board.move_piece(row1, col1, row2, col2)
            self.check_winner(row2, col2)
            # Добавить запись в историю
            self.add_to_history(row1, col1, row2, col2)
        self.selected_cell = None

    def get_click(self, mouse_pos):
        """Обработать клик"""

        func = self.get_button_func(mouse_pos)
        if func is not None:
            return func()

        # Проверка заблокировано ли поле
        if self.locked:
            return

        if self.promoting_cell:
            piece = self.get_piece_from_selector(mouse_pos)
            if piece:
                self.board.move_and_promote_pawn(*self.promoting_cell, piece)
                self.check_winner(*self.promoting_cell[2:])
                self.add_to_history(*self.promoting_cell)
                self.promoting_cell = None
            return

        cell = self.get_coords(mouse_pos)
        if not cell:
            return
        self.on_click(cell)


SIZE = WIDTH, HEIGHT = 800, 600
CAPTION = "Шахматы"
ICON = "icon.png"

BACKGROUND_COLOR = pygame.Color(139, 69, 19)
MAIN_COLOR = pygame.Color(214, 171, 111)
SELECTED_CELL_COLOR = pygame.Color(255, 41, 70)
AVAILABLE_MOVES_COLOR = pygame.Color(69, 148, 38)

PIECES_IMAGES_NAMES = {
    Pawn: "pawn",
    Rook: "rook",
    Knight: "knight",
    Bishop: "bishop",
    Queen: "queen",
    King: "king"
}

START_SCREEN_IMAGE = "start_screen.png"

SELECTOR_PIECES = (Pawn, Rook, Knight, Bishop, Queen)

BUTTONS = [
    ("ПЕРЕВЕРНУТЬ ДОСКУ", 26, flip_board),
    ("НОВАЯ ИГРА", 36, start_new_game)
]

if __name__ == "__main__":
    pygame.init()
    pygame.display.set_caption(CAPTION)
    screen = pygame.display.set_mode(SIZE)

    icon = load_image(ICON)
    pygame.display.set_icon(icon)

    start_screen()

    board_reversed = False

    game = Game()
    game.render(screen)

    running = True
    while running:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                terminate()
            if event.type == pygame.MOUSEBUTTONDOWN:
                game.get_click(event.pos)
                game.render(screen)

        pygame.display.flip()

    pygame.quit()
