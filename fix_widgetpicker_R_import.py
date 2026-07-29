from pathlib import Path

def ok(msg): print(f"[OK] {msg}")

count = 0
for f in Path("modules/widgetpicker/src").rglob("*.kt"):
    content = f.read_text(encoding="utf-8")
    old = "import com.android.launcher3.widgetpicker.R\n"
    new = "import com.android.launcher3.R\n"
    if old in content:
        content = content.replace(old, new, 1)
        f.write_text(content, encoding="utf-8")
        ok(f"import de R corrigido em {f}")
        count += 1
print(f"\nTotal corrigidos: {count}")
