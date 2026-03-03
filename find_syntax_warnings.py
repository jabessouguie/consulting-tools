import os
import py_compile
import warnings


def check_files():
    base_dir = "."
    exclude = {".venv", "venv", "temp", "cache", "output", "__pycache__", "htmlcov"}

    for root, dirs, files in os.walk(base_dir):
        dirs[:] = [d for d in dirs if d not in exclude]
        for file in files:
            if file.endswith(".py"):
                path = os.path.join(root, file)
                try:
                    with warnings.catch_warnings(record=True) as w:
                        warnings.simplefilter("always")
                        py_compile.compile(path, doraise=True)
                        for warning in w:
                            if issubclass(warning.category, SyntaxWarning):
                                print(
                                    f"{path}:{warning.lineno}: {warning.category.__name__}: {warning.message}"
                                )
                except Exception as e:
                    # SyntaxErrors will be caught here if they are fatal,
                    # but we are looking for SyntaxWarnings specifically.
                    pass


if __name__ == "__main__":
    check_files()
