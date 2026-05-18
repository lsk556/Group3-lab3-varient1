from __future__ import annotations

import math
import pytest

from expression_tree import (
    Evaluator,
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
    """verify that type_check will reject parameters of the wrong type"""

    @type_check(0, str)
    def foo(a: str) -> str:
        return a

    assert foo("ok") == "ok"
    with pytest.raises(TypeError):
        foo(123)


def test_range_check_decorator() -> None:
    """Verify the range_check decorator"""

    @range_check(0, min_val=0, max_val=100)
    def foo(x: float) -> float:
        return x

    assert foo(50) == 50
    with pytest.raises(ValueError):
        foo(-1)
    with pytest.raises(ValueError):
        foo(101)


def test_non_empty_check_decorator() -> None:
    """Verify non_empty_check decorator"""

    @non_empty_check(0)
    def foo(s: str) -> str:
        return s

    assert foo("hello") == "hello"
    with pytest.raises(ValueError):
        foo("")
    with pytest.raises(ValueError):
        foo("   ")


def test_positive_check_decorator() -> None:
    """Verify positive_check rejects zero or negative numbers"""

    @positive_check(0)
    def foo(x: float) -> float:
        return x

    assert foo(5) == 5
    with pytest.raises(ValueError):
        foo(0)
    with pytest.raises(ValueError):
        foo(-1)


# ---------- Tests for edge cases and complex examples ----------
def test_empty_string() -> None:
    """Ensure the error for an empty expression string."""
    with pytest.raises(ValueError):
        parse("")


def test_whitespace_only() -> None:
    """reject a string containing only whitespace."""
    with pytest.raises(ValueError):
        parse("   ")


def test_unmatched_parentheses() -> None:
    """Error of  unbalanced parentheses"""
    with pytest.raises(SyntaxError):
        parse("(1+2")
    with pytest.raises(SyntaxError):
        parse("1+2)")


def test_consecutive_operators() -> None:
    """Ensure consecutive operators (1++2)"""
    with pytest.raises(SyntaxError):
        parse("1++2")


def test_invalid_character() -> None:
    """Ensure an invalid character in the input triggers a SyntaxError"""
    with pytest.raises(SyntaxError):
        parse("2$3")


def test_division_by_zero() -> None:
    """Cannot be divided by 0"""
    with pytest.raises(ZeroDivisionError):
        evaluate(parse("1/0"))


def test_undefined_variable() -> None:
    """Undefined variables should not be used."""
    with pytest.raises(NameError):
        evaluate(parse("x + 1"))


def test_undefined_function() -> None:
    """Undefined functions cannot be called"""
    with pytest.raises(NameError):
        parse("bar(1)")


def test_power_precedence() -> None:
    """Test left-associativity"""
    res = evaluate(parse("2^3^2"))
    assert res == 64.0
    res = evaluate(parse("2^3*2"))
    assert res == 16.0
    res = evaluate(parse("2*3^2"))
    assert res == 18.0


def test_nested_function_call() -> None:
    """Test evaluation of nested function"""
    funcs = {"add": lambda a, b: a + b, "square": lambda x: x * x}
    expr = "add(square(2), square(3))"
    res = evaluate(parse(expr, funcs))
    assert res == 4 + 9 == 13.0


def test_complex_quadratic_formula() -> None:
    """Test a realistic quadratic formula with sqrt and variables"""
    funcs = {"sqrt": math.sqrt}
    a, b, c = 1.0, -3.0, 2.0
    env = {"a": a, "b": b, "c": c}
    expr = "(-b + sqrt(b^2 - 4*a*c)) / (2*a)"
    res = evaluate(parse(expr, funcs), env)
    assert abs(res - 2.0) < 1e-9
    expr_minus = "(-b - sqrt(b^2 - 4*a*c)) / (2*a)"
    res2 = evaluate(parse(expr_minus, funcs), env)
    assert abs(res2 - 1.0) < 1e-9


def test_deeply_nested_expression() -> None:
    """Test a deeply parenthesized expression"""
    expr = "1+(2+(3+(4+5)))"
    res = evaluate(parse(expr))
    assert res == 1 + 2 + 3 + 4 + 5


def test_user_function_exception() -> None:
    """Ensure exceptions raised by user-defined functions propagate correctly"""

    def faulty(x):
        raise RuntimeError("intentional error")

    funcs = {"bad": faulty}
    expr = "bad(42)"
    node = parse(expr, funcs)
    with pytest.raises(RuntimeError):
        evaluate(node)


def test_trace_visualization_with_nested_calls() -> None:
    """test the trace annotations appear in DOT output for nested calls"""
    funcs = {"mul": lambda x, y: x * y}
    env = {"a": 2, "b": 3}
    expr = "mul(a, b)"
    node = parse(expr, funcs)
    evaluator = Evaluator(env)
    result = evaluator.evaluate(node)
    assert result == 6
    dot = to_dot(node, evaluator.trace)
    assert "6" in dot
    assert "λ" in dot  # lambda function appears as λ


def test_large_expression_with_many_operators() -> None:
    """Test if a series of additions works."""
    expr = "1+2+3+4+5+6+7+8+9+10+11+12+13+14+15+16+17+18+19+20"
    res = evaluate(parse(expr))
    assert res == sum(range(1, 21))


def test_precedence_of_unary_minus() -> None:
    """Test that unary minus binds tighter than power"""
    res = evaluate(parse("-2^3"))
    assert res == -8.0
    with pytest.raises(SyntaxError, match="Negative exponent must be parenthesized"):
        parse("2^-3")


def test_function_with_multiple_arguments() -> None:
    """Test function call with three positional arguments"""
    funcs = {"max3": lambda a, b, c: max(a, b, c)}
    expr = "max3(10, 20, 15)"
    res = evaluate(parse(expr, funcs))
    assert res == 20


if __name__ == "__main__":
    pytest.main()
