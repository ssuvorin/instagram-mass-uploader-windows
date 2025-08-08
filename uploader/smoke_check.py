"""
Static smoke check: parses all refactored modules with AST and lists exported names.
No third-party imports, safe to run anywhere.
"""
import os, ast, json

ROOT = os.path.dirname(__file__)
AS_DIR = os.path.join(ROOT, "async_impl")

report = {}
for fn in sorted(os.listdir(AS_DIR)):
    if not fn.endswith(".py"):
        continue
    path = os.path.join(AS_DIR, fn)
    try:
        code = open(path, "r", encoding="utf-8", errors="ignore").read()
        tree = ast.parse(code)
        names = []
        for n in tree.body:
            if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
                names.append(n.name)
        report[fn] = {"count": len(names), "names": names[:50]}
    except Exception as e:
        report[fn] = {"error": repr(e)}

print(json.dumps(report, ensure_ascii=False, indent=2))
