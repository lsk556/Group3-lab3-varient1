# Group-3 - lab 3 - variant 1

This project implements a simple interpreter for mathematical expressions
using an expression tree representation.

## Project Structure

- expression_tree.py — Core implementation: tokenizer, recursive-descent
  parser, AST nodes, evaluator, visualizer, AOP decorators
- test_expression_tree.py — Unit tests covering decorators, edge cases,
  arithmetic, function calls, complex examples, and trace visualisation

## Core API Functions

- parse — Parse expression string into AST
- evaluate — Evaluate AST with given variable environment
- to_dot — Generate GraphViz DOT output with optional trace

## Advanced Features

- Tokenizer — Split input string into tokens (numbers, names, operators)
- Parser — Recursive-descent parser building AST (Literal, Variable,
  Binary, Unary, Call)
- Evaluator — Visitor pattern evaluator with execution trace
- Visualizer — GraphViz DOT output with trace annotation
- AOP decorators — type_check, range_check, non_empty_check,
  positive_check applied to all public APIs

## Contribution Log

### 09.05.2026 — Lin Shengkai

- Implemented expression tree interpreter
- Wrote tokenizer, parser, evaluator, and visualizer
- Implemented AOP decorators for input validation
- Wrote basic tests

### 13.05.2026 — Xia Jiale

- Finished unit tests

### 18.05.2026 — Lin Shengkai

- Merged branch with Xia Jiale
- Adjusted code style and README format
- Passed all CI checks

## Design Notes

- **Visitor pattern** — Keeps evaluation logic separate from AST nodes,
  making it easy to add new operations without modifying existing classes.
- **AOP decorators** — Applied to all public APIs for type, range,
  non-empty, and positive validation.
- **No eval/exec** — Pure recursive-descent parser and visitor-based
  evaluator; no Python string evaluation.
- **No string dispatch** — Visitor pattern used instead of operator
  dictionaries.
- **Logging** — Python logging module records tokenization, evaluation,
  and function calls at DEBUG level.
- **Error handling** — Syntax errors, division by zero, undefined
  variables/functions, and user exceptions are caught with detailed
  messages.
