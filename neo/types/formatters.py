class Table:
    def __init__(self):
        self.columns: list[str] = []
        self.rows: list[list[str]] = []
        self.widths: list[int] = []

    def init_columns(self, columns: list[str]):
        self.columns = columns
        self.widths = [len(col) + 4 for col in columns]

    def add_row(self, row: list[str]):
        if len(row) > len(self.columns):
            raise ValueError("Row has too many columns")
        self.rows.append(row)

        for index, item in enumerate(row):
            if (len(item) + 4) > self.widths[index]:
                self.widths[index] = len(item) + 4

    def build(self):
        cols = []
        for index, col in enumerate(self.columns):
            cols.append(col.center(self.widths[index]))
        self.columns = "|" + "|".join(cols) + "|"

        separator = "+".join("-" * w for w in self.widths)
        self.border = "+" + separator + "+"

        rows = []
        for row in self.rows:
            final_row = []
            for index, item in enumerate(row):
                final_row.append(item.center(self.widths[index]))
            rows.append("|" + "|".join(final_row) + "|")
        self.rows = rows

    def display(self):
        self.build()
        rows = "\n".join(self.rows)
        return (
            f"{self.border}\n"
            f"{self.columns}\n"
            f"{self.border}\n"
            f"{rows}\n"
            f"{self.border}"
        )
