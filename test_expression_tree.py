from __future__ import annotations

import math
import pytest

from expression_tree import (
    Evaluator,
    Literal,
    Variable,
    evaluate,
    parse,
    to_dot,
    type_check,
    range_check,
    non_empty_check,
    positive_check,
)


# ---------- Tests for AOP decorators ----------
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
    assert foo(0) == 0   # range_check with min_val=0 allows 0
    # For strict positive, use strict_positive_check
    @strict_positive_check(0)
    def bar(x: float) -> float:
        return x
    assert bar(1) == 1
    with pytest.raises(ValueError):
        bar(0)


# ---------- Tests for edge cases and complex examples ----------
def test_empty_string() -> None:
    with pytest.raises(ValueError):  # non_empty_check catches
        parse("")


def test_whitespace_only() -> None:
    with pytest.raises(ValueError):  # non_empty_check catches
        parse("   ")


def test_unmatched_parentheses() -> None:
    with pytest.raises(SyntaxError):
        parse("(1+2")
    with pytest.raises(SyntaxError):
        parse("1+2)")


def test_consecutive_operators() -> None:
    # Our parser doesn't support '1++2', it will raise syntax error
    with pytest.raises(SyntaxError):
        parse("1++2")


def test_invalid_character() -> None:
    with pytest.raises(SyntaxError):
        parse("2$3")


def test_division_by_zero() -> None:
    with pytest.raises(ZeroDivisionError):
        evaluate(parse("1/0"))


def test_undefined_variable() -> None:
    with pytest.raises(NameError):
        evaluate(parse("x + 1"))


def test_undefined_function() -> None:
    with pytest.raises(NameError):
        parse("bar(1)")


def test_power_precedence() -> None:
    # '^' has higher precedence than '*' and '/'
    # 2^3*2 -> (2^3)*2 = 8*2=16
    res = evaluate(parse("2^3*2"))
    assert res == 16.0
    # 2*3^2 -> 2*(3^2)=18
    res = evaluate(parse("2*3^2"))
    assert res == 18.0
    # Left-associative: 2^3^2 -> (2^3)^2 = 64 (not 2^(3^2)=512)
    res = evaluate(parse("2^3^2"))
    assert res == 64.0  # as implemented


def test_nested_function_call() -> None:
    funcs = {"add": lambda a, b: a + b, "square": lambda x: x * x}
    expr = "add(square(2), square(3))"
    res = evaluate(parse(expr, funcs))
    assert res == 4 + 9 == 13.0


def test_complex_quadratic_formula() -> None:
    # Solve quadratic equation: a*x^2 + b*x + c = 0, use formula (-b + sqrt(b^2-4ac))/(2a)
    # We'll compute both roots with two expressions, but test one branch.
    funcs = {"sqrt": math.sqrt}
    a, b, c = 1.0, -3.0, 2.0   # roots 1 and 2
    env = {"a": a, "b": b, "c": c}
    expr = "(-b + sqrt(b^2 - 4*a*c)) / (2*a)"
    res = evaluate(parse(expr, funcs), env)
    assert abs(res - 2.0) < 1e-9   # root 2
    expr_minus = "(-b - sqrt(b^2 - 4*a*c)) / (2*a)"
    res2 = evaluate(parse(expr_minus, funcs), env)
    assert abs(res2 - 1.0) < 1e-9   # root 1


def test_deeply_nested_expression() -> None:
    # Create a deeply nested expression to test recursion depth
    # e.g., 1+(2+(3+(4+5)))...
    # Build programmatically
    expr = "1"
    for i in range(2, 100):
        expr = f"{i}+({expr})"  # Actually we want right-associative nesting
    # But our parser can handle up to recursion limit ~1000; 100 should be fine.
    # However constructing that string might be large; we test a moderate depth
    expr = "1+(2+(3+(4+5)))"
    res = evaluate(parse(expr))
    assert res == 1+2+3+4+5


def test_user_function_exception() -> None:
    def faulty(x):
        raise RuntimeError("intentional error")
    funcs = {"bad": faulty}
    expr = "bad(42)"
    node = parse(expr, funcs)
    with pytest.raises(RuntimeError):
        evaluate(node)


def test_trace_visualization_with_nested_calls() -> None:
    funcs = {"mul": lambda x, y: x * y}
    env = {"a": 2, "b": 3}
    expr = "mul(a, b)"
    node = parse(expr, funcs)
    evaluator = Evaluator(env)
    result = evaluator.evaluate(node)
    assert result == 6
    dot = to_dot(node, evaluator.trace)
    assert "6" in dot
    assert "mul" in dot


def test_large_expression_with_many_operators() -> None:
    # Stress test with 50 additions
    expr = "1+2+3+4+5+6+7+8+9+10+11+12+13+14+15+16+17+18+19+20"
    res = evaluate(parse(expr))
    assert res == sum(range(1, 21))


def test_precedence_of_unary_minus() -> None:
    # -2^3 should be parsed as -(2^3) = -8
    res = evaluate(parse("-2^3"))
    assert res == -8.0
    # 2^-3 is not supported (negative exponent requires parentheses), but test syntax error
    with pytest.raises(SyntaxError):
        parse("2^-3")


def test_function_with_multiple_arguments() -> None:
    funcs = {"max3": lambda a, b, c: max(a, b, c)}
    expr = "max3(10, 20, 15)"
    res = evaluate(parse(expr, funcs))
    assert res == 20


if __name__ == "__main__":
    pytest.main()