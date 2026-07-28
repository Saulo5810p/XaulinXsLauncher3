from pathlib import Path

def ok(msg): print(f"[OK] {msg}")
def skip(msg): print(f"[SKIP] {msg}")
def fail(msg): print(f"[FALHOU] {msg}")

# Adicionar o método showHomeBehindDesktop() que falta na classe Flags
p = Path("aosp-stubs/com/android/launcher3/config/Flags.java")
if not p.exists():
    candidates = list(Path(".").rglob("Flags.java"))
    if not candidates:
        fail("não encontrei nenhum Flags.java no projeto")
        raise SystemExit(1)
    p = candidates[0]
    for c in candidates:
        if "showDesktopWindowingPersistence" in c.read_text(encoding="utf-8", errors="ignore") or "aosp-stubs" in str(c):
            p = c
            break

content = p.read_text(encoding="utf-8")

if "showHomeBehindDesktop" in content:
    skip(f"showHomeBehindDesktop() já existe em {p}")
else:
    last_brace = content.rfind("}")
    if last_brace == -1:
        fail(f"não achei chave de fechamento em {p}")
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
