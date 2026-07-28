from pathlib import Path

def ok(msg): print(f"[OK] {msg}")
def skip(msg): print(f"[SKIP] {msg}")
def fail(msg): print(f"[FALHOU] {msg}")

p = Path("src/com/android/launcher3/util/SimpleBroadcastReceiver.kt")
if not p.exists():
    fail(f"não encontrei {p}")
    raise SystemExit(1)

content = p.read_text(encoding="utf-8")

old_import = "import android.content.Context\n"
new_import = "import android.content.Context\nimport android.content.Context.RECEIVER_NOT_EXPORTED\n"
if "Context.RECEIVER_NOT_EXPORTED" in content or "import android.content.Context.RECEIVER_NOT_EXPORTED" in content:
    skip("import de RECEIVER_NOT_EXPORTED já existe")
elif old_import in content:
    content = content.replace(old_import, new_import, 1)
    ok("import de RECEIVER_NOT_EXPORTED adicionado")
else:
    fail("não achei a linha 'import android.content.Context' pra ancorar o novo import")

old_param = "        flags: Int = 0,\n"
new_param = "        flags: Int = RECEIVER_NOT_EXPORTED,\n"
if "flags: Int = RECEIVER_NOT_EXPORTED" in content:
    skip("default de flags já é RECEIVER_NOT_EXPORTED")
elif old_param in content:
    content = content.replace(old_param, new_param, 1)
    ok("default de 'flags' alterado de 0 para RECEIVER_NOT_EXPORTED")
else:
    fail("não achei 'flags: Int = 0,' pra substituir (confere manualmente)")

p.write_text(content, encoding="utf-8")
print("\nScript concluído.")
