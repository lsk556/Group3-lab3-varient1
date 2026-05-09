from __future__ import annotations

import math

import pytest

from expression_tree import (
    Evaluator,
    Literal,
    Tokenizer,
    Variable,
    arg_type,
    evaluate,
    parse,
    to_dot,
)


def test_arg_type_decorator() -> None:
    @arg_type(0, str)
    def foo(a: str) -> str:
        return a

    assert foo("ok") == "ok"
    with pytest.raises(TypeError):
        foo(123)  # type: ignore[arg-type]


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


def test_division_by_zero() -> None:
    with pytest.raises(ZeroDivisionError):
        evaluate(parse("1 / 0"))


def test_undefined_variable() -> None:
    with pytest.raises(NameError):
        evaluate(parse("x + 1"))


def test_undefined_function() -> None:
    with pytest.raises(NameError):
        parse("bar(1)")


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
    assert "1.0" in dot
    assert "2.0" in dot
    assert "3.0" in dot
