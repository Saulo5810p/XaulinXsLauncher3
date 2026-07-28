from pathlib import Path

def ok(msg): print(f"[OK] {msg}")
def skip(msg): print(f"[SKIP] {msg}")
def fail(msg): print(f"[FALHOU] {msg}")

# ============================================================
# 1) Mover de volta os 2 NoOp modules + PreviewContext.kt
# ============================================================
moves = [
    ("deferred-appfunctions-widgetpicker/widgetpicker/NoOpWidgetPickerModule.kt",
     "src/com/android/launcher3/widgetpicker/NoOpWidgetPickerModule.kt"),
    ("deferred-appfunctions-widgetpicker/workspacefunctions/NoOpWorkspaceFunctionsModule.kt",
     "src/com/android/launcher3/workspacefunctions/NoOpWorkspaceFunctionsModule.kt"),
    ("deferred-appfunctions-widgetpicker/PreviewContext.kt",
     "src/com/android/launcher3/preview/PreviewContext.kt"),
]
for src, dst in moves:
    s, d = Path(src), Path(dst)
    if d.exists():
        skip(f"{d} já existe")
        continue
    if not s.exists():
        fail(f"{s} não existe")
        continue
    d.parent.mkdir(parents=True, exist_ok=True)
    s.rename(d)
    ok(f"{s} -> {d}")

# ============================================================
# 2) PreviewContext.kt: alias pro systemui.shared.Flags
# ============================================================
p = Path("src/com/android/launcher3/preview/PreviewContext.kt")
if p.exists():
    content = p.read_text(encoding="utf-8")
    if "import com.android.systemui.shared.Flags as SystemUiSharedFlags" in content:
        skip("PreviewContext.kt: já tem o alias")
    elif "import com.android.launcher3.dagger.ApplicationContext" in content:
        content = content.replace(
            "import com.android.launcher3.dagger.ApplicationContext",
            "import com.android.launcher3.dagger.ApplicationContext\n"
            "import com.android.systemui.shared.Flags as SystemUiSharedFlags",
            1,
        )
        content = content.replace(
            "com.android.systemui.shared.Flags.workspaceItemsLabelHidden()",
            "SystemUiSharedFlags.workspaceItemsLabelHidden()",
            1,
        )
        p.write_text(content, encoding="utf-8")
        ok("PreviewContext.kt: alias aplicado")
    else:
        fail("PreviewContext.kt: âncora do import não bateu (confere manualmente)")
else:
    skip("PreviewContext.kt não está em src/ ainda (move não rodou?)")

# ============================================================
# 3) ProvidesInterface.java (annotations do plugin)
# ============================================================
ann_dir = Path("aosp-stubs/com/android/systemui/plugins/annotations")
ann_dir.mkdir(parents=True, exist_ok=True)
ann_file = ann_dir / "ProvidesInterface.java"
if ann_file.exists():
    skip("ProvidesInterface.java já existe")
else:
    ann_file.write_text(
        "package com.android.systemui.plugins.annotations;\n\n"
        "import java.lang.annotation.Retention;\n"
        "import java.lang.annotation.RetentionPolicy;\n\n"
        "/** Stub manual — anotação marcadora, sem uso em runtime aqui. */\n"
        "@Retention(RetentionPolicy.SOURCE)\n"
        "public @interface ProvidesInterface {\n"
        "    String action() default \"\";\n"
        "    int version() default 1;\n"
        "}\n",
        encoding="utf-8",
    )
    ok("ProvidesInterface.java criado")

# ============================================================
# 4) Stubs do com.google.android.msdl (lib não pública do Google)
# ============================================================
msdl_files = {
    "aosp-stubs/com/google/android/msdl/data/model/MSDLToken.java": (
        "package com.google.android.msdl.data.model;\n\n"
        "/**\n"
        " * Stub manual — MSDL (Motion & Sound Design Language) é uma lib do Google\n"
        " * ainda não publicada fora da árvore interna. Vazio por enquanto; conforme\n"
        " * outros arquivos usarem valores específicos (ex: MSDLToken.LONG_PRESS),\n"
        " * o próximo log vai apontar e a gente adiciona aqui.\n"
        " */\n"
        "public enum MSDLToken {\n"
        "}\n"
    ),
    "aosp-stubs/com/google/android/msdl/domain/InteractionProperties.java": (
        "package com.google.android.msdl.domain;\n\n"
        "/** Stub manual — propriedades de interação pro MSDL. */\n"
        "public class InteractionProperties {\n"
        "}\n"
    ),
    "aosp-stubs/com/google/android/msdl/logging/MSDLEvent.java": (
        "package com.google.android.msdl.logging;\n\n"
        "/** Stub manual — evento de histórico do MSDL. */\n"
        "public class MSDLEvent {\n"
        "    @Override\n"
        "    public String toString() {\n"
        "        return \"MSDLEvent(stub)\";\n"
        "    }\n"
        "}\n"
    ),
    "aosp-stubs/com/google/android/msdl/domain/MSDLPlayer.java": (
        "package com.google.android.msdl.domain;\n\n"
        "import android.os.Vibrator;\n\n"
        "import com.google.android.msdl.data.model.MSDLToken;\n"
        "import com.google.android.msdl.logging.MSDLEvent;\n\n"
        "import java.util.Collections;\n"
        "import java.util.List;\n"
        "import java.util.concurrent.Executor;\n\n"
        "/**\n"
        " * Stub manual — MSDLPlayer real ainda não existe fora da árvore interna do\n"
        " * Google. playToken() é no-op; getHistory() sempre volta vazio.\n"
        " */\n"
        "public abstract class MSDLPlayer {\n"
        "    public abstract void playToken(MSDLToken token, InteractionProperties properties);\n"
        "    public abstract List<MSDLEvent> getHistory();\n\n"
        "    public static final Companion Companion = new Companion();\n\n"
        "    public static final class Companion {\n"
        "        public MSDLPlayer createPlayer(\n"
        "                Vibrator vibrator, Executor executor, Object useHapticFeedbackForToken) {\n"
        "            return new MSDLPlayer() {\n"
        "                @Override\n"
        "                public void playToken(MSDLToken token, InteractionProperties properties) {}\n\n"
        "                @Override\n"
        "                public List<MSDLEvent> getHistory() {\n"
        "                    return Collections.emptyList();\n"
        "                }\n"
        "            };\n"
        "        }\n"
        "    }\n"
        "}\n"
    ),
}

for path_str, content in msdl_files.items():
    p = Path(path_str)
    if p.exists():
        skip(f"{p} já existe")
        continue
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(content, encoding="utf-8")
    ok(f"{p} criado")

print("\nScript concluído. Roda:")
print("  ./gradlew --stop && ./gradlew assembleNoQuickstepDebug --stacktrace 2>&1 | tee build_next15.log")
