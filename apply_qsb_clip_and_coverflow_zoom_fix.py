#!/usr/bin/env python3
"""
XaulinXsLauncher3 — fix_qsb_clip_and_coverflow_zoom.py

Corrige 2 bugs reportados:

1) QSB (Barra de busca): slider "Tamanho" da QsbConfigActivity parava de
   ter efeito visual acima de 100%. Causa raiz: o BubbleTextView filho
   crescia normalmente (view.scaleX/scaleY), mas o OseWidgetView pai
   (host do AppWidget da QSB na hotseat) nunca desativava clipChildren/
   clipToPadding — herda o default de ViewGroup (clip=true) do
   AppWidgetHostView do próprio framework Android. Tudo que passava de
   100% do tamanho original da célula era cortado no draw, e por isso o
   slider "não fazia nada" visualmente. Abaixo de 100% funcionava porque
   encolher para dentro dos bounds nunca precisa de clipping.
   Fix: OseWidgetView.init agora desliga clipChildren/clipToPadding
   (mesmo padrão que PendingItemDragHelper já usa para o preview de
   widget arrastado).

2) Efeito de "zoom" do CoverFlow3D (scroll3D) no Workspace continuava
   aparecendo mesmo com o interruptor de giroscópio desligado, "engolindo"
   parte dos ícones/widgets. Causa raiz: o zoom (escala acima de 100% na
   página central, SCALE_BASE=1.18/SCALE_MAX=1.25) era aplicado sempre,
   incondicionalmente — só a leitura do próprio giroscópio (tiltX/tiltY)
   era zerada ao desligar o interruptor, mas o zoom em si não dependia
   disso. Fix: o zoom agora só é liberado quando o interruptor de
   giroscópio (XaulinXsGyroTiltSetting.isEnabled) está LIGADO. Desligado,
   a página central fica travada em 100% (nunca ultrapassa) — rotação,
   perspectiva e alpha do coverflow continuam funcionando normalmente,
   só o componente de escala >100% desaparece. NÃO remove o scroll3D.

Uso:
    python3 apply_qsb_clip_and_coverflow_zoom_fix.py [caminho_do_repo]

Sem argumento, assume que o script está rodando dentro da raiz do repo
(diretório atual). Idempotente: pode rodar múltiplas vezes sem duplicar
nada.
"""
import sys
import hashlib
from pathlib import Path

def sha256(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()

def patch_file(path: Path, patches, label):
    if not path.exists():
        print(f"[ERRO] Arquivo não encontrado: {path}")
        sys.exit(1)

    original = path.read_text(encoding="utf-8")
    content = original
    applied = []
    skipped = []
    conflicts = []

    for marker, old, new in patches:
        if marker in content:
            skipped.append(marker)
            continue
        if old not in content:
            conflicts.append(marker)
            continue
        content = content.replace(old, new, 1)
        applied.append(marker)

    if conflicts:
        print(f"[CONFLITO] {label}: os seguintes patches não bateram com o "
              f"conteúdo esperado (arquivo pode já ter sido editado "
              f"manualmente de outra forma): {conflicts}")
        print(f"           Nenhuma alteração foi salva neste arquivo. "
              f"Resolva manualmente ou peça um novo script.")
        return False

    if applied:
        path.write_text(content, encoding="utf-8")
        print(f"[OK] {label}: aplicado(s) {applied}")
    if skipped:
        print(f"[SKIP] {label}: já aplicado(s) antes {skipped}")

    return True

def main():
    repo_root = Path(sys.argv[1]) if len(sys.argv) > 1 else Path.cwd()

    coverflow_path = repo_root / "src/com/xaulinxs/customizations/cinematic/CinematicCoverFlowEffect.kt"
    oseview_path = repo_root / "src/com/android/launcher3/qsb/OseWidgetView.kt"

    ok = True

    # --- Patch 1: CinematicCoverFlowEffect.kt (zoom atrelado ao giroscópio) ---
    coverflow_patches = [
        (
            "XAULINXS_ZOOM_GATED_BY_GYRO",
            '''    private const val ROTATION_MULTIPLIER = -58f
    private const val ROTATION_MAX = 75f
    private const val SCALE_BASE = 1.18f
    private const val SCALE_FALLOFF = 0.28f
    private const val SCALE_MIN = 0.60f
    private const val SCALE_MAX = 1.25f
    private const val ALPHA_FALLOFF = 0.32f
    private const val ALPHA_MIN = 0.35f''',
            '''    private const val ROTATION_MULTIPLIER = -58f
    private const val ROTATION_MAX = 75f
    private const val SCALE_FALLOFF = 0.28f
    private const val SCALE_MIN = 0.60f

    // XAULINXS_ZOOM_GATED_BY_GYRO: o zoom (escala acima de 100% na página
    // central) só é liberado quando o interruptor de giroscópio está
    // LIGADO. Com o giroscópio desligado, a página central fica travada em
    // 100% (SCALE_BASE_NO_TILT/SCALE_MAX_NO_TILT = 1.0) — o coverflow
    // continua rodando (rotação + perspectiva + alpha), só o componente de
    // escala >100% que desaparece. Isso não depende de tiltX/tiltY em si
    // (que já zeram corretamente ao desligar), e sim do próprio zoom base
    // do efeito, que antes era aplicado sempre, incondicionalmente.
    private const val SCALE_BASE_WITH_TILT = 1.18f
    private const val SCALE_MAX_WITH_TILT = 1.25f
    private const val SCALE_BASE_NO_TILT = 1.0f
    private const val SCALE_MAX_NO_TILT = 1.0f

    private const val ALPHA_FALLOFF = 0.32f
    private const val ALPHA_MIN = 0.35f'''
        ),
        (
            "XAULINXS_ZOOM_GATED_BY_GYRO_APPLY",
            '''        val rotationY = (pageOffset * ROTATION_MULTIPLIER)
            .coerceIn(-ROTATION_MAX, ROTATION_MAX) + (GyroTiltProvider.tiltX * 0.55f)
        val scale = (SCALE_BASE - (absOffset * SCALE_FALLOFF)).coerceIn(SCALE_MIN, SCALE_MAX)
        val alpha = (1f - (absOffset * ALPHA_FALLOFF)).coerceIn(ALPHA_MIN, 1f)''',
            '''        val rotationY = (pageOffset * ROTATION_MULTIPLIER)
            .coerceIn(-ROTATION_MAX, ROTATION_MAX) + (GyroTiltProvider.tiltX * 0.55f)

        // XAULINXS_ZOOM_GATED_BY_GYRO_APPLY: zoom (base/teto >100%) só entra
        // com o giroscópio ligado. Checa o interruptor diretamente (não
        // tiltX/tiltY, que podem estar momentaneamente em 0 mesmo ligado,
        // ex. aparelho perfeitamente nivelado) para a decisão ser sobre o
        // estado da feature, não sobre a leitura instantânea do sensor.
        val gyroEnabled = XaulinXsGyroTiltSetting.isEnabled(page.context)
        val scaleBase = if (gyroEnabled) SCALE_BASE_WITH_TILT else SCALE_BASE_NO_TILT
        val scaleMax = if (gyroEnabled) SCALE_MAX_WITH_TILT else SCALE_MAX_NO_TILT
        val scale = (scaleBase - (absOffset * SCALE_FALLOFF)).coerceIn(SCALE_MIN, scaleMax)

        val alpha = (1f - (absOffset * ALPHA_FALLOFF)).coerceIn(ALPHA_MIN, 1f)'''
        ),
    ]
    if not patch_file(coverflow_path, coverflow_patches, "CinematicCoverFlowEffect.kt"):
        ok = False

    # --- Patch 2: OseWidgetView.kt (clip do slider de tamanho da QSB) ---
    oseview_patches = [
        (
            "XAULINXS_QSB_SIZE_SLIDER_CLIP_FIX",
            '''    internal var autoUpdateTag = true

    init {
        activityContext.appWidgetHolder?.onViewCreationCallback?.accept(this)''',
            '''    internal var autoUpdateTag = true

    init {
        // XaulinXs Customizations — XAULINXS_QSB_SIZE_SLIDER_CLIP_FIX:
        // applyXaulinXsQsbAppearance() escala o BubbleTextView filho
        // (view.scaleX/scaleY) conforme o slider "Tamanho" da
        // QsbConfigActivity. Abaixo de 100% funcionava (o filho encolhe
        // PARA DENTRO dos bounds fixos deste host, nada precisa ser
        // cortado); acima de 100% parecia "travado" no slider — na
        // verdade o filho estava crescendo normalmente, só que o AOSP
        // AppWidgetHostView (ancestral deste ViewGroup, via
        // NavigableAppWidgetHostView) é um ViewGroup comum com
        // clipChildren=true por padrão, então tudo que passava dos
        // bounds originais da célula da hotseat era cortado
        // silenciosamente no draw — visualmente indistinguível de "não
        // mudou nada" acima de 100%. Fix: desliga o clip neste host, o
        // mesmo padrão já usado em PendingItemDragHelper para o preview
        // de widget arrastado (mAppWidgetHostViewPreview.setClipChildren/
        // setClipToPadding(false)).
        clipChildren = false
        clipToPadding = false
        activityContext.appWidgetHolder?.onViewCreationCallback?.accept(this)'''
        ),
    ]
    if not patch_file(oseview_path, oseview_patches, "OseWidgetView.kt"):
        ok = False

    if ok:
        print("\n[SUCESSO] Todos os patches foram aplicados (ou já estavam aplicados).")
        sys.exit(0)
    else:
        print("\n[FALHA] Um ou mais patches tiveram conflito. Veja mensagens acima.")
        sys.exit(1)

if __name__ == "__main__":
    main()
