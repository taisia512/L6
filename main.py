import subprocess
import sys
from pathlib import Path

# locate the folder containing this script
BASE_DIR = Path(__file__).resolve().parent


def main():
    # print the heading before the lexer starts
    print("=== LEXICAL ANALYSIS ===", flush=True)

    # run the lexer with the same python interpreter and wait for it to finish
    result = subprocess.run(
        [sys.executable, str(BASE_DIR / "lexer.py")],
        cwd=BASE_DIR
    )

    # stop if the lexer exits with an error
    if result.returncode != 0:
        print("Lexical analysis failed.")
        return

    # locate the report written by the lexer
    errors_file = BASE_DIR / "lexical_errors.txt"

    # stop if the report is missing
    if not errors_file.exists():
        print("Lexical errors file was not generated.")
        return

    # read the report and trim whitespace around the message
    errors = errors_file.read_text(encoding="utf-8").strip()

    # continue only if the lexer reports no lexical errors
    if errors != "No lexical errors found.":
        print("\nParsing stopped because lexical errors were found.")
        return

    # print the heading before the parser starts
    print("\n=== SYNTACTIC ANALYSIS ===", flush=True)

    # run the parser from the project folder
    subprocess.run(
        [sys.executable, str(BASE_DIR / "parser.py")],
        cwd=BASE_DIR
    )


# call main only when this file is run directly
if __name__ == "__main__":
    main()