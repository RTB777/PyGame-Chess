def opponent(color):
    """Возвращает цвет противника."""
    if color == WHITE:
        return BLACK
    else:
        return WHITE


def correct_coords(row, col):
    """Функция проверяет, что координаты (row, col) лежат
    внутри доски"""
    return 0 <= row < 8 and 0 <= col < 8


def move_direction(row, col, row1, col1):
    """Функция возвращает кортеж, описывающий направление движения
    из клетки (row, col) в клетку (row1, col1) по горизонтали и по вертикали.
    '+' - движение вверх/вправо. '-' - движение вниз/влево. '0' - движения не было."""
    # Движение по вертикали
    if row - row1 > 0:
        i = '-'
    elif row - row1 < 0:
        i = '+'
    else:
        i = '0'

    # Движение по горизонтали
    if col - col1 > 0:
        j = '-'
    elif col - col1 < 0:
        j = '+'
    else:
        j = '0'

    return i, j


class Board:
    def __init__(self):
        self.color = WHITE
        self.field = []

        for row in range(8):
            self.field.append([None] * 8)

        figures = [Rook, Knight, Bishop, Queen, King, Bishop, Knight, Rook]  # Порядок фигур

        for j in range(8):
            self.field[7][j] = figures[j](BLACK)  # Расставляем фигуры
            self.field[0][j] = figures[j](WHITE)
            self.field[6][j] = Pawn(BLACK)  # Расставляем пешки
            self.field[1][j] = Pawn(WHITE)

        self.is_check = False  # Атрибут для отслеживания шаха

        # Координаты королей
        self.black_king_coords = 7, 4
        self.white_king_coords = 0, 4

        # Атрибут для отслеживания возможности взятия на проходе
        self.long_pawn_move = False

        # Атрибут содержит координаты клетки через которую возможно взятие на проходе
        # Если взятие на подходе невозможно, атрибут равен None
        self.en_passant = None

        # Если король находится под атакой,
        # список содержит кортежи, каждый из которых описывает напрвление от атакующей фигуры до короля
        self.attack_direction = []

        self.double_attack = False  # Если королю ургожают две фигуры противника, атрибут равет True

    def current_player_color(self):
        return self.color

    def opponent_color(self):
        return opponent(self.color)

    def end_turn(self):
        """Метод конца хода."""
        if self.long_pawn_move:
            self.long_pawn_move = False
        else:
            # Если пешка не двигалась на 2 клетки, перестаем отслеживать взятие на подходе
            self.en_passant = None

        # Перестаём отслеживать шах
        self.is_check = False
        self.attack_direction = []
        self.double_attack = False

        # Передаем ход другому игроку
        self.color = opponent(self.color)

    def try_move(self, row, col, row1, col1):
        """Метод проверяет, можно ли переместить фигуру из клетки (row, col) в клетку (row1, col1).
        Если перемещение возможно, вернёт True.
        Если нет --- вернёт строку, содержащую причину, по которой переместить фигуру нельзя"""

        if row == row1 and col == col1:
            return False

        piece = self.field[row][col]

        if piece is None:
            return False
        if piece.get_color() != self.color:
            return False

        if isinstance(piece, Pawn) and (row1, col1) == self.en_passant:
            return piece.can_attack(self, row, col, row1, col1)

        if isinstance(piece, King):
            if row1 == (self.color - 1) * 7:
                if col1 == 2 and self.try_castling0():
                    return True
                if col1 == 6 and self.try_castling7():
                    return True

            other_king_row, other_king_col = self.get_opponent_king_coords()

            if abs(row1 - other_king_row) == 1 and \
                    abs(col1 - other_king_col) == 1:
                return False
            elif self.under_attack(row1, col1, self.opponent_color(), False):
                return False

            # Если король пойдёт вдоль линии атаки, он не сможет убраться из под шаха
            elif move_direction(row, col, row1, col1) in self.attack_direction:
                return False

            # Нельзя атаковать фигуру своего цвета
            elif not piece.can_move(self, row, col, row1, col1) \
                    or self.field[row1][col1] and self.field[row1][col1].get_color() == self.current_player_color():
                return False

        elif self.field[row1][col1] is None and not piece.can_move(self, row, col, row1, col1):
            return False

        # Нельзя атаковать фигуру своего цвета
        elif self.field[row1][col1] and (self.field[row1][col1].get_color() == piece.get_color() or
                                         not piece.can_attack(self, row, col, row1, col1)):
            return False

        # Защитится от шаха можно поставив фигуру в клетку, через которую король может быть атакован
        # Если королю угрожают сразу две фигуры, защититься от шаха таким образом не получиться
        elif self.is_check and not self.king_can_be_attacked(row1, col1) or self.double_attack:
            return False

        # Если фигура закрывает короля от атаки вражеской фигуры,
        # она может передвигаться только вдоль линии атаки этой фигуры.
        # В другом случае, передвинувшись она подставит короля под шах.
        # Конь не может ходить вдоль одной линии,
        # поэтому вообще не может сдвинуться когда защищает короля
        elif self.king_can_be_attacked(row, col) and \
                (move_direction(row, col, row1, col1) != move_direction(*self.get_current_king_coords(), row, col)
                 and move_direction(row, col, row1, col1) != move_direction(row, col, *self.get_current_king_coords())
                 or isinstance(piece, Knight)):
            return False

        return True

    def move_options(self, row, col):
        """Метод возвращает список клеток,
        в которые может пойти фигура, стоящая в клетке (row, col)."""
        cells = []

        for i in range(8):
            for j in range(8):
                if self.try_move(row, col, i, j):
                    cells.append((i, j))

        return cells

    def move_piece(self, row, col, row1, col1):
        """Переместить фигуру из клетки (row, col) в клетку (row1, col1)."""
        piece = self.field[row][col]

        # Взятие на проходе
        if isinstance(piece, Pawn):
            if (row1, col1) == self.en_passant:
                self.field[row][col1] = None
            elif abs(row - row1) == 2:
                direction = 1 if row1 > row else -1
                self.en_passant = (row + direction, col)
                self.long_pawn_move = True

        # Отмечаем, что король или ладья передвинулась, для отслеживания рокировки
        if isinstance(piece, Rook) or isinstance(piece, King):
            piece.already_moved()

        # Меняем атрибут для отслеживания координат короля
        if isinstance(piece, King):
            if piece.get_color() == WHITE:
                self.white_king_coords = row1, col1
            else:
                self.black_king_coords = row1, col1

            # Рокировка
            if col1 - col == -2:
                return self.castling0()
            if col1 - col == 2:
                return self.castling7()

        self.field[row][col] = None  # Снять фигуру
        self.field[row1][col1] = piece  # Поставить на новое место.
        self.end_turn()

    def try_promote_pawn(self, row, col, row1, col1):
        """Метод проверяет, является ли ход из клетки (row, col)
        в клетку (row1, col1) превращением пешки."""
        if not isinstance(self.field[row][col], Pawn):
            return False

        # Проверяем, двигается ли пешка на последний ряд
        if self.current_player_color() == WHITE and row1 == 7 or self.current_player_color() == BLACK and row1 == 0:

            # Пешка либо движется по прямой, либо атакует по диагонали
            can_make_turn = self.field[row][col].can_move(self, row, col, row1, col1) and \
                            self.field[row1][col1] is None or \
                            self.field[row][col].can_attack(self, row, col, row1, col1) and \
                            self.field[row1][col1] and self.field[row1][col1].get_color() == self.opponent_color()
            if can_make_turn:
                return True
        return False

    def move_and_promote_pawn(self, row, col, row1, col1, figure):
        """Метод перемещает фигуру из клетки (row, col) в клетку (row1, col1),
        после этого превращает её в фигуру figure."""

        # Создаём фигуру того же цвета, что и пешка
        self.field[row1][col1] = figure(self.field[row][col].get_color())
        self.field[row][col] = None  # Убираем исходную фигуру

        self.end_turn()

    def try_castling0(self):
        """Метод проверяет, может ли текущий игрок совершить длинную рокировку."""

        if self.color == WHITE:
            row = 0
        else:
            row = 7

        if self.field[row][1:4] != [None, None, None]:  # Между ладьёй и королём не должны стоять другие фигуры
            return False

        if not (isinstance(self.field[row][0], Rook) and  # Проверяем, что король и ладья стоят на своих местах
                isinstance(self.field[row][4], King)):
            return False

        if self.field[row][0].move_status() or \
                self.field[row][4].move_status():  # Король и ладья не должны двигаться до рокировки
            return False

        # Король и поле в которое он передвинется не должны находится под атакой
        if self.under_attack(row, 4, self.opponent_color(), False) or \
                self.under_attack(row, 2, self.opponent_color(), False):
            return False

        return True

    def castling0(self):
        """Длинная рокировка."""
        if self.color == WHITE:
            row = 0
        else:
            row = 7

        # Отмечаем, что король иладья уже совершили рокировку
        self.field[row][4].already_moved()
        self.field[row][0].already_moved()

        # Двигаем фигуры
        self.field[row][2] = self.field[row][4]
        self.field[row][3] = self.field[row][0]

        self.field[row][4] = None
        self.field[row][0] = None

        # Меняем атрибут для отслеживания короля
        if self.current_player_color() == WHITE:
            self.white_king_coords = row, 2
        else:
            self.black_king_coords = row, 2

        self.end_turn()

    def try_castling7(self):
        """Метод проверяет, может ли текущий игрок совершить короткую рокировку."""
        if self.color == WHITE:
            row = 0
        else:
            row = 7

        if self.field[row][5:7] != [None, None]:
            return False
        if not (isinstance(self.field[row][7], Rook) and
                isinstance(self.field[row][4], King)):
            return False
        if self.field[row][7].move_status() or \
                self.field[row][4].move_status():
            return False
        if self.under_attack(row, 4, self.opponent_color(), False) or \
                self.under_attack(row, 6, self.opponent_color(), False):
            return False

        return True

    def castling7(self):
        """Короткая рокировка."""
        if self.color == WHITE:
            row = 0
        else:
            row = 7

        self.field[row][4].already_moved()
        self.field[row][7].already_moved()
        self.field[row][6] = self.field[row][4]
        self.field[row][5] = self.field[row][7]
        self.field[row][4] = None
        self.field[row][7] = None
        if self.current_player_color() == WHITE:
            self.white_king_coords = row, 6
        else:
            self.black_king_coords = row, 6
        self.end_turn()

    def under_attack(self, row, col, color, ignore_figure):
        """Метод проверяет находится ли клетка (row, col) под атакой фигуры цвета color.
        Если ignore_figure содержит кортеж из инексов шахматной клетки, фигура,
        стоящая в этой клетке игнорируется."""
        for i in range(8):
            for j in range(8):
                if (i, j) == ignore_figure:
                    continue
                if self.field[i][j]:
                    piece = self.field[i][j]
                    if (i != row or j != col) and piece.get_color() == color and \
                            piece.can_attack(self, i, j, row, col):
                        return True
        return False

    def can_be_occupied(self, row, col, color, ignore_figure):
        """Метод проверяет может ли клетка (row, col) быть знаята фигурой цвета color.
        Если ignore_figure содержит кортеж из инексов шахматной клетки, фигура,
        стоящая в этой клетке игнорируется."""
        for i in range(8):
            for j in range(8):
                if (i, j) == ignore_figure:
                    continue
                if self.field[i][j]:
                    piece = self.field[i][j]
                    if (i != row or j != col) and piece.get_color() == color and \
                            piece.can_move(self, i, j, row, col):
                        return True
        return False

    def get_current_king_coords(self):
        """Возвращает кортеж с координатами короля текущего игрока."""
        if self.current_player_color() == WHITE:
            return self.white_king_coords[0], self.white_king_coords[1]
        else:
            return self.black_king_coords[0], self.black_king_coords[1]

    def get_opponent_king_coords(self):
        """Возвращает кортеж с координатами короля противника текущего игрока."""
        if opponent(self.current_player_color()) == WHITE:
            return self.white_king_coords[0], self.white_king_coords[1]
        else:
            return self.black_king_coords[0], self.black_king_coords[1]

    def king_escapes_attack(self):
        """Метод проверяет, может ли король текущего игрока уйти
        из под боя фигуры противника."""
        row_king, col_king = self.get_current_king_coords()

        # Перебераем соседние клетки.
        # Король может передвинуться в клетку если она не находится под атакой противника,
        # не занята фигурой того же цвета что и король и не находится на линнии атаки фигуры противника.
        free_squares = (any((not (self.under_attack(row_king + i, col_king + j, self.opponent_color(), False) or
                                  (self.field[row_king + i][col_king + j] is not None and
                                   self.field[row_king + i][col_king + j].get_color() == self.current_player_color()) or
                                  move_direction(row_king, col_king, row_king + i,
                                                 col_king - j) in self.attack_direction))
                            for j in range(-1, 2)
                            if (i != 0 or j != 0) and correct_coords(row_king + i, col_king + j))
                        for i in range(-1, 2))
        if any(free_squares):
            return True
        else:
            return False

    def check_and_mate(self, row, col):
        """Метод проверяет может ли фигура в клетке (row, col) поставить шах или мат
        королю текущего игрока и возвращает CHECK или MATE соответственно.
        Если шах или мат поставить невозможно, возвращает None."""
        row_king, col_king = self.get_current_king_coords()

        # Если фигура противника может атаковать короля, она ставит ему шах
        if self.field[row][col].can_attack(self, row, col, row_king, col_king):
            self.is_check = True

            step_i = 0
            step_j = 0

            if row > row_king:
                step_i = -1
            elif row < row_king:
                step_i = 1

            if col > col_king:
                step_j = -1
            elif col < col_king:
                step_j = 1

            # Формируем список клеток, через которые фигура противника ставит королю шах
            if row == row_king:
                way_to_king = [(row, j) for j in range(col + step_j, col_king, step_j)]
            elif col == col_king:
                way_to_king = [(i, col) for i in range(row + step_i, row_king, step_i)]
            else:
                way_to_king = [i for i in zip(range(row + step_i, row_king, step_i),
                                              range(col + step_j, col_king, step_j))]

            # Если шах ставит не конь, запоминаем направление атаки
            if not isinstance(self.field[row][col], Knight):
                self.attack_direction.append(move_direction(row, col, row_king, col_king))

            # Король находится под атакой ещё одной фигуры
            if self.under_attack(row_king, col_king, self.opponent_color(), (row, col)):
                self.double_attack = True

            # Защитить короля от шаха можно атаковав фигуру, которая поставила королю шах, или закрыв ей путь к королю
            # Если короля атакуют сразу две фигуры противника, защитить короля не возможно
            defend_king = not self.double_attack and \
                          (self.under_attack(row, col, self.current_player_color(), self.get_current_king_coords()) or
                           any(self.can_be_occupied(*i, self.current_player_color(), self.get_current_king_coords())
                               for i in way_to_king))

            # Если игрок может передвинуть короля или защитить короля, ему поставили шах, иначе - мат
            if self.king_escapes_attack() or defend_king:
                return CHECK
            else:
                return MATE
        else:
            return None

    def king_can_be_attacked(self, row, col):
        """Если король текущего игрока быть атакован через клетку (row, col),
        метод возвращает координаты фигуры, которая может это сделать.
        Иначе, метод возвращает False."""
        row_king, col_king = self.get_current_king_coords()

        # Непосредственно в клетке стоит фигура, угрожающая королю
        if self.field[row][col] and self.field[row][col].get_color() == self.opponent_color() and \
                self.field[row][col].can_attack(self, row, col, row_king, col_king):
            return row, col

        # Через клетку нельзя атаковать короля
        if not Queen(None).can_move(self, row, col, row_king, col_king):
            return False

        # Через клетку можно атаковать короля по диагонали
        if abs(col - col_king) == abs(row - row_king):
            step_row = -1 if row < row_king else 1
            step_col = -1 if col < col_king else 1

            # Идём по диагонали в противоположную от короля сторону, пока не встертим другую фигуру
            while 0 < row < 7 and 0 < col < 7:
                row += step_row
                col += step_col
                if self.field[row][col]:
                    # Встреченная фигура принадлежит противнику и она может атаковать по диагонали
                    if self.field[row][col].attack_diag_line() and self.field[row][col].get_color() == \
                            self.opponent_color():
                        return row, col
                    else:
                        return False

        # Через клетку можно атаковать короля по горизонтали
        elif row == row_king:
            start = col + 1 if col > col_king else col - 1
            end = 8 if col > col_king else -1
            step = 1 if col > col_king else -1

            for j in range(start, end, step):
                if self.field[row][j]:
                    if self.field[row][j].attack_straight_line() and self.field[row][j].get_color() == \
                            self.opponent_color():
                        return row, j
                    else:
                        return False

        # Через клетку можно атаковать короля по вертикали
        else:
            start = row + 1 if row > row_king else row - 1
            end = 8 if row > row_king else -1
            step = 1 if row > row_king else -1

            for i in range(start, end, step):
                if self.field[i][col]:
                    if self.field[i][col].attack_straight_line() and self.field[i][col].get_color() == \
                            self.opponent_color():
                        return i, col
                    else:
                        return False

        return False


class Figure:
    def __init__(self, color):
        self.color = color

    def can_move(self, board, row, col, row1, col1):
        """Метод проверяет, может ли фигура переместиться из клетки (row, col) в клетку (row1, col1)
         с учетом фигур между этими клетками."""
        return False

    def can_attack(self, board, row, col, row1, col1):
        """Метод аналогичен 'can_move' для всех фигур, за исключением пешки."""
        return False

    def get_color(self):
        return self.color

    def straight_move(self, board, row, col, row1, col1):
        """Метод проверяет, можно ли движением по вертикали или горизонтали
        добраться из клетки (row, col) в клетку (row1, col1)."""
        step = 1 if (row1 >= row) else -1
        for i in range(row + step, row1, step):
            # Если на пути по горизонтали есть фигура
            if board.field[i][col]:
                return False

        step = 1 if (col1 >= col) else -1
        for j in range(col + step, col1, step):
            # Если на пути по вертикали есть фигура
            if board.field[row][j]:
                return False
        return True

    def diag_move(self, board, row, col, row1, col1):
        """Метод проверяет, можно ли движением по диагонали
        добраться из клетки (row, col) в клетку (row1, col1)."""
        if abs(col - col1) == abs(row - row1):
            if col1 > col:
                step = 1 if row1 > row else -1
                start_row = row
            else:
                step = 1 if row1 < row else -1
                start_row = row1

            param = 0
            for i in range(min(col, col1) + 1, max(col, col1)):
                param += step
                if board.field[start_row + param][i] is not None:
                    return False
        return True

    def attack_straight_line(self):
        """Метод возвращает True если фигура может двигаться на любое кол-во клеток
         по горизонтали или вертикали."""
        return False

    def attack_diag_line(self):
        """Метод возвращает True если фигура может двигаться на любое кол-во клеток
        по диагонали."""
        return False


class Rook(Figure):
    def __init__(self, color):
        super().__init__(color)
        self.moved = False  # Атрибут для отслеживания возможности рокировки

    def can_move(self, board, row, col, row1, col1):
        # Невозможно сделать ход в клетку, которая не лежит в том же ряду
        # или столбце клеток.
        if row != row1 and col != col1:
            return False
        return self.straight_move(board, row, col, row1, col1)

    def can_attack(self, board, row, col, row1, col1):
        return self.can_move(board, row, col, row1, col1)

    def already_moved(self):
        self.moved = True

    def attack_straight_line(self):
        return True

    def move_status(self):
        return self.moved


class Pawn(Figure):
    def can_move(self, board, row, col, row1, col1):
        if col != col1:
            return False

        # Пешка может сделать из начального положения ход на 2 клетки
        # вперёд, поэтому поместим индекс начального ряда в start_row.
        if self.color == WHITE:
            direction = 1
            start_row = 1
        else:
            direction = -1
            start_row = 6

        # ход на 1 клетку
        if row + direction == row1:
            return True

        # ход на 2 клетки из начального положения
        if (row == start_row
                and row + 2 * direction == row1
                and board.field[row + direction][col] is None):
            return True

        return False

    def can_attack(self, board, row, col, row1, col1):
        direction = 1 if (self.color == WHITE) else -1
        return (row + direction == row1
                and (col + 1 == col1 or col - 1 == col1))


class Knight(Figure):
    def can_move(self, board, row, col, row1, col1):
        return {2, 1} == {abs(row - row1), abs(col - col1)}

    def can_attack(self, board, row, col, row1, col1):
        return self.can_move(board, row, col, row1, col1)


class King(Figure):
    def __init__(self, color):
        super().__init__(color)
        self.moved = False  # Атрибут для отслеживания возможности рокировки

    def can_move(self, board, row, col, row1, col1):
        return {0, 1} == {abs(row - row1), abs(col - col1)} \
               or {1, 1} == {abs(row - row1), abs(col - col1)}

    def can_attack(self, board, row, col, row1, col1):
        return self.can_move(board, row, col, row1, col1)

    def already_moved(self):
        self.moved = True

    def move_status(self):
        return self.moved


class Queen(Figure):
    def can_move(self, board, row, col, row1, col1):
        if abs(col - col1) == abs(row - row1):
            return self.diag_move(board, row, col, row1, col1)
        elif row == row1 or col == col1:
            return self.straight_move(board, row, col, row1, col1)
        return False

    def can_attack(self, board, row, col, row1, col1):
        return self.can_move(board, row, col, row1, col1)

    def attack_straight_line(self):
        return True

    def attack_diag_line(self):
        return True


class Bishop(Figure):
    def can_move(self, board, row, col, row1, col1):
        if abs(col - col1) == abs(row - row1):
            return self.diag_move(board, row, col, row1, col1)
        return False

    def can_attack(self, board, row, col, row1, col1):
        return self.can_move(board, row, col, row1, col1)

    def attack_diag_line(self):
        return True


# Константы цветов
WHITE = 1
BLACK = 2

# Константы шаха и мата
CHECK = 0
MATE = 1