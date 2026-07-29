from pathlib import Path

def ok(msg): print(f"[OK] {msg}")
def skip(msg): print(f"[SKIP] {msg}")
def fail(msg): print(f"[FALHOU] {msg}")

p = Path("build.gradle")
content = p.read_text(encoding="utf-8")

old = "    implementation 'androidx.compose.material3:material3:1.5.0-alpha24'\n"
new = "    implementation 'androidx.compose.material3:material3'\n"

if new in content:
    skip("já no padrão do BOM")
elif old in content:
    content = content.replace(old, new, 1)
    p.write_text(content, encoding="utf-8")
    ok("material3 revertido para o BOM padrão")
else:
    fail("não achei a linha de override")

p2 = Path("modules/widgetpicker/src/com/android/launcher3/widgetpicker/ui/components/floatingsheet/TitledFloatingSheet.kt")
content2 = p2.read_text(encoding="utf-8")

old_import2 = "import androidx.compose.material3.ExperimentalMaterial3ExpressiveApi\n"
old_optin2 = "@OptIn(ExperimentalMaterial3ExpressiveApi::class)\n@Composable\nfun TitledFloatingSheet(\n"
new_optin2 = "@Composable\nfun TitledFloatingSheet(\n"

if old_import2 not in content2 and old_optin2 not in content2:
    skip("já corrigido")
else:
    if old_import2 in content2:
        content2 = content2.replace(old_import2, "", 1)
    if old_optin2 in content2:
        content2 = content2.replace(old_optin2, new_optin2, 1)
    p2.write_text(content2, encoding="utf-8")
    ok("TitledFloatingSheet.kt corrigido")

p3 = Path("modules/widgetpicker/src/com/android/launcher3/widgetpicker/ui/theme/WidgetPickerTextStyles.kt")
content3 = p3.read_text(encoding="utf-8")

old_import3 = "import androidx.compose.material3.ExperimentalMaterial3ExpressiveApi\n"
old_optin3 = "@OptIn(ExperimentalMaterial3ExpressiveApi::class)\n@Composable\nfun defaultWidgetPickerTextStyles() =\n"
new_optin3 = "@Composable\nfun defaultWidgetPickerTextStyles() =\n"

old_style_a = "sheetTitle = MaterialTheme.typography.headlineSmallEmphasized,\n"
new_style_a = "sheetTitle = MaterialTheme.typography.headlineSmall.copy(fontWeight = FontWeight.Medium),\n"

old_style_b = "selectedListHeaderTitle =\n            MaterialTheme.typography.titleMediumEmphasized.copy(fontWeight = FontWeight.Medium),\n"
new_style_b = "selectedListHeaderTitle =\n            MaterialTheme.typography.titleMedium.copy(fontWeight = FontWeight.Bold),\n"

old_style_c = "toolbarSelectedTabLabel = MaterialTheme.typography.labelLargeEmphasized,\n"
new_style_c = "toolbarSelectedTabLabel = MaterialTheme.typography.labelLarge.copy(fontWeight = FontWeight.Bold),\n"

changed3 = False
for old, new in [(old_import3, ""), (old_optin3, new_optin3), (old_style_a, new_style_a), (old_style_b, new_style_b), (old_style_c, new_style_c)]:
    if old in content3:
        content3 = content3.replace(old, new, 1)
        changed3 = True

if changed3:
    p3.write_text(content3, encoding="utf-8")
    ok("WidgetPickerTextStyles.kt corrigido")
else:
    skip("já corrigido")
