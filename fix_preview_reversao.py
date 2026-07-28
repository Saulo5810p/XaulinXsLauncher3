from pathlib import Path

def ok(msg): print(f"[OK] {msg}")
def skip(msg): print(f"[SKIP] {msg}")
def fail(msg): print(f"[FALHOU] {msg}")

archive_dir = Path("deferred-appfunctions-widgetpicker")
archive_dir.mkdir(exist_ok=True)

# ============================================================
# 1) Desfazer a restauração dos 2 NoOp modules (não são resolvíveis:
#    dependem de WorkspaceRepository/WorkspaceSpec que exigem androidx.appfunctions
#    de verdade, e de NoOpWidgetPickerComposeWrapper que nem existe no repo)
# ============================================================
undo_moves = [
    ("src/com/android/launcher3/widgetpicker/NoOpWidgetPickerModule.kt",
     archive_dir / "widgetpicker" / "NoOpWidgetPickerModule.kt"),
    ("src/com/android/launcher3/workspacefunctions/NoOpWorkspaceFunctionsModule.kt",
     archive_dir / "workspacefunctions" / "NoOpWorkspaceFunctionsModule.kt"),
]
for src, dst in undo_moves:
    s = Path(src)
    if not s.exists():
        skip(f"{s} já não está em src/ (já desfeito?)")
        continue
    dst.parent.mkdir(parents=True, exist_ok=True)
    s.rename(dst)
    ok(f"{s} -> {dst} (revertido)")

# ============================================================
# 2) Mover PreviewContext.kt, PreviewSurfaceRenderer.java,
#    PreviewLifecycleObserver.kt pra pasta de adiados
# ============================================================
preview_files = [
    "src/com/android/launcher3/preview/PreviewContext.kt",
    "src/com/android/launcher3/preview/PreviewSurfaceRenderer.java",
    "src/com/android/launcher3/preview/PreviewLifecycleObserver.kt",
]
for f in preview_files:
    s = Path(f)
    if not s.exists():
        skip(f"{s} não existe (já movido?)")
        continue
    dst = archive_dir / s.name
    s.rename(dst)
    ok(f"{s} -> {dst}")

# ============================================================
# 3) GridCustomizationsProxy.java — cortar só a fatia de preview
# ============================================================
p = Path("src/com/android/launcher3/graphics/GridCustomizationsProxy.java")
content = p.read_text(encoding="utf-8")

if "// Preview desativado (Fase 2)" in content:
    skip("GridCustomizationsProxy.java já foi ajustado")
else:
    replacements = [
        ('import static com.android.launcher3.preview.PreviewSurfaceRenderer.KEY_BITMAP_GENERATION_DELAY_MS;\n'
         'import static com.android.launcher3.preview.PreviewSurfaceRenderer.KEY_VIEW_HEIGHT;\n'
         'import static com.android.launcher3.preview.PreviewSurfaceRenderer.KEY_VIEW_WIDTH;\n'
         'import static com.android.launcher3.preview.PreviewSurfaceRenderer.MIN_BITMAP_GENERATION_DELAY_MS;\n',
         ''),
        ('import com.android.launcher3.preview.PreviewLifecycleObserver;\n'
         'import com.android.launcher3.preview.PreviewSurfaceRenderer;\n',
         ''),
        ('    // Set of all active previews used to track duplicate memory allocations\n'
         '    private final Set<PreviewLifecycleObserver> mActivePreviews =\n'
         '            Collections.newSetFromMap(new ConcurrentHashMap<>());\n\n',
         '    // Preview desativado (Fase 2) — PreviewSurfaceRenderer/PreviewLifecycleObserver\n'
         '    // adiados junto com widgetpicker/appfunctions.\n\n'),
        ('        lifeCycle.addCloseable(() -> mActivePreviews.forEach(PreviewLifecycleObserver::binderDied));\n',
         ''),
    ]
    for old, new in replacements:
        if old not in content:
            fail(f"padrão não bateu (confere manualmente): {old[:60]!r}...")
            continue
        content = content.replace(old, new, 1)

    # troca o dispatcher call() + os 2 métodos por um único call() no-op
    start_marker = '    @Override\n    public Bundle call(@NonNull String method, String arg, Bundle extras) {\n'
    end_marker = '\n    /**\n     * A WeakReference wrapper around Handler.Callback'
    start_idx = content.find(start_marker)
    end_idx = content.find(end_marker)
    if start_idx == -1 or end_idx == -1:
        fail("não achei os marcadores de início/fim do bloco de preview (confere manualmente)")
    else:
        new_block = (
            '    @Override\n'
            '    public Bundle call(@NonNull String method, String arg, Bundle extras) {\n'
            '        // Preview desativado (Fase 2) — getPreview()/getPreviewBitmap() dependiam\n'
            '        // de PreviewSurfaceRenderer/PreviewLifecycleObserver, adiados por enquanto.\n'
            '        return null;\n'
            '    }\n'
        )
        content = content[:start_idx] + new_block + content[end_idx + 1:]
        ok("GridCustomizationsProxy.java: fatia de preview cortada")

    p.write_text(content, encoding="utf-8")

print("\nScript concluído. Roda:")
print("  ./gradlew --stop && ./gradlew assembleNoQuickstepDebug --stacktrace 2>&1 | tee build_next16.log")
