from __future__ import annotations

import math

import pytest

from expression_tree import (
    Evaluator,
    Literal,
    Tokenizer,
    Variable,
    evaluate,
    non_empty_check,
    parse,
    positive_check,
    range_check,
    to_dot,
    type_check,
)


# ---------- AOP decorator tests ----------
def test_type_check_decorator() -> None:
    @type_check(0, str)
    def foo(a: str) -> str:
        return a

    assert foo("ok") == "ok"
    with pytest.raises(TypeError):
        foo(123)


def test_range_check_decorator() -> None:
    @range_check(0, min_val=0, max_val=100)
    def foo(x: float) -> float:
        return x

    assert foo(50) == 50
    with pytest.raises(ValueError):
        foo(-1)
    with pytest.raises(ValueError):
        foo(101)


def test_non_empty_check_decorator() -> None:
    @non_empty_check(0)
    def foo(s: str) -> str:
        return s

    assert foo("hello") == "hello"
    with pytest.raises(ValueError):
        foo("")
    with pytest.raises(ValueError):
        foo("   ")


def test_positive_check_decorator() -> None:
    @positive_check(0)
    def foo(x: float) -> float:
        return x

    assert foo(5) == 5
    with pytest.raises(ValueError):
        foo(0)
    with pytest.raises(ValueError):
        foo(-1)


# ---------- Edge case tests ----------
def test_empty_string() -> None:
    with pytest.raises(ValueError):
        parse("")


def test_whitespace_only() -> None:
    with pytest.raises(ValueError):
        parse("   ")


def test_unmatched_parentheses() -> None:
    with pytest.raises(SyntaxError):
        parse("(1+2")
    with pytest.raises(SyntaxError):
        parse("1+2)")


def test_consecutive_operators() -> None:
    with pytest.raises(SyntaxError):
        parse("1++2")


def test_invalid_character() -> None:
    with pytest.raises(SyntaxError):
        parse("2$3")


def test_division_by_zero() -> None:
    with pytest.raises(ZeroDivisionError):
        evaluate(parse("1 / 0"))


def test_undefined_variable() -> None:
    with pytest.raises(NameError):
        evaluate(parse("x + 1"))


def test_undefined_function() -> None:
    with pytest.raises(NameError):
        parse("bar(1)")


# ---------- Basic function tests ----------
def test_tokenizer() -> None:
    t = Tokenizer("a + 2.5 * (3 - 4)")
    tokens = t.tokenize()
    assert len(tokens) == 9


def test_parser_literal() -> None:
    node = parse("42")
    assert isinstance(node, Literal)
    assert node.value == 42.0


def test_parser_variable() -> None:
    node = parse("x")
    assert isinstance(node, Variable)
    assert node.name == "x"


def test_eval_simple() -> None:
    assert evaluate(parse("2 + 3")) == 5.0
    assert evaluate(parse("10 - 4")) == 6.0
    assert evaluate(parse("3 * 4")) == 12.0
    assert evaluate(parse("8 / 2")) == 4.0


def test_eval_complex() -> None:
    """Complex example from the lab PDF: a + 2 - sin(-0.3)*(b-c)."""
    env = {"a": 1.0, "b": 2.0, "c": 0.5}
    funcs = {"sin": math.sin}
    node = parse("a + 2 - sin(-0.3) * (b - c)", funcs)
    result = evaluate(node, env)
    expected = 1.0 + 2.0 - math.sin(-0.3) * (2.0 - 0.5)
    assert round(result, 6) == round(expected, 6)


def test_eval_with_user_function() -> None:
    funcs = {"foo": lambda x: x * 42}
    node = parse("foo(2)", funcs)
    assert evaluate(node) == 84.0


def test_visualization() -> None:
    node = parse("2 + 3")
    dot = to_dot(node)
    assert "digraph G" in dot
    assert "+" in dot


def test_trace_visualization() -> None:
    env = {"a": 1.0, "b": 2.0}
    node = parse("a + b")
    evaluator = Evaluator(env)
    result = evaluator.evaluate(node)
    dot = to_dot(node, evaluator.trace)
    assert result == 3.0
    assert "1.0" in dot
    assert "2.0" in dot
    assert "3.0" in dot


# ---------- Operator precedence tests ----------
def test_power_precedence() -> None:
    res = evaluate(parse("2^3^2"))
    assert res == 64.0
    res = evaluate(parse("2^3*2"))
    assert res == 16.0
    res = evaluate(parse("2*3^2"))
    assert res == 18.0


def test_precedence_of_unary_minus() -> None:
    res = evaluate(parse("-2^3"))
    assert res == -8.0
    with pytest.raises(
        SyntaxError, match="Negative exponent must be parenthesized"
    ):
        parse("2^-3")


def test_function_with_multiple_arguments() -> None:
    funcs = {"max3": lambda a, b, c: max(a, b, c)}
    expr = "max3(10, 20, 15)"
    res = evaluate(parse(expr, funcs))
    assert res == 20


# ---------- Complex examples ----------
def test_complex_quadratic_formula() -> None:
    """Complex example: quadratic formula with sqrt and variables."""
    funcs = {"sqrt": math.sqrt}
    a, b, c = 1.0, -3.0, 2.0
    env = {"a": a, "b": b, "c": c}
    expr = "(-b + sqrt(b^2 - 4*a*c)) / (2*a)"
    res = evaluate(parse(expr, funcs), env)
    assert abs(res - 2.0) < 1e-9
    expr_minus = "(-b - sqrt(b^2 - 4*a*c)) / (2*a)"
    res2 = evaluate(parse(expr_minus, funcs), env)
    assert abs(res2 - 1.0) < 1e-9


def test_trace_visualization_with_nested_calls() -> None:
    """
    Complex example: user-defined lambda function with trace annotation.
    Covers both 'user-specific functions' and 'dataflow graph with trace'
    requirements from the lab specification.
    """
    funcs = {"mul": lambda x, y: x * y}
    env = {"a": 2, "b": 3}
    expr = "mul(a, b)"
    node = parse(expr, funcs)
    evaluator = Evaluator(env)
    result = evaluator.evaluate(node)
    assert result == 6
    dot = to_dot(node, evaluator.trace)
    assert "6" in dot
    assert "λ" in dot
