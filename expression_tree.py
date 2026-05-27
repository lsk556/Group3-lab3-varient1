from __future__ import annotations

import functools
import logging
import os
import re
from typing import Any, Callable, Optional

import matplotlib
matplotlib.use("Agg")  # noqa: E402
import matplotlib.pyplot as plt  # noqa: E402
import matplotlib.patches as patches  # noqa: E402
from matplotlib.figure import Figure  # noqa: E402

# ---------- Logging ----------
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger("expr")


# ---------- AOP decorators ----------
def type_check(
    pos: int, expected_type: type[Any],
) -> Callable[[Callable[..., Any]], Callable[..., Any]]:
    """Decorator to check argument type at given position."""

    def decorator(
        func: Callable[..., Any],
    ) -> Callable[..., Any]:
        @functools.wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            if (
                len(args) > pos
                and args[pos] is not None
                and not isinstance(args[pos], expected_type)
            ):
                error_msg = (
                    f"{func.__name__} arg {pos} expects "
                    f"{expected_type.__name__}, got "
                    f"{type(args[pos]).__name__}"
                )
                logger.error(error_msg)
                raise TypeError(error_msg)
            return func(*args, **kwargs)

        return wrapper

    return decorator


def range_check(
    pos: int,
    min_val: Optional[float] = None,
    max_val: Optional[float] = None,
) -> Callable[[Callable[..., Any]], Callable[..., Any]]:
    """
    Check numeric value or string length lies within [min_val, max_val].
    For strings, checks length. For numbers, checks value.
    """

    def decorator(
        func: Callable[..., Any],
    ) -> Callable[..., Any]:
        @functools.wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            if len(args) > pos:
                val = args[pos]
                if val is not None:
                    if isinstance(val, str):
                        length = len(val)
                        if min_val is not None and length < min_val:
                            raise ValueError(
                                f"{func.__name__}: string length "
                                f"{length} < {min_val}"
                            )
                        if max_val is not None and length > max_val:
                            raise ValueError(
                                f"{func.__name__}: string length "
                                f"{length} > {max_val}"
                            )
                    elif isinstance(val, (int, float)):
                        if min_val is not None and val < min_val:
                            raise ValueError(
                                f"{func.__name__}: value {val} < {min_val}"
                            )
                        if max_val is not None and val > max_val:
                            raise ValueError(
                                f"{func.__name__}: value {val} > {max_val}"
                            )
            return func(*args, **kwargs)

        return wrapper

    return decorator


def non_empty_check(
    pos: int,
) -> Callable[[Callable[..., Any]], Callable[..., Any]]:
    """Decorator to check string argument is not empty (after stripping)."""

    def decorator(
        func: Callable[..., Any],
    ) -> Callable[..., Any]:
        @functools.wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            if len(args) > pos:
                val = args[pos]
                if isinstance(val, str) and val.strip() == "":
                    error_msg = (
                        f"{func.__name__} arg {pos} must be a "
                        f"non-empty string"
                    )
                    logger.error(error_msg)
                    raise ValueError(error_msg)
            return func(*args, **kwargs)

        return wrapper

    return decorator


def positive_check(
    pos: int,
) -> Callable[[Callable[..., Any]], Callable[..., Any]]:
    """Decorator to check numeric argument is positive."""

    def decorator(
        func: Callable[..., Any],
    ) -> Callable[..., Any]:
        @functools.wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            if len(args) > pos:
                val = args[pos]
                if val is not None and isinstance(val, (int, float)):
                    if val <= 0:
                        error_msg = (
                            f"{func.__name__} arg {pos} value {val} "
                            f"must be > 0"
                        )
                        logger.error(error_msg)
                        raise ValueError(error_msg)
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
    @type_check(1, str)
    @non_empty_check(1)
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
            if ch in "+-*/^(),":
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

    def tokens_table(self) -> str:
        """Return a markdown table of tokens."""
        tokens = self.tokenize()
        lines = ["| Token | Value |", "|-------|-------|"]
        for kind, val in tokens:
            lines.append(f"| {kind} | `{val}` |")
        return "\n".join(lines)


# ---------- Parser ----------
class Parser:
    @type_check(1, list)
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
        node = self.unary(allow_unary_after_power=True)
        while True:
            tok = self.peek()
            if tok and tok[0] == "OP" and tok[1] == "^":
                self.consume()
                right = self.unary(allow_unary_after_power=False)
                node = Binary(node, "^", right)
            else:
                break
        return node

    def unary(self, allow_unary_after_power: bool = True) -> Expr:
        tok = self.peek()
        if tok and tok[0] == "OP" and tok[1] == "-":
            if not allow_unary_after_power:
                raise SyntaxError(
                    "Negative exponent must be parenthesized "
                    "(e.g., 2^(-3))"
                )
            self.consume()
            operand = self.unary(allow_unary_after_power)
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
    @type_check(1, dict)
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
            return left**right
        raise ValueError(f"Unknown operator: {node.op}")

    def visit_unary(self, node: Unary) -> Any:
        val = self.evaluate(node.operand)
        if node.op == "-":
            return -val
        raise ValueError(f"Unknown unary operator: {node.op}")

    def visit_call(self, node: Call) -> Any:
        args = [self.evaluate(arg) for arg in node.args]
        func_name = getattr(node.func, "__name__", "call")
        logger.debug("Calling %s with args: %s", func_name, args)
        try:
            return node.func(*args)
        except Exception as e:
            logger.error("Error in function call: %s", e)
            raise


# ---------- Legacy Visualizer (DOT output, kept for compatibility) ----------
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
            func_name = getattr(node.func, "__name__", "call")
            if func_name == "<lambda>":
                func_name = "λ"
            label = func_name
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


# ---------- Matplotlib PNG Visualizer ----------
class _Layout:
    def __init__(self) -> None:
        self.pos: dict[int, tuple[float, float, str]] = {}
        self._counter = 0.0

    def _traverse(self, node: Optional[Expr], depth: int = 0) -> None:
        if node is None:
            return
        if isinstance(node, Binary):
            self._traverse(node.left, depth + 1)
            label = self._label(node)
            self.pos[id(node)] = (self._counter, -depth, label)
            self._counter += 1.2
            self._traverse(node.right, depth + 1)
        elif isinstance(node, Unary):
            self._traverse(node.operand, depth + 1)
            label = self._label(node)
            self.pos[id(node)] = (self._counter, -depth, label)
            self._counter += 1.2
        elif isinstance(node, Call):
            for arg in node.args:
                self._traverse(arg, depth + 1)
            label = self._label(node)
            self.pos[id(node)] = (self._counter, -depth, label)
            self._counter += 1.2
        else:
            # Literal, Variable
            label = self._label(node)
            self.pos[id(node)] = (self._counter, -depth, label)
            self._counter += 1.2

    def _label(self, node: Expr) -> str:
        if isinstance(node, Literal):
            return f"{node.value}"
        if isinstance(node, Variable):
            return f"var:{node.name}"
        if isinstance(node, Binary):
            return node.op
        if isinstance(node, Unary):
            return f"u{node.op}"
        if isinstance(node, Call):
            fn = getattr(node.func, "__name__", "call")
            return "λ" if fn == "<lambda>" else fn
        return "node"


def visualize_png(
    node: Expr,
    trace: Optional[dict[int, Any]] = None,
    path: Optional[str] = None,
    figsize: tuple[float, float] = (8, 5),
) -> Figure:
    """Draw expression tree as PNG image using matplotlib."""
    trace = trace or {}
    layout = _Layout()
    layout._traverse(node)

    fig, ax = plt.subplots(figsize=figsize)
    if not layout.pos:
        ax.text(0.5, 0.5, "Empty", ha="center", va="center")
        ax.set_xlim(0, 1)
        ax.set_ylim(0, 1)
        ax.axis("off")
        if path:
            fig.savefig(path, dpi=150, bbox_inches="tight")
        return fig

    xs = [p[0] for p in layout.pos.values()]
    ys = [p[1] for p in layout.pos.values()]
    ax.set_xlim(min(xs) - 0.8, max(xs) + 0.8)
    ax.set_ylim(min(ys) - 1.0, max(ys) + 1.0)
    ax.axis("off")

    def _edges(n: Optional[Expr]) -> None:
        if n is None or not isinstance(n, (Binary, Unary, Call)):
            return
        px, py, _ = layout.pos[id(n)]
        children: list[Expr] = []
        if isinstance(n, Binary):
            children = [n.left, n.right]
        elif isinstance(n, Unary):
            children = [n.operand]
        elif isinstance(n, Call):
            children = n.args
        for child in children:
            if child is not None and id(child) in layout.pos:
                cx, cy, _ = layout.pos[id(child)]
                ax.plot([px, cx], [py - 0.3, cy + 0.3], "k-", lw=1.5)
                _edges(child)

    _edges(node)

    for nid, (x, y, label) in layout.pos.items():
        val = trace.get(nid)
        display = f"{label}\n= {val}" if val is not None else label
        color = "#c8e6c9" if val is not None else "#e3f2fd"
        edge = "#2e7d32" if val is not None else "#1565c0"

        box = patches.FancyBboxPatch(
            (x - 0.45, y - 0.3), 0.9, 0.6,
            boxstyle="round,pad=0.05",
            facecolor=color,
            edgecolor=edge,
            lw=2,
        )
        ax.add_patch(box)
        ax.text(
            x, y, display, ha="center", va="center",
            fontsize=11, weight="bold",
        )

    plt.tight_layout()
    if path:
        fig.savefig(path, dpi=150, bbox_inches="tight")
    return fig


# ---------- Step-by-step evaluation with PNG ----------
def _postorder(node: Expr) -> list[Expr]:
    """Return nodes in post-order (leaves to root)."""
    result: list[Expr] = []
    if isinstance(node, Binary):
        result.extend(_postorder(node.left))
        result.extend(_postorder(node.right))
    elif isinstance(node, Unary):
        result.extend(_postorder(node.operand))
    elif isinstance(node, Call):
        for arg in node.args:
            result.extend(_postorder(arg))
    result.append(node)
    return result


def evaluate_steps_png(
    node: Expr,
    env: Optional[dict[str, Any]] = None,
    out_dir: str = "evaluation_steps",
) -> list[tuple[Expr, Any, str]]:
    """Evaluate step by step, generating a PNG image at each step."""
    os.makedirs(out_dir, exist_ok=True)
    env = env or {}
    evaluator = Evaluator(env)
    steps: list[tuple[Expr, Any, str]] = []
    for i, n in enumerate(_postorder(node), start=1):
        result = evaluator.evaluate(n)
        path = os.path.join(out_dir, f"step{i:02d}.png")
        visualize_png(node, evaluator.trace, path=path)
        steps.append((n, result, path))
    return steps


def explain_computation_png(
    text: str,
    env: Optional[dict[str, Any]] = None,
    funcs: Optional[dict[str, Callable[..., Any]]] = None,
    out_dir: str = "evaluation_steps",
) -> dict[str, Any]:
    """
    Full pipeline: tokenize -> parse -> evaluate step by step.
    Generates artifacts for each phase.
    """
    os.makedirs(out_dir, exist_ok=True)

    # Phase 1: Tokenize
    tokenizer = Tokenizer(text)
    tokens = tokenizer.tokenize()
    with open(
        os.path.join(out_dir, "01_tokens.md"), "w", encoding="utf-8"
    ) as f:
        f.write(f"# Tokens for: `{text}`\n\n")
        f.write(tokenizer.tokens_table())

    # Phase 2: Parse (AST)
    parser = Parser(tokens, funcs or {})
    ast = parser.parse()
    visualize_png(ast, path=os.path.join(out_dir, "02_ast.png"))

    # Phase 3: Evaluate step by step
    steps = evaluate_steps_png(ast, env, out_dir)

    return {
        "tokens": tokens,
        "ast": ast,
        "steps": steps,
        "final_result": steps[-1][1] if steps else None,
    }


# ---------- Public API with AOP ----------
@type_check(0, str)
@non_empty_check(0)
@range_check(0, min_val=1, max_val=10000)
@type_check(1, dict)
def parse(
    text: str, funcs: Optional[dict[str, Callable[..., Any]]] = None
) -> Expr:
    funcs = funcs or {}
    tokenizer = Tokenizer(text)
    tokens = tokenizer.tokenize()
    parser = Parser(tokens, funcs)
    return parser.parse()


@type_check(0, Expr)
@type_check(1, dict)
def evaluate(
    node: Expr, env: Optional[dict[str, Any]] = None
) -> Any:
    env = env or {}
    evaluator = Evaluator(env)
    return evaluator.evaluate(node)


@type_check(0, Expr)
@type_check(1, dict)
def to_dot(
    node: Expr, trace: Optional[dict[int, Any]] = None
) -> str:
    """Legacy DOT output (kept for compatibility)."""
    return Visualizer().visualize(node, trace)
