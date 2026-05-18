# Group 3 – Lab 3 – Variant 1: Mathematical Expression Tree Interpreter

This project implements a simple interpreter for mathematical expressions using an expression tree representation.  

## Project structure

- `expression_tree.py` – core implementation:
  - Tokenizer, recursive‑descent parser, AST nodes (`Literal`, `Variable`, `Binary`, `Unary`, `Call`)
  - Evaluator (Visitor pattern) with execution trace
  - Visualizer (GraphViz DOT output)
  - AOP decorators for type, range, non‑empty, and positive checks
  - Public API: `parse()`, `evaluate()`, `to_dot()`
- `test_expression_tree.py` – unit tests covering:
  - Decorator behaviour (type, range, non‑empty, positive)
  - Edge cases (empty string, unmatched parentheses, consecutive operators, invalid characters)
  - Arithmetic (division by zero, precedence, unary minus, power associativity)
  - Function calls (nested, multiple arguments, user exceptions)
  - Complex example: quadratic formula with `sqrt`
  - Trace visualisation with annotated DOT output

## Features

- **Expression language**:
  - Numbers (integer/float), variables (`a`, `b`, `x1`), parentheses
  - Binary operators: `+`, `-`, `*`, `/`, `^` (power, left‑associative)
  - Unary minus (binds tighter than `^`, e.g. `-2^3` = `-(2^3)`)
  - Function calls: built‑in `sin` (example) or user‑supplied (e.g. `{"foo": lambda x: x*42}`)
- **Interpreter**:
  - Recursive‑descent parser with AST construction
  - Visitor‑based evaluator with detailed execution trace (`logger.debug`)
  - Error handling: syntax errors, division by zero, undefined variables/functions, user exceptions
- **AOP input validation** (decorators applied to all public APIs):
  - `@type_check(pos, type)` – type checking (e.g. `parse` expects `str`)
  - `@non_empty_check(pos)` – reject empty/whitespace strings
  - `@range_check(pos, min, max)` – numeric or string‑length bounds (expression length 1…10000)
  - `@positive_check(pos)` – strict positivity for numeric arguments
- **Visualisation**:
  - GraphViz DOT output of the expression tree
  - Optional trace annotation (show computed value in each node)
- **Logging**: Python `logging` module with `DEBUG` level details (tokenization, evaluation, function calls)
- **Testing**:
  - 21 unit tests covering normal, edge, and complex cases
  - Hypothesis property‑based tests (optional, not included in basic template)
  - Coverage measurement (`pytest --cov=.`)

## Contribution

- Xia Jiale (<1436172989@qq.com>) – finish the unit tests

## Changelog

- 13.05.2026 - 0
  - Implementation of basic tests  

## Design notes

### Why a visitor pattern for evaluation?

The AST classes (Literal, Binary…) are stable, but the operations on them may grow.  
Visitor keeps evaluation logic separate from the AST classes and makes it easy to add new operations
without modifying existing nodes.
