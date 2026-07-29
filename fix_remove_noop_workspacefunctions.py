from pathlib import Path

def ok(msg): print(f"[OK] {msg}")
def skip(msg): print(f"[SKIP] {msg}")

p = Path("deferred-appfunctions-widgetpicker/PreviewContext.kt")
content = p.read_text(encoding="utf-8")
original = content

old_import = "import com.android.launcher3.workspacefunctions.NoOpWorkspaceFunctionsModule\n"
if old_import in content:
    content = content.replace(old_import, "", 1)
    ok("import removido")

old_module_entry = "                NoOpWorkspaceFunctionsModule::class,\n"
if old_module_entry in content:
    content = content.replace(old_module_entry, "", 1)
    ok("entrada removida")

if content != original:
    p.write_text(content, encoding="utf-8")
    ok("PreviewContext.kt salvo")
