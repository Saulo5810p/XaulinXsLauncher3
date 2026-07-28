from pathlib import Path
import re

patterns_found = []
for ext in ("*.java", "*.kt"):
    for p in Path("src").rglob(ext):
        try:
            content = p.read_text(encoding="utf-8", errors="ignore")
        except Exception:
            continue
        for m in re.finditer(r'\.register\(([^;]{0,200}?)\)', content):
            snippet = m.group(0).replace("\n", " ")
            if "Filter" in snippet or "filter" in snippet:
                line_no = content[:m.start()].count("\n") + 1
                patterns_found.append((str(p), line_no, snippet[:150]))

print(f"Total de chamadas .register(...) com 'filter' no argumento: {len(patterns_found)}\n")
for path, line_no, snippet in patterns_found:
    print(f"{path}:{line_no}\n    {snippet}\n")
