from pathlib import Path

def ok(msg): print(f"[OK] {msg}")
def skip(msg): print(f"[SKIP] {msg}")
def fail(msg): print(f"[FALHOU] {msg}")

# 1) build.gradle: protobuf-javalite na versão certa (casa com libprotoc 35.1)
p = Path("build.gradle")
content = p.read_text(encoding="utf-8")
old = "implementation 'com.google.protobuf:protobuf-javalite:3.25.5'"
new = "implementation 'com.google.protobuf:protobuf-javalite:4.35.1'"
if new in content:
    skip("protobuf-javalite já está em 4.35.1")
elif old in content:
    content = content.replace(old, new, 1)
    ok("protobuf-javalite atualizado pra 4.35.1")
else:
    fail("não achei a linha do protobuf-javalite 3.25.5 (confere manualmente)")

# 2) build.gradle: mais 3 buildConfigField
fields = [
    ("boolean", "IS_DEBUG_DEVICE", '"false"'),
    ("boolean", "NOTIFICATION_DOTS_ENABLED", '"true"'),
    ("boolean", "QSB_ON_FIRST_SCREEN", '"true"'),
]
anchor = 'versionName "1.0"\n'
added = []
for typ, name, val in fields:
    if f'"{name}"' in content:
        continue
    added.append(f'        buildConfigField "{typ}", "{name}", {val}\n')
if added and anchor in content:
    content = content.replace(anchor, anchor + "".join(added), 1)
    ok(f"buildConfigField adicionados: {', '.join(f[1] for f in fields if f[1] not in content or True)}")
elif not added:
    skip("buildConfigField já existiam")
else:
    fail("não achei 'versionName \"1.0\"' pra ancorar os novos buildConfigField")

p.write_text(content, encoding="utf-8")

# 3) MSDLToken.java: adicionar as 3 constantes que faltam
p = Path("aosp-stubs/com/google/android/msdl/data/model/MSDLToken.java")
content = p.read_text(encoding="utf-8")
if "DRAG_INDICATOR_DISCRETE" in content:
    skip("MSDLToken.java já tem as constantes")
else:
    content = content.replace(
        "public enum MSDLToken {\n}\n",
        "public enum MSDLToken {\n"
        "    DRAG_INDICATOR_DISCRETE,\n"
        "    SWIPE_THRESHOLD_INDICATOR,\n"
        "    TAP_HIGH_EMPHASIS,\n"
        "}\n",
    )
    p.write_text(content, encoding="utf-8")
    ok("MSDLToken.java: 3 constantes adicionadas")

print("\nScript concluído.")
