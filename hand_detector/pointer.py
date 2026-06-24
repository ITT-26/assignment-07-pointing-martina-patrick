class Pointer:
    def __init__(self, x, y, clicked):
        self.x = x
        self.y = y
        self.clicked = clicked

    def __str__(self):
        return f'Pointer at {self.x}, {self.y} is {"clicked" if self.clicked else "not clicked"}.'

    @classmethod
    def invalid_pointer(cls):
        return cls(-99, -99, False)


