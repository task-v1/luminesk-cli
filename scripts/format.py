import ast
import subprocess
import sys
from pathlib import Path


class BlankLineChecker(ast.NodeVisitor):
    def __init__(self, filename: str, content: str):
        self.filename = filename
        self.lines = content.splitlines()
        self.lines_to_fix: set[int] = set()
        self.errors: list[str] = []

    def check_block(self, body):
        for idx, stmt in enumerate(body):
            if isinstance(stmt, (ast.If, ast.For, ast.While, ast.Try, ast.With)):
                if idx > 0:
                    prev = body[idx - 1]
                    prev_end = getattr(prev, "end_lineno", prev.lineno)
                    curr_start = stmt.lineno

                    has_blank_line = False

                    for line_idx in range(prev_end, curr_start - 1):
                        if not self.lines[line_idx].strip():
                            has_blank_line = True
                            break

                    if not has_blank_line:
                        insert_idx = curr_start - 1
                        self.lines_to_fix.add(insert_idx)
                        statement_type = stmt.__class__.__name__.lower()
                        self.errors.append(
                            f"{self.filename}:{curr_start}: Перед оператором '{statement_type}' должна быть пустая строка."
                        )

                if idx < len(body) - 1:
                    next_stmt = body[idx + 1]
                    curr_end = getattr(stmt, "end_lineno", stmt.lineno)
                    next_start = next_stmt.lineno

                    has_blank_line = False

                    for line_idx in range(curr_end, next_start - 1):
                        if not self.lines[line_idx].strip():
                            has_blank_line = True
                            break

                    if not has_blank_line:
                        insert_idx = next_start - 1
                        self.lines_to_fix.add(insert_idx)
                        statement_type = stmt.__class__.__name__.lower()
                        self.errors.append(
                            f"{self.filename}:{curr_end + 1}: После оператора '{statement_type}' должна быть пустая строка."
                        )

        for node in body:
            self.generic_visit(node)

    def visit_FunctionDef(self, node):
        self.check_block(node.body)

    def visit_AsyncFunctionDef(self, node):
        self.check_block(node.body)

    def visit_If(self, node):
        self.check_block(node.body)

        if node.orelse:
            self.check_block(node.orelse)

        self.generic_visit(node)

    def visit_For(self, node):
        self.check_block(node.body)
        self.generic_visit(node)

    def visit_While(self, node):
        self.check_block(node.body)
        self.generic_visit(node)


def process_file(path: Path, autofix: bool) -> list[str]:
    try:
        content = path.read_text(encoding="utf-8")
        tree = ast.parse(content, filename=str(path))
        checker = BlankLineChecker(str(path), content)
        checker.visit(tree)

        if autofix and checker.lines_to_fix:
            lines = content.splitlines()

            for idx in sorted(checker.lines_to_fix, reverse=True):
                current_line = lines[idx] if idx < len(lines) else ""
                indent = len(current_line) - len(current_line.lstrip())
                lines.insert(idx, " " * indent)

            path.write_text("\n".join(lines) + "\n", encoding="utf-8")
            return [
                f"[FIXED] {path}: Добавлено пустых строк: {len(checker.lines_to_fix)}"
            ]

        return checker.errors
    except Exception as e:
        return [f"{path}: Ошибка обработки ({e})"]


def main():
    args = sys.argv[1:]
    autofix = "--fix" in args

    if autofix:
        args.remove("--fix")

    files = [Path(p) for p in args] if args else list(Path(".").rglob("*.py"))

    exclude_dirs = {
        ".venv",
        "venv",
        ".git",
        "__pycache__",
        ".ruff_cache",
        "build",
        "dist",
        "workspaces",
    }
    files = [f for f in files if not any(part in exclude_dirs for part in f.parts)]

    all_messages = []

    for file in files:
        if file.is_file():
            all_messages.extend(process_file(file, autofix))

    if autofix:
        subprocess.run(["ruff", "check", "--fix"])

    if all_messages:
        for msg in all_messages:
            print(msg)
        sys.exit(0 if autofix else 1)
    else:
        print("Проверка пройдена! Все пустые строки на месте.")
        sys.exit(0)


if __name__ == "__main__":
    main()
