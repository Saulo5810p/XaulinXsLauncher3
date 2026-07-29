from pathlib import Path

def ok(msg): print(f"[OK] {msg}")
def skip(msg): print(f"[SKIP] {msg}")
def fail(msg): print(f"[FALHOU] {msg}")

p = Path("modules/widgetpicker/src/com/android/launcher3/widgetpicker/ui/components/floatingsheet/TitledFloatingSheet.kt")
content = p.read_text(encoding="utf-8")

old_import = "import androidx.compose.animation.core.AnimationSpec\n"
new_import = (
    "import androidx.compose.animation.core.AnimationSpec\n"
    "import androidx.compose.animation.core.Spring\n"
    "import androidx.compose.animation.core.spring\n"
)
if "import androidx.compose.animation.core.spring\n" in content:
    skip("import já presente")
elif old_import in content:
    content = content.replace(old_import, new_import, 1)
    ok("imports adicionados")

old_spec = "val animSpec: AnimationSpec<Float> = MaterialTheme.motionScheme.slowSpatialSpec()\n"
new_spec = (
    "val animSpec: AnimationSpec<Float> =\n"
    "        spring(dampingRatio = Spring.DampingRatioLowBouncy, stiffness = Spring.StiffnessLow)\n"
)
if "spring(dampingRatio = Spring.DampingRatioLowBouncy" in content:
    skip("spring() já aplicado")
elif old_spec in content:
    content = content.replace(old_spec, new_spec, 1)
    ok("motionScheme substituído por spring() estável")

p.write_text(content, encoding="utf-8")
