# billing_evaluator_secure.py

import ast
import operator
import logging
import argparse

# Setup logging
logging.basicConfig(filename="billing_log.txt", level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# Operator mappings
OPERATORS = {
    ast.Add: operator.add,
    ast.Sub: operator.sub,
    ast.Mult: operator.mul,
    ast.Div: lambda x, y: x / y if y != 0 else float('inf'),
    ast.Mod: operator.mod,
    ast.Pow: operator.pow,
    ast.Gt: operator.gt,
    ast.Lt: operator.lt,
    ast.GtE: operator.ge,
    ast.LtE: operator.le,
    ast.Eq: operator.eq,
    ast.NotEq: operator.ne,
    ast.And: lambda x, y: x and y,
    ast.Or: lambda x, y: x or y,
}

# Safe environment variables
SAFE_FUNCS = {}

class EvalError(Exception):
    pass

class BillingSession:
    def __init__(self, customer_id="demo"):
        self.vars = {
            'isPeak': True,
            'isLowIncome': False,
            'units': 120,
            'rate': 5.0,
            'base': 100,
            'surcharge': 50,
            'maintenanceFee': 20,
        }
        self.customer_id = customer_id

    def evaluate(self, expr):
        try:
            tree = ast.parse(expr, mode='exec')
            result = self._eval(tree)
            logging.info(f"Evaluated: {expr} => {result}")
            return result
        except Exception as e:
            logging.error(f"Error in expression '{expr}': {str(e)}")
            return f"Error: {str(e)}"

    def _eval(self, node):
        if isinstance(node, ast.Module):
            return self._eval(node.body[0])

        elif isinstance(node, ast.Expr):
            return self._eval(node.value)

        elif isinstance(node, ast.Assign):
            var_name = node.targets[0].id
            value = self._eval(node.value)
            self.vars[var_name] = value
            return value

        elif isinstance(node, ast.BinOp):
            left = self._eval(node.left)
            right = self._eval(node.right)
            op_type = type(node.op)
            if op_type in OPERATORS:
                return OPERATORS[op_type](left, right)
            raise EvalError(f"Unsupported operator: {op_type}")

        elif isinstance(node, ast.Compare):
            left = self._eval(node.left)
            for op, comparator in zip(node.ops, node.comparators):
                right = self._eval(comparator)
                op_type = type(op)
                if op_type in OPERATORS:
                    if not OPERATORS[op_type](left, right):
                        return False
                else:
                    raise EvalError(f"Unsupported comparison: {op_type}")
                left = right
            return True

        elif isinstance(node, ast.BoolOp):
            values = [self._eval(v) for v in node.values]
            result = values[0]
            for val in values[1:]:
                result = OPERATORS[type(node.op)](result, val)
            return result

        elif isinstance(node, ast.UnaryOp):
            operand = self._eval(node.operand)
            if isinstance(node.op, ast.USub):
                return -operand
            elif isinstance(node.op, ast.Not):
                return not operand
            else:
                raise EvalError("Unsupported unary operator")

        elif isinstance(node, ast.IfExp):
            condition = self._eval(node.test)
            return self._eval(node.body if condition else node.orelse)

        elif isinstance(node, ast.Call):
            func_name = node.func.id
            if func_name not in SAFE_FUNCS:
                raise EvalError(f"Function {func_name} is not allowed")
            args = [self._eval(arg) for arg in node.args]
            result = SAFE_FUNCS[func_name](*args)
            logging.info(f"Called {func_name}({args}) -> {result}")
            return result

        elif isinstance(node, ast.Name):
            if node.id in self.vars:
                return self.vars[node.id]
            else:
                raise EvalError(f"Unknown variable: {node.id}")

        elif isinstance(node, ast.Constant):
            return node.value

        elif isinstance(node, ast.Expr):
            return self._eval(node.value)

        else:
            raise EvalError(f"Unsupported syntax: {ast.dump(node)}")

# CLI usage
if __name__ == '__main__':
    parser = argparse.ArgumentParser(description="Safe Billing Expression Evaluator")
    parser.add_argument('--expr', nargs='*', help="Expressions to evaluate")
    parser.add_argument('--interactive', action='store_true', help="Start interactive mode")
    args = parser.parse_args()

    session = BillingSession()

    if args.expr:
        for exp in args.expr:
            print(f"> {exp}\n= {session.evaluate(exp)}\n")
    elif args.interactive:
        print("Entering interactive mode. Type 'exit' to quit.")
        while True:
            user_input = input("Enter expression: ").strip()
            if user_input.lower() == 'exit':
                break
            if user_input:
                result = session.evaluate(user_input)
                print(f"Result: {result}\n")
    else:
        expressions = [
            "total = base + (units * rate) + (surcharge if isPeak else 0)",
            "discountedBill = total * 0.9 if units < 100 else total",
            "penalty = 500 if units > 1000 and not isLowIncome else 0",
            "bill = total + penalty + maintenanceFee"
        ]
        for exp in expressions:
            print(f"> {exp}\n= {session.evaluate(exp)}\n")
