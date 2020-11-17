import ast

import import_expression

code_base = (
    "async def __aexec__(scope):"
    "\n  try:"
    "\n    pass"
    "\n  finally:"
    "\n    scope.update(locals())"
)


def insert_yield(body):

    if not isinstance(body[-1], ast.Expr):
        return

    if not isinstance(body[-1].value, ast.Yield):
        yield_st = ast.Yield(body[-1].value)
        ast.copy_location(yield_st, body[-1])
        yield_expr = ast.Expr(yield_st)
        ast.copy_location(yield_expr, body[-1])
        body[-1] = yield_expr


def compile_all(code_input):

    code_in = import_expression.parse(code_input)
    base = import_expression.parse(code_base)

    try_block = base.body[-1].body[-1].body
    try_block.extend(code_in.body)

    ast.fix_missing_locations(base)
    insert_yield(try_block)

    return base
