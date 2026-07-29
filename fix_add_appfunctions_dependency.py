from pathlib import Path

def ok(msg): print(f"[OK] {msg}")
def skip(msg): print(f"[SKIP] {msg}")
def fail(msg): print(f"[FALHOU] {msg}")

p = Path("build.gradle")
content = p.read_text(encoding="utf-8")

anchor = "    implementation 'com.google.protobuf:protobuf-javalite:4.35.1'\n"
new_deps = (
    "    implementation 'com.google.protobuf:protobuf-javalite:4.35.1'\n"
    "\n"
    "    implementation 'androidx.appfunctions:appfunctions:1.0.0-alpha10'\n"
    "    implementation 'androidx.appfunctions:appfunctions-service:1.0.0-alpha10'\n"
    "    ksp 'androidx.appfunctions:appfunctions-compiler:1.0.0-alpha10'\n"
)

if "androidx.appfunctions:appfunctions:" in content:
    skip("dependência já presente")
elif anchor in content:
    content = content.replace(anchor, new_deps, 1)
    p.write_text(content, encoding="utf-8")
    ok("dependências androidx.appfunctions adicionadas")
else:
    fail("não achei o ponto de ancoragem")

stub = Path("aosp-stubs/androidx/appfunctions/AppFunctionSerializable.java")
if stub.exists():
    stub.unlink()
    ok(f"stub manual removido: {stub}")
else:
    skip("stub manual já não existe")
