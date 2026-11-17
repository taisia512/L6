
import re
from pathlib import Path

from tokens import KEYWORDS
from symbol_table import SymbolTable
from fa_reader import read_fa


# project folder
BASE_DIR = Path(__file__).resolve().parent


# load finite automata from Lab 4
identifier_fa = read_fa(str(BASE_DIR / "input" / "identifier_fa.txt"))
integer_fa = read_fa(str(BASE_DIR / "input" / "integer_fa.txt"))
real_fa = read_fa(str(BASE_DIR / "input" / "real_fa.txt"))
string_fa = read_fa(str(BASE_DIR / "input" / "string_fa.txt"))


# recognize tokens from the source program
def tokenize(source_code):
    tokens = []
    errors = []

    # regex separates candidate tokens
    # finite automata validate identifiers and constants
    token_pattern = re.compile(
        r'(?P<STRING>"[^"\n]*(?:"|(?=\n|$)))'
        r'|(?P<WORD>[A-Za-z0-9_.]+)'
        r'|(?P<OPERATOR>:=|==|!=|>=|<=|[+\-*/%><])'
        r'|(?P<SEPARATOR>[\[\](),])'
        r'|(?P<WHITESPACE>\s+)'
        r'|(?P<INVALID>.)'
    )

    # go through each token found in the source code
    for match in token_pattern.finditer(source_code):
        # get the token category (WORD, OPERATOR, STRING, etc.)
        token_type = match.lastgroup
        # get the actual token value (grade, :=, 10, etc.)
        token_value = match.group()

        if token_type == "WHITESPACE":
            continue

        # classify words using keywords and finite automata
        if token_type == "WORD":
            if token_value in KEYWORDS:
                token_type = "KEYWORD"
            elif identifier_fa.accepts(token_value):
                token_type = "IDENTIFIER"
            elif integer_fa.accepts(token_value):
                token_type = "INTEGER"
            elif real_fa.accepts(token_value):
                token_type = "REAL"
            else:
                token_type = "INVALID_TOKEN"

        # validate strings using finite automaton
        elif token_type == "STRING":
            if not string_fa.accepts(token_value):
                token_type = "INVALID_TOKEN"

        # collect lexical errors
        if token_type in ("INVALID", "INVALID_TOKEN"):
            line = source_code.count("\n", 0, match.start()) + 1

            errors.append(
                f"Invalid token '{token_value}' at line {line}"
            )
        else:
            tokens.append((token_type, token_value))

    return tokens, errors


# read the source program and display the results
if __name__ == "__main__":
    with open(BASE_DIR / "program_valid1.txt", "r", encoding="utf-8") as file:
        source_code = file.read()

    tokens, errors = tokenize(source_code)

    print("TOKENS:")
    for token_type, token_value in tokens:
        print(f"{token_type}: {token_value}")

    print("\nLEXICAL ERRORS:")
    if errors:
        for error in errors:
            print(error)
    else:
        print("No lexical errors found.")

    # create and populate the symbol table
    st = SymbolTable()

    # go through all valid tokens
    for token_type, token_value in tokens:
        # add only identifiers and constants to the symbol table
        if token_type in ("IDENTIFIER", "INTEGER", "REAL", "STRING"):
            st.add(token_value)

    print("\nSYMBOL TABLE:")
    st.display()

    # generate the program internal form
    pif = []

    for token_type, token_value in tokens:
        if token_type in ("IDENTIFIER", "INTEGER", "REAL", "STRING"):
            position = st.search(token_value)

            if token_type == "IDENTIFIER":
                pif_token = "IDENTIFIER"
            else:
                pif_token = "CONSTANT"

            pif.append((pif_token, position))
        else:
            pif.append((token_value, (-1, -1)))

    print("\nPROGRAM INTERNAL FORM:")
    for token, position in pif:
        print(f"{token} -> {position}")

    # save the program internal form
    with open(BASE_DIR / "PIF.txt", "w", encoding="utf-8") as file:
        for token, position in pif:
            file.write(f"{token} -> {position}\n")

    # save the symbol table
    with open(BASE_DIR / "ST.txt", "w", encoding="utf-8") as file:
        for position, bucket in enumerate(st.table):
            for index, value in enumerate(bucket):
                file.write(f"{value} -> ({position}, {index})\n")

    # save lexical errors
    with open(BASE_DIR / "lexical_errors.txt", "w", encoding="utf-8") as file:
        if errors:
            for error in errors:
                file.write(error + "\n")
        else:
            file.write("No lexical errors found.\n")

    print("\nResults saved to files.")
