import tkinter as tk
from tkinter import messagebox

class SudokuSolver:
    def __init__(self, board):
        self.board = board

    def is_valid(self, row: int, col: int, num: int) -> bool:
        for i in range(9):
            if self.board[row][i] == num or self.board[i][col] == num:
                return False

        start_row, start_col = 3 * (row // 3), 3 * (col // 3)
        for i in range(3):
            for j in range(3):
                if self.board[start_row + i][start_col + j] == num:
                    return False
        return True

    def find_empty_cell(self):
        for r in range(9):
            for c in range(9):
                if self.board[r][c] == 0:
                    return r, c
        return None

    def solve_generator(self):
        empty = self.find_empty_cell()
        if not empty:
            yield (self.board, None, True)
            return
        row, col = empty

        for num in range(1, 10):
            if self.is_valid(row, col, num):
                self.board[row][col] = num
                yield (self.board, (row, col), False)
                for result in self.solve_generator():
                    yield result
                    if result[2]:
                        return
                self.board[row][col] = 0
                yield (self.board, (row, col), False)
        yield (self.board, None, False)

class SudokuApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Sudoku Solver Animation")
        self.delay = 10  
        self.default_fg = "white"
        self.create_widgets()

    def create_widgets(self):
        self.entries = [[None for _ in range(9)] for _ in range(9)]
        self.grid_frame = tk.Frame(self.root, bg="black")
        self.grid_frame.grid(row=0, column=0, padx=10, pady=10)

        for r in range(9):
            for c in range(9):
                padx = (5, 1) if c % 3 == 0 and c != 0 else (1, 1)
                pady = (5, 1) if r % 3 == 0 and r != 0 else (1, 1)
                entry = tk.Entry(self.grid_frame, width=3, font=("Arial", 18), justify="center", bd=2)
                entry.grid(row=r, column=c, padx=padx, pady=pady, ipadx=5, ipady=5)
                self.entries[r][c] = entry

        btn_style = {"font": ("Arial", 14), "bd": 3, "relief": "raised", "bg": "white", "fg": "black"}
        tk.Button(self.root, text="Animate Solve", command=self.animate_solve_sudoku, **btn_style)\
            .grid(row=1, column=0, pady=10, sticky="ew")
        tk.Button(self.root, text="Solve (Instant)", command=self.solve_sudoku, **btn_style)\
            .grid(row=2, column=0, pady=10, sticky="ew")
        tk.Button(self.root, text="Clear", command=self.clear_board, **btn_style)\
            .grid(row=3, column=0, pady=10, sticky="ew")

    def get_board(self) -> list:
        board = []
        for r in range(9):
            row = []
            for c in range(9):
                val = self.entries[r][c].get()
                try:
                    num = int(val)
                except ValueError:
                    num = 0
                row.append(num)
            board.append(row)
        return board

    def update_board(self, board, highlight=None):
        for r in range(9):
            for c in range(9):
                entry = self.entries[r][c]
                entry.delete(0, tk.END)
                if board[r][c] != 0:
                    entry.insert(0, str(board[r][c]))
                if highlight and (r, c) == highlight:
                    entry.config(fg="red")
                else:
                    entry.config(fg=self.default_fg)
        self.root.update_idletasks()

    def animate_solve_sudoku(self):
        board = self.get_board()
        self.solver = SudokuSolver(board)
        self.solver_generator = self.solver.solve_generator()
        self.animate_step()

    def animate_step(self):
        try:
            board, highlight, solved = next(self.solver_generator)
            self.update_board(board, highlight)
            if solved:
                self.update_board(board)
                return
            self.root.after(self.delay, self.animate_step)
        except StopIteration:
            if all(all(cell != 0 for cell in row) for row in self.solver.board):
                self.update_board(self.solver.board)
            else:
                messagebox.showerror("Error", "No solution exists!")

    def solve_sudoku(self):
        board = self.get_board()
        solver = SudokuSolver(board)
        if self.backtrack_solve(solver):
            self.update_board(solver.board)
        else:
            messagebox.showerror("Error", "No solution exists!")

    def backtrack_solve(self, solver: SudokuSolver) -> bool:
        empty = solver.find_empty_cell()
        if not empty:
            return True
        row, col = empty
        for num in range(1, 10):
            if solver.is_valid(row, col, num):
                solver.board[row][col] = num
                if self.backtrack_solve(solver):
                    return True
                solver.board[row][col] = 0
        return False

    def clear_board(self):
        for r in range(9):
            for c in range(9):
                self.entries[r][c].delete(0, tk.END)
                self.entries[r][c].config(fg=self.default_fg)

def main():
    root = tk.Tk()
    app = SudokuApp(root)
    root.mainloop()

if __name__ == '__main__':
    main()
