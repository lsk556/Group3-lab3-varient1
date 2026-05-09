from __future__ import annotations

import logging
import re
from typing import Any, Callable, Optional

# ---------- Logging ----------
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger("expr")


# ---------- AOP decorators ----------
def arg_type(
    pos: int, expected: type
) -> Callable[[Callable[..., Any]], Callable[..., Any]]:
    def decorator(func: Callable[..., Any]) -> Callable[..., Any]:
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            if (
                len(args) > pos
                and args[pos] is not None
                and not isinstance(args[pos], expected)
            ):
                raise TypeError(
                    f"{func.__name__} arg {pos} expects "
                    f"{expected.__name__}, got {type(args[pos]).__name__}"
                )
            return func(*args, **kwargs)
        return wrapper
    return decorator


# ---------- AST ----------
class Expr:
    def accept(self, visitor: Evaluator) -> Any:
        raise NotImplementedError


class Literal(Expr):
    def __init__(self, value: float) -> None:
        self.value = value

    def accept(self, visitor: Evaluator) -> Any:
        return visitor.visit_literal(self)


class Variable(Expr):
    def __init__(self, name: str) -> None:
        self.name = name

    def accept(self, visitor: Evaluator) -> Any:
        return visitor.visit_variable(self)


class Binary(Expr):
    def __init__(self, left: Expr, op: str, right: Expr) -> None:
        self.left = left
        self.op = op
        self.right = right

    def accept(self, visitor: Evaluator) -> Any:
        return visitor.visit_binary(self)


class Unary(Expr):
    def __init__(self, op: str, operand: Expr) -> None:
        self.op = op
        self.operand = operand

    def accept(self, visitor: Evaluator) -> Any:
        return visitor.visit_unary(self)


class Call(Expr):
    def __init__(self, func: Callable[..., Any], args: list[Expr]) -> None:
        self.func = func
        self.args = args

    def accept(self, visitor: Evaluator) -> Any:
        return visitor.visit_call(self)


# ---------- Tokenizer ----------
class Tokenizer:
    @arg_type(1, str)
    def __init__(self, text: str) -> None:
        self.text = text
        self.pos = 0

    def tokenize(self) -> list[tuple[str, str]]:
        tokens: list[tuple[str, str]] = []
        while self.pos < len(self.text):
            ch = self.text[self.pos]
            if ch.isspace():
                self.pos += 1
                continue
            if ch in "+-*/^()":
                tokens.append(("OP", ch))
                self.pos += 1
                continue
            if ch.isdigit() or ch == ".":
                match = re.match(r"\d+(\.\d*)?", self.text[self.pos:])
                if match:
                    val = match.group(0)
                    tokens.append(("NUM", val))
                    self.pos += len(val)
                    continue
            if ch.isalpha() or ch == "_":
                match = re.match(
                    r"[A-Za-z_][A-Za-z0-9_]*", self.text[self.pos:]
                )
                if match:
                    val = match.group(0)
                    tokens.append(("NAME", val))
                    self.pos += len(val)
                    continue
            raise SyntaxError(
                f"Unexpected character: {ch} at pos {self.pos}"
            )
        return tokens


# ---------- Parser ----------
class Parser:
    @arg_type(1, list)
    def __init__(
        self,
        tokens: list[tuple[str, str]],
        funcs: dict[str, Callable[..., Any]],
    ) -> None:
        self.tokens = tokens
        self.pos = 0
        self.funcs = funcs

    def peek(self) -> Optional[tuple[str, str]]:
        if self.pos < len(self.tokens):
            return self.tokens[self.pos]
        return None

    def consume(
        self, expected_type: Optional[str] = None
    ) -> tuple[str, str]:
        tok = self.peek()
        if tok is None:
            raise SyntaxError("Unexpected end of input")
        if expected_type and tok[0] != expected_type:
            raise SyntaxError(
                f"Expected {expected_type}, got {tok[0]}"
            )
        self.pos += 1
        return tok

    def parse(self) -> Expr:
        node = self.expr()
        if self.peek() is not None:
            raise SyntaxError(
                "Unexpected token after end of expression"
            )
        return node

    def expr(self) -> Expr:
        node = self.term()
        while True:
            tok = self.peek()
            if tok and tok[0] == "OP" and tok[1] in ("+", "-"):
                self.consume()
                right = self.term()
                node = Binary(node, tok[1], right)
            else:
                break
        return node

    def term(self) -> Expr:
        node = self.factor()
        while True:
            tok = self.peek()
            if tok and tok[0] == "OP" and tok[1] in ("*", "/"):
                self.consume()
                right = self.factor()
                node = Binary(node, tok[1], right)
            else:
                break
        return node

    def factor(self) -> Expr:
        node = self.unary()
        tok = self.peek()
        if tok and tok[0] == "OP" and tok[1] == "^":
            self.consume()
            right = self.factor()
            return Binary(node, "^", right)
        return node

    def unary(self) -> Expr:
        tok = self.peek()
        if tok and tok[0] == "OP" and tok[1] == "-":
            self.consume()
            operand = self.unary()
            return Unary("-", operand)
        return self.primary()

    def primary(self) -> Expr:
        tok = self.peek()
        if tok is None:
            raise SyntaxError("Unexpected end of input")
        if tok[0] == "NUM":
            self.consume()
            return Literal(float(tok[1]))
        if tok[0] == "NAME":
            self.consume()
            name = tok[1]
            next_tok = self.peek()
            if next_tok and next_tok[0] == "OP" and next_tok[1] == "(":
                self.consume()  # '('
                args: list[Expr] = []
                nxt = self.peek()
                if nxt and not (nxt[0] == "OP" and nxt[1] == ")"):
                    args.append(self.expr())
                    while True:
                        nxt2 = self.peek()
                        if (
                            nxt2
                            and nxt2[0] == "OP"
                            and nxt2[1] == ","
                        ):
                            self.consume()  # ','
                            args.append(self.expr())
                        else:
                            break
                self.consume()  # ')'
                if name not in self.funcs:
                    raise NameError(f"Unknown function: {name}")
                return Call(self.funcs[name], args)
            return Variable(name)
        if tok[0] == "OP" and tok[1] == "(":
            self.consume()
            node = self.expr()
            self.consume()  # ')'
            return node
        raise SyntaxError(f"Unexpected token: {tok}")


# ---------- Evaluator (Visitor) ----------
class Evaluator:
    @arg_type(1, dict)
    def __init__(self, env: dict[str, Any]) -> None:
        self.env = env
        self.trace: dict[int, Any] = {}

    def evaluate(self, node: Expr) -> Any:
        result = node.accept(self)
        self.trace[id(node)] = result
        logger.debug("Eval %s -> %s", type(node).__name__, result)
        return result

    def visit_literal(self, node: Literal) -> Any:
        return node.value

    def visit_variable(self, node: Variable) -> Any:
        if node.name not in self.env:
            raise NameError(f"Variable '{node.name}' not defined")
        return self.env[node.name]

    def visit_binary(self, node: Binary) -> Any:
        left = self.evaluate(node.left)
        right = self.evaluate(node.right)
        if node.op == "+":
            return left + right
        if node.op == "-":
            return left - right
        if node.op == "*":
            return left * right
        if node.op == "/":
            if right == 0:
                raise ZeroDivisionError("Division by zero")
            return left / right
        if node.op == "^":
            return left ** right
        raise ValueError(f"Unknown operator: {node.op}")

    def visit_unary(self, node: Unary) -> Any:
        val = self.evaluate(node.operand)
        if node.op == "-":
            return -val
        raise ValueError(f"Unknown unary operator: {node.op}")

    def visit_call(self, node: Call) -> Any:
        args = [self.evaluate(arg) for arg in node.args]
        logger.debug("Calling with args: %s", args)
        return node.func(*args)


# ---------- Visualizer ----------
class Visualizer:
    def __init__(self) -> None:
        self.lines: list[str] = []
        self.ids: dict[int, str] = {}
        self.counter = 0

    def _nid(self, node: Expr) -> str:
        i = id(node)
        if i not in self.ids:
            self.ids[i] = f"n{self.counter}"
            self.counter += 1
        return self.ids[i]

    def visualize(
        self, node: Expr, trace: Optional[dict[int, Any]] = None
    ) -> str:
        self.lines = ["digraph G {"]
        self._visit(node, trace)
        self.lines.append("}")
        return "\n".join(self.lines)

    def _visit(self, node: Expr, trace: Optional[dict[int, Any]]) -> None:
        nid = self._nid(node)
        if isinstance(node, Literal):
            label = f"{node.value}"
        elif isinstance(node, Variable):
            label = f"var:{node.name}"
        elif isinstance(node, Binary):
            label = node.op
        elif isinstance(node, Unary):
            label = f"u{node.op}"
        elif isinstance(node, Call):
            label = "call"
        else:
            label = "node"

        if trace and id(node) in trace:
            label += f"\\n={trace[id(node)]}"

        self.lines.append(f'{nid}[label="{label}"];')

        if isinstance(node, Binary):
            self._edge(nid, node.left, trace)
            self._edge(nid, node.right, trace)
        elif isinstance(node, Unary):
            self._edge(nid, node.operand, trace)
        elif isinstance(node, Call):
            for arg in node.args:
                self._edge(nid, arg, trace)

    def _edge(
        self, parent: str, child: Expr, trace: Optional[dict[int, Any]]
    ) -> None:
        cid = self._nid(child)
        self.lines.append(f"{parent} -> {cid};")
        self._visit(child, trace)


# ---------- Public API ----------
@arg_type(0, str)
def parse(
    text: str,
    funcs: Optional[dict[str, Callable[..., Any]]] = None,
) -> Expr:
    funcs = funcs or {}
    tokenizer = Tokenizer(text)
    tokens = tokenizer.tokenize()
    parser = Parser(tokens, funcs)
    return parser.parse()


@arg_type(0, Expr)
@arg_type(1, dict)
def evaluate(
    node: Expr, env: Optional[dict[str, Any]] = None
) -> Any:
    env = env or {}
    evaluator = Evaluator(env)
    return evaluator.evaluate(node)


@arg_type(0, Expr)
def to_dot(
    node: Expr, trace: Optional[dict[int, Any]] = None
) -> str:
    return Visualizer().visualize(node, trace)