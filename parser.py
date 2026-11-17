from pathlib import Path
import re

import ply.yacc as yacc
from ply.lex import LexToken

from lexer import integer_fa, real_fa, string_fa


# project folder
BASE_DIR = Path(__file__).resolve().parent


# token types used by the parser
tokens = (
    "INT", "REAL", "GRADELIST",
    "INPUT", "OUTPUT",
    "IF", "THEN", "ELSE", "END",
    "FOR", "IN", "DO",
    "AND", "OR",

    "IDENTIFIER", "INTEGER", "REAL_NUMBER", "STRING",

    "ASSIGN",
    "PLUS", "MINUS", "MULTIPLY", "DIVIDE", "MODULO",

    "EQ", "NE", "GT", "LT", "GE", "LE",

    "LPAREN", "RPAREN",
    "LBRACKET", "RBRACKET", "COMMA"
)


# map operators and separators to ply token types
TOKEN_MAP = {
    ":=": "ASSIGN",
    "+": "PLUS",
    "-": "MINUS",
    "*": "MULTIPLY",
    "/": "DIVIDE",
    "%": "MODULO",

    "==": "EQ",
    "!=": "NE",
    ">": "GT",
    "<": "LT",
    ">=": "GE",
    "<=": "LE",

    "(": "LPAREN",
    ")": "RPAREN",
    "[": "LBRACKET",
    "]": "RBRACKET",
    ",": "COMMA"
}


# load symbol values by their table positions
def read_symbol_table():
    st = {}

    # read each symbol and its stored position
    with open(BASE_DIR / "ST.txt", "r", encoding="utf-8") as file:
        for line in file:
            line = line.rstrip("\n")

            if not line.strip():
                continue

            # split the value and position at the last arrow
            value, position = line.rsplit(" -> ", 1)

            # check that the position has the form (bucket, index)
            match = re.fullmatch(r"\((\d+),\s*(\d+)\)", position)

            # report an invalid position
            if not match:
                raise ValueError(f"Invalid ST entry: {line}")

            # convert the two captured numbers from text to integers
            bucket = int(match.group(1))
            index = int(match.group(2))

            # store the value using its position as the dictionary key
            st[(bucket, index)] = value

    # return the symbol table for lookups by position
    return st


# convert pif entries into tokens the parser can read
def read_pif():
    st = read_symbol_table()
    result = []

    # read tokens in their original order
    with open(BASE_DIR / "PIF.txt", "r", encoding="utf-8") as file:
        for line_number, line in enumerate(file, start=1):
            line = line.strip()

            if not line:
                continue

            token_name, position = line.rsplit(" -> ", 1)

            match = re.fullmatch(r"\((-?\d+),\s*(-?\d+)\)", position)

            if not match:
                raise ValueError(f"Invalid PIF entry: {line}")

            bucket = int(match.group(1))
            index = int(match.group(2))
            symbol_position = (bucket, index)

            # create the token object expected by ply
            token = LexToken()

            # look up the original identifier name
            if token_name == "IDENTIFIER":
                if symbol_position not in st:
                    raise ValueError(f"Missing identifier in ST: {symbol_position}")

                token.type = "IDENTIFIER"
                token.value = st[symbol_position]

            # recover the constant and determine its type
            elif token_name == "CONSTANT":
                if symbol_position not in st:
                    raise ValueError(f"Missing constant in ST: {symbol_position}")

                value = st[symbol_position]
                token.value = value

                if string_fa.accepts(value):
                    token.type = "STRING"
                elif integer_fa.accepts(value):
                    token.type = "INTEGER"
                elif real_fa.accepts(value):
                    token.type = "REAL_NUMBER"
                else:
                    raise ValueError(f"Invalid constant in ST: {value}")

            # map operators and separators to ply token types
            # operators: :=, +, -, *, /, %, ==, !=, >, <, >=, <=
            # separators: (, ), [, ], ,
            elif token_name in TOKEN_MAP:
                if symbol_position != (-1, -1):
                    raise ValueError(f"Invalid position for {token_name}")

                token.type = TOKEN_MAP[token_name]
                token.value = token_name

            # keep keyword names as token types
            # keywords: INT, REAL, GRADELIST, INPUT, OUTPUT, IF, THEN, ELSE, END, FOR, IN, DO, AND, OR
            elif token_name in tokens and token_name not in (
                "IDENTIFIER", "INTEGER", "REAL_NUMBER", "STRING"
            ):
                if symbol_position != (-1, -1):
                    raise ValueError(f"Invalid position for {token_name}")

                token.type = token_name
                token.value = token_name

            else:
                raise ValueError(f"Unknown PIF token: {token_name}")

            # use the pif entry number for error messages
            token.lineno = line_number
            token.lexpos = line_number - 1

            result.append(token)

    return result


# give ply the tokens from read_pif() one at a time
class TokenStream:
    def __init__(self, token_list):
        self.tokens = token_list

        # start at the first token in the list
        self.position = 0

    def token(self):
        # tell ply when there are no more tokens
        if self.position >= len(self.tokens):
            return None

        # take the current token and advance to the next one
        token = self.tokens[self.position]
        self.position += 1
        return token


# store productions and syntax errors
productions = []
syntax_errors = []


# record each rule applied by the parser
def record(production):
    productions.append(production)


# starting rule
start = "program"


# program ::= statement_list
def p_program(p):
    "program : statement_list"
    record("program -> statement_list")
    p[0] = True


# statement_list ::= statement statement_list | epsilon
def p_statement_list(p):
    """statement_list : statement statement_list
                      | empty"""
    if len(p) == 3:
        record("statement_list -> statement statement_list")
    else:
        record("statement_list -> epsilon")


# statement types
def p_statement(p):
    """statement : declaration_stmt
                 | assignment_stmt
                 | input_stmt
                 | output_stmt
                 | if_stmt
                 | for_stmt"""
    record("statement -> " + p.slice[1].type)


# declarations
def p_declaration_stmt(p):
    """declaration_stmt : simple_declaration
                        | gradelist_declaration"""
    record("declaration_stmt -> " + p.slice[1].type)


# accept an integer or real variable declaration
def p_simple_declaration(p):
    """simple_declaration : INT IDENTIFIER
                          | REAL IDENTIFIER"""
    record("simple_declaration -> " + p.slice[1].type + " IDENTIFIER")


# accept a grade list declaration with square brackets
def p_gradelist_declaration(p):
    "gradelist_declaration : GRADELIST IDENTIFIER ASSIGN LBRACKET number_list RBRACKET"
    record("gradelist_declaration -> GRADELIST IDENTIFIER ASSIGN LBRACKET number_list RBRACKET")


# allow a list of numbers or an empty list
def p_number_list(p):
    """number_list : number number_tail_list
                   | empty"""
    if len(p) == 3:
        record("number_list -> number number_tail_list")
    else:
        record("number_list -> epsilon")


# accept more numbers separated by commas
def p_number_tail_list(p):
    """number_tail_list : COMMA number number_tail_list
                        | empty"""
    if len(p) == 4:
        record("number_tail_list -> COMMA number number_tail_list")
    else:
        record("number_tail_list -> epsilon")


# assignment
def p_assignment_stmt(p):
    "assignment_stmt : IDENTIFIER ASSIGN expression"
    record("assignment_stmt -> IDENTIFIER ASSIGN expression")


# input
def p_input_stmt(p):
    "input_stmt : INPUT IDENTIFIER"
    record("input_stmt -> INPUT IDENTIFIER")


# output
def p_output_stmt(p):
    "output_stmt : OUTPUT output_value"
    record("output_stmt -> OUTPUT output_value")


# allow an expression or a string after output
def p_output_value(p):
    """output_value : expression
                    | STRING"""
    record("output_value -> " + p.slice[1].type)


# if statement
def p_if_stmt(p):
    "if_stmt : IF condition THEN statement_list else_part END"
    record("if_stmt -> IF condition THEN statement_list else_part END")


# allow an optional else block
def p_else_part(p):
    """else_part : ELSE statement_list
                 | empty"""
    if len(p) == 3:
        record("else_part -> ELSE statement_list")
    else:
        record("else_part -> epsilon")


# conditions
def p_condition(p):
    "condition : comparison condition_rest"
    record("condition -> comparison condition_rest")


# allow more comparisons joined by logical operators
def p_condition_rest(p):
    """condition_rest : logical_op comparison condition_rest
                      | empty"""
    if len(p) == 4:
        record("condition_rest -> logical_op comparison condition_rest")
    else:
        record("condition_rest -> epsilon")


# compare two expressions
def p_comparison(p):
    "comparison : expression comparison_op expression"
    record("comparison -> expression comparison_op expression")


# list the allowed comparison operators
def p_comparison_op(p):
    """comparison_op : EQ
                     | NE
                     | GT
                     | LT
                     | GE
                     | LE"""
    record("comparison_op -> " + p.slice[1].type)


# list the operators that connect comparisons
def p_logical_op(p):
    """logical_op : AND
                  | OR"""
    record("logical_op -> " + p.slice[1].type)


# for statement
def p_for_stmt(p):
    "for_stmt : FOR IDENTIFIER IN IDENTIFIER DO statement_list END"
    record("for_stmt -> FOR IDENTIFIER IN IDENTIFIER DO statement_list END")


# arithmetic expressions
def p_expression(p):
    "expression : term expression_rest"
    record("expression -> term expression_rest")


# allow more terms joined by addition or subtraction
def p_expression_rest(p):
    """expression_rest : add_op term expression_rest
                       | empty"""
    if len(p) == 4:
        record("expression_rest -> add_op term expression_rest")
    else:
        record("expression_rest -> epsilon")


# list the operators between terms
def p_add_op(p):
    """add_op : PLUS
              | MINUS"""
    record("add_op -> " + p.slice[1].type)


# group multiplication, division and modulo before addition
def p_term(p):
    "term : factor term_rest"
    record("term -> factor term_rest")


# allow more factors joined by multiplicative operators
def p_term_rest(p):
    """term_rest : mult_op factor term_rest
                 | empty"""
    if len(p) == 4:
        record("term_rest -> mult_op factor term_rest")
    else:
        record("term_rest -> epsilon")


# list the operators between factors
def p_mult_op(p):
    """mult_op : MULTIPLY
               | DIVIDE
               | MODULO"""
    record("mult_op -> " + p.slice[1].type)


# accept a variable, number or parenthesized expression
def p_factor(p):
    """factor : IDENTIFIER
              | number
              | LPAREN expression RPAREN"""
    if len(p) == 2:
        record("factor -> " + p.slice[1].type)
    else:
        record("factor -> LPAREN expression RPAREN")


# numeric constants
def p_number(p):
    """number : INTEGER
              | REAL_NUMBER"""
    record("number -> " + p.slice[1].type)


# empty production
def p_empty(p):
    "empty :"
    record("empty -> epsilon")


# syntax errors
def p_error(p):
    if p:
        message = f"Syntax error near '{p.value}' ({p.type}) at PIF line {p.lineno}"
    else:
        message = "Syntax error at end of file"

    syntax_errors.append(message)


# build the yacc parser
parser = yacc.yacc(
    start=start,
    write_tables=False,
    debug=False
)


# perform syntactical analysis using pif
def parse_program():
    # reset the results before each parse
    productions.clear()
    syntax_errors.clear()

    # read tokens from pif and st
    ply_tokens = read_pif()

    # create the token stream
    token_stream = TokenStream(ply_tokens)

    # syntactical analysis using yacc
    result = parser.parse(lexer=token_stream, tracking=False)

    # report failure if parsing did not accept the program
    if syntax_errors or result is not True:
        if not syntax_errors:
            syntax_errors.append("Syntax analysis failed")

        return False, syntax_errors.copy(), []

    return True, [], productions.copy()


# run parser
if __name__ == "__main__":
    try:
        valid, errors, used_productions = parse_program()

    # report unreadable files or malformed input entries
    except (OSError, ValueError) as error:
        valid = False
        errors = [str(error)]
        used_productions = []

    # display and save the applied rules after a successful parse
    if valid:
        print("Syntactically correct program.")

        print("\nPRODUCTIONS:")
        for index, production in enumerate(used_productions, start=1):
            print(f"{index}. {production}")

        # save productions to file
        with open(BASE_DIR / "productions.txt", "w", encoding="utf-8") as file:
            for index, production in enumerate(used_productions, start=1):
                file.write(f"{index}. {production}\n")

        print("\nProductions saved to productions.txt")

    else:
        print("Invalid program.")

        for error in errors:
            print(error)

        # avoid keeping productions from a previous successful run
        (BASE_DIR / "productions.txt").write_text("", encoding="utf-8")

