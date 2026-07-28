from pathlib import Path

def ok(msg): print(f"[OK] {msg}")
def skip(msg): print(f"[SKIP] {msg}")
def fail(msg): print(f"[FALHOU] {msg}")

p = Path("aosp-stubs/com/android/window/flags/Flags.java")
if not p.exists():
    fail(f"não encontrei {p}")
    raise SystemExit(1)

content = p.read_text(encoding="utf-8")
print("--- conteúdo atual ---")
print(content)
print("--- fim ---")

if "showHomeBehindDesktop" in content:
    skip("showHomeBehindDesktop() já existe")
else:
    last_brace = content.rfind("}")
    if last_brace == -1:
        fail("não achei chave de fechamento")
    else:
        new_method = (
            "    public static boolean showHomeBehindDesktop() {\n"
            "        return false;\n"
            "    }\n\n"
        )
        content = content[:last_brace] + new_method + content[last_brace:]
        p.write_text(content, encoding="utf-8")
        ok(f"showHomeBehindDesktop() adicionado em {p}")

print("\nScript concluído.")
