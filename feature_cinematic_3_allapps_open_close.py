"""
XaulinXs Customizations — Feature Cinematografica 3/N: motion blur +
aberracao cromatica ao abrir/fechar o app drawer (AllApps), MAIS giro 720
em cascata em cada icone ao abrir, portado do perfil NOW_PLAYING_ENTER do
projeto irmao RetroPlayer (NowPlayingScreen.kt).

Reaproveita o mesmo motor CinematicScrollVelocityEffect/CinematicShader ja
usado no scroll de paginas (feature 2) para o motion blur do container do
drawer. O giro em cascata dos icones e um efeito novo (AllAppsIconEnterEffect),
com fisica via SpringAnimation (androidx.dynamicanimation, ja disponivel
no projeto).

Pre-requisito: rode antes os scripts feature_cinematic_1_icon_press.py e
feature_cinematic_2_scroll_motion_blur.py (criam CinematicShader.kt e
CinematicScrollVelocityEffect.kt, reaproveitados aqui).

Idempotente: pode rodar de novo sem duplicar nada.

USO (Termux, dentro da pasta raiz do projeto XaulinXsLauncher3):
    python3 feature_cinematic_3_allapps_open_close.py
"""
from pathlib import Path

def write_if_absent(path_str, content, skip_if=False):
    if skip_if:
        return
    path = Path(path_str)
    if path.exists():
        print(f"SKIP (ja existe): {path_str}")
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")
    print(f"CRIADO: {path_str}")

def replace_once(path_str, old, new, label, required=True):
    path = Path(path_str)
    assert path.exists(), f"arquivo nao encontrado: {path_str} (rode este script na raiz do projeto)"
    content = path.read_text(encoding="utf-8")
    if new in content:
        print(f"SKIP ({label}): ja aplicado")
        return
    if old not in content:
        msg = f"ancora nao encontrada em {path_str} ({label})"
        if required:
            raise AssertionError(msg + " - o arquivo pode ter mudado, cola o arquivo atual")
        print(f"SKIP ({label}): {msg} (provavelmente ja substituida por uma correcao posterior)")
        return
    assert content.count(old) == 1, f"ancora aparece {content.count(old)}x em {path_str} ({label}), precisa ser unica"
    content = content.replace(old, new)
    path.write_text(content, encoding="utf-8")
    print(f"APLICADO: {label}")


assert Path("src/com/xaulinxs/customizations/cinematic/CinematicShader.kt").exists(), (
    "PRE-REQUISITO FALTANDO: rode feature_cinematic_2_scroll_motion_blur.py antes deste script "
    "(ele cria CinematicShader.kt, reaproveitado aqui)."
)
assert Path("src/com/xaulinxs/customizations/cinematic/CinematicScrollVelocityEffect.kt").exists(), (
    "PRE-REQUISITO FALTANDO: rode feature_cinematic_2_scroll_motion_blur.py antes deste script "
    "(ele cria CinematicScrollVelocityEffect.kt, reaproveitado aqui)."
)

# ---------------------------------------------------------------------------
# 1) Estado de coordenacao da janela de cascata de entrada (OBSOLETO desde
#    fix_cinematic_3b_direction_based_cascade.py — este bloco so cria o
#    arquivo se a versao nova (AllAppsCascadeTrigger.kt) ainda nao existir,
#    para nao ressuscitar um arquivo morto ao rodar este script de novo
#    depois do fix 3b ja ter rodado).
# ---------------------------------------------------------------------------
_cascade_trigger_exists = Path("src/com/xaulinxs/customizations/cinematic/AllAppsCascadeTrigger.kt").exists()
if _cascade_trigger_exists:
    print("SKIP: AllAppsCascadeTrigger.kt (versao nova) ja existe — nao recriando AllAppsEnterCascadeState.kt (obsoleto)")

write_if_absent(
    "src/com/xaulinxs/customizations/cinematic/AllAppsEnterCascadeState.kt",
    '''/*
 * XaulinXs Customizations — não faz parte do AOSP original.
 *
 * Coordena o efeito de entrada em cascata (giro 720°, portado do perfil
 * NOW_PLAYING_ENTER do RetroPlayer) nos ícones do app drawer. Existe
 * porque BaseAllAppsAdapter.onBindViewHolder() roda tanto na ABERTURA do
 * drawer quanto durante RECICLAGEM NORMAL DE SCROLL — sem essa distinção,
 * a cascata dispararia toda vez que o RecyclerView reciclasse uma view
 * durante o scroll comum, não só ao abrir. AllAppsTransitionController já
 * sabe exatamente quando a abertura começa (mProgress saindo de 1→0) e
 * ativa a janela aqui; o adapter só consulta isActive() antes de disparar
 * a animação em cada ícone.
 */
package com.xaulinxs.customizations.cinematic

import android.os.SystemClock

object AllAppsEnterCascadeState {

    // Mesma duração do perfil NOW_PLAYING_ENTER do RetroPlayer (750ms) +
    // margem para a cascata terminar de disparar em todos os ícones
    // visíveis antes da janela fechar.
    private const val WINDOW_MS = 900L

    @Volatile
    private var windowStartUptimeMs: Long = -1L

    /** Chamar quando a transição de abertura do drawer começa de verdade. */
    @JvmStatic
    fun startWindow() {
        windowStartUptimeMs = SystemClock.uptimeMillis()
    }

    /** true enquanto a janela de cascata de entrada está ativa. */
    @JvmStatic
    fun isActive(): Boolean {
        val start = windowStartUptimeMs
        if (start < 0L) return false
        return SystemClock.uptimeMillis() - start < WINDOW_MS
    }
}
''',
    skip_if=_cascade_trigger_exists,
)

# ---------------------------------------------------------------------------
# 2) Efeito de giro 720 em cascata por icone
# ---------------------------------------------------------------------------
write_if_absent(
    "src/com/xaulinxs/customizations/cinematic/AllAppsIconEnterEffect.kt",
    '''/*
 * XaulinXs Customizations — não faz parte do AOSP original.
 *
 * Giro 720° + motion blur + aberração cromática na entrada de cada ícone
 * do app drawer, portado do perfil NOW_PLAYING_ENTER do projeto irmão
 * RetroPlayer Compose (NowPlayingScreen.kt): rotationZ decrescendo de
 * maxRotationDegrees até 0 conforme o progresso avança, escala com
 * overshoot senoidal, alpha fade-in, blur/aberração cromática máximos no
 * início e some ao final — mesma matemática, só trocando Animatable+spring
 * do Compose por SpringAnimation (androidx.dynamicanimation), o
 * equivalente nativo View System.
 *
 * Efeito em CASCATA: cada ícone recebe um atraso proporcional à sua
 * posição no grid, criando a sensação de "surgir" em sequência em vez de
 * todos ao mesmo tempo.
 */
package com.xaulinxs.customizations.cinematic

import android.os.Build
import android.view.View
import androidx.dynamicanimation.animation.FloatValueHolder
import androidx.dynamicanimation.animation.SpringAnimation
import androidx.dynamicanimation.animation.SpringForce
import kotlin.math.PI
import kotlin.math.max
import kotlin.math.sin

object AllAppsIconEnterEffect {

    // Mesmos valores do perfil NOW_PLAYING_ENTER (CinematicProfile.kt do
    // RetroPlayer): mass=1.5, stiffness=130, damping=6.5, rotação 720°,
    // overshoot 1.5x, blur/aberração cromática altos.
    private const val MAX_ROTATION_DEGREES = 720f
    private const val OVERSHOOT_SCALE = 1.5f
    private const val BLUR_MULTIPLIER = 3.6f
    private const val CHROMATIC_MULTIPLIER = 3.0f
    private const val VIGNETTE_MULTIPLIER = 1.0f

    // Atraso entre o início da animação de cada ícone consecutivo na
    // cascata — pequeno o bastante para não atrasar demais o último ícone
    // visível, grande o bastante para a sequência ser perceptível.
    private const val STAGGER_DELAY_MS = 18L
    private const val MAX_STAGGER_ITEMS = 30 // evita atraso enorme em grids grandes

    /**
     * Dispara a animação de entrada em cascata no ícone, com atraso
     * proporcional à posição dele no grid do app drawer.
     */
    @JvmStatic
    fun animateEnter(icon: View, positionInGrid: Int) {
        val staggerIndex = positionInGrid.coerceIn(0, MAX_STAGGER_ITEMS)
        val delayMs = staggerIndex * STAGGER_DELAY_MS

        // Estado inicial: escondido/girado, antes da spring rodar.
        icon.rotationZ = MAX_ROTATION_DEGREES
        icon.rotationY = 30f
        icon.scaleX = 0.05f
        icon.scaleY = 0.05f
        icon.alpha = 0f

        icon.postDelayed({ runSpring(icon) }, delayMs)
    }

    private fun runSpring(icon: View) {
        // FloatValueHolder vai de 0 a 1 (não 1000 — mSpring já trabalha
        // bem em escala 0..1, sem necessidade de normalizar depois).
        // Valores de stiffness/dampingRatio escolhidos para reproduzir o
        // "bounce" perceptível do perfil NOW_PLAYING_ENTER do RetroPlayer
        // (overshoot visível, mas sem oscilar demais) — as unidades do
        // SpringForce do Android (stiffness absoluta, dampingRatio 0..1)
        // não correspondem 1:1 às unidades do spring() do Compose, então
        // isso é uma calibração visual equivalente, não uma conversão
        // matemática direta dos mesmos números.
        val holder = FloatValueHolder(0f)
        val spring = SpringAnimation(holder).apply {
            setSpring(
                SpringForce(1f).apply {
                    stiffness = SpringForce.STIFFNESS_LOW
                    dampingRatio = 0.55f // <1 = permite overshoot visível
                }
            )
            setStartVelocity(0f)
            minimumVisibleChange = 0.001f
        }

        spring.addUpdateListener { _, value, _ ->
            applyFrame(icon, value.coerceIn(0f, 1.4f)) // permite overshoot > 1
        }
        spring.addEndListener { _, _, _, _ ->
            applyFrame(icon, 1f)
        }
        spring.start()
    }

    private fun applyFrame(icon: View, progress: Float) {
        val remaining = max(0f, 1f - progress)

        if (remaining <= 0.005f) {
            icon.rotationZ = 0f
            icon.rotationY = 0f
            icon.scaleX = 1f
            icon.scaleY = 1f
            icon.alpha = 1f
            if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.S) {
                icon.setRenderEffect(null)
            }
            return
        }

        icon.rotationZ = remaining * MAX_ROTATION_DEGREES
        icon.rotationY = remaining * 30f

        val enterScale = (1f + (OVERSHOOT_SCALE - 1f) *
                sin(progress * PI.toFloat()) * remaining + (1f - remaining))
            .coerceAtLeast(0.05f)
        icon.scaleX = enterScale
        icon.scaleY = enterScale
        icon.alpha = progress.coerceIn(0f, 1f)

        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.S) {
            val w = icon.width.toFloat().coerceAtLeast(50f)
            val h = icon.height.toFloat().coerceAtLeast(50f)
            val effect = CinematicShader.createCinematicEffect(
                width = w,
                height = h,
                rotationSpeed = remaining * 4.0f,
                scaleFactor = enterScale,
                blurIntensity = remaining * BLUR_MULTIPLIER,
                chromaticShift = remaining * CHROMATIC_MULTIPLIER,
                vignetteIntensity = remaining * VIGNETTE_MULTIPLIER
            )
            icon.setRenderEffect(effect)
        }
    }
}
''',
)

# ---------------------------------------------------------------------------
# 3) Hook no AllAppsTransitionController.java: motion blur do container +
#    disparo da janela de cascata
# ---------------------------------------------------------------------------
replace_once(
    "src/com/android/launcher3/allapps/AllAppsTransitionController.java",
    """    public void setProgress(float progress) {
        if (Float.compare(mProgress, progress) == 0) {
            return;
        }
        mProgress = progress;
        boolean fromBackground =
                mLauncher.getStateManager().getCurrentStableState() == BACKGROUND_APP;
        // Allow apps panel to shift the full screen if coming from another app.
        float shiftRange = fromBackground ? mLauncher.getDeviceProfile().getDeviceProperties().getHeightPx() : mShiftRange;
        getAppsViewProgressTranslationY().setValue(mProgress * shiftRange);
        mLauncher.onAllAppsTransition(1 - progress);

        boolean hasScrim = progress < NAV_BAR_COLOR_FORCE_UPDATE_THRESHOLD
                && mLauncher.getAppsView().getNavBarScrimHeight() > 0;
        mLauncher.getSystemUiController().updateUiState(
                UI_STATE_ALL_APPS, hasScrim ? mNavScrimFlag : 0);
    }""",
    """    public void setProgress(float progress) {
        if (Float.compare(mProgress, progress) == 0) {
            return;
        }
        float previousProgress = mProgress;
        mProgress = progress;
        boolean fromBackground =
                mLauncher.getStateManager().getCurrentStableState() == BACKGROUND_APP;
        // Allow apps panel to shift the full screen if coming from another app.
        float shiftRange = fromBackground ? mLauncher.getDeviceProfile().getDeviceProperties().getHeightPx() : mShiftRange;
        getAppsViewProgressTranslationY().setValue(mProgress * shiftRange);
        mLauncher.onAllAppsTransition(1 - progress);

        // XaulinXs Customizations: motion blur + aberração cromática
        // reagindo à velocidade da transição de abertura/fechamento do app
        // drawer, portado do RetroPlayer. progress*shiftRange já é uma
        // posição em pixels equivalente à do scroll de páginas — mesmo
        // motor (CinematicScrollVelocityEffect) reaproveitado sem mudanças.
        // Puramente observacional, roda depois da translação real acima.
        if (mAppsView != null) {
            com.xaulinxs.customizations.cinematic.CinematicScrollVelocityEffect
                    .onScrollPositionChanged(mAppsView, mProgress * shiftRange);
            if (mProgress <= 0f || mProgress >= 1f) {
                com.xaulinxs.customizations.cinematic.CinematicScrollVelocityEffect
                        .onScrollSettled(mAppsView);
            }
        }
        // XaulinXs Customizations: detecta o INÍCIO real da abertura do
        // drawer (estava fechado/quase fechado, agora começou a abrir) e
        // ativa a janela de cascata de entrada nos ícones — ver
        // AllAppsEnterCascadeState para o motivo de não disparar isso
        // direto no adapter.
        if (previousProgress >= 0.98f && mProgress < 0.98f) {
            com.xaulinxs.customizations.cinematic.AllAppsEnterCascadeState.startWindow();
        }

        boolean hasScrim = progress < NAV_BAR_COLOR_FORCE_UPDATE_THRESHOLD
                && mLauncher.getAppsView().getNavBarScrimHeight() > 0;
        mLauncher.getSystemUiController().updateUiState(
                UI_STATE_ALL_APPS, hasScrim ? mNavScrimFlag : 0);
    }""",
    "hook de motion blur + disparo de cascata em AllAppsTransitionController.setProgress",
    required=False,  # fix_cinematic_3b_direction_based_cascade.py pode ter substituído esta âncora — não é erro
)

# ---------------------------------------------------------------------------
# 4) Hook no BaseAllAppsAdapter.java: dispara o giro em cada icone
# ---------------------------------------------------------------------------
replace_once(
    "src/com/android/launcher3/allapps/BaseAllAppsAdapter.java",
    """                    // Views can still be bounded before the app list is updated hence showing icons
                    // after collapsing.
                    if (privateProfileManager.getCurrentState() == STATE_DISABLED
                            && isPrivateSpaceItem) {
                        adapterItem.decorationInfo = null;
                        icon.setVisibility(GONE);
                    }
                }
                break;
            }
            case VIEW_TYPE_EMPTY_SEARCH: {""",
    """                    // Views can still be bounded before the app list is updated hence showing icons
                    // after collapsing.
                    if (privateProfileManager.getCurrentState() == STATE_DISABLED
                            && isPrivateSpaceItem) {
                        adapterItem.decorationInfo = null;
                        icon.setVisibility(GONE);
                    }
                }
                // XaulinXs Customizations: giro 720° em cascata ao abrir o
                // app drawer, portado do RetroPlayer (perfil
                // NOW_PLAYING_ENTER). Só dispara durante a janela real de
                // abertura do drawer (AllAppsEnterCascadeState) — nunca
                // durante reciclagem normal de scroll, que também passa
                // por aqui. Puramente aditivo: reset()/applyFromApplicationInfo
                // acima já configuraram o ícone normalmente antes disso.
                if (com.xaulinxs.customizations.cinematic.AllAppsEnterCascadeState.isActive()) {
                    com.xaulinxs.customizations.cinematic.AllAppsIconEnterEffect
                            .animateEnter(icon, position);
                }
                break;
            }
            case VIEW_TYPE_EMPTY_SEARCH: {""",
    "hook de giro 720 em cascata em BaseAllAppsAdapter.onBindViewHolder",
    required=False,  # fix_cinematic_3b_direction_based_cascade.py pode ter substituído esta âncora — não é erro
)

print("\nOK - Feature 3/N (motion blur no container do drawer + giro 720 em cascata nos icones) aplicada.")
print("Cobre abertura E fechamento do app drawer.")
print("Proximo passo: ./gradlew assembleNoQuickstepDebug")
