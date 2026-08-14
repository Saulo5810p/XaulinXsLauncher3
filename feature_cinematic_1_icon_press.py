"""
XaulinXs Customizations — Feature Cinematográfica 1/N: giro/blur/escala ao
tocar nos ícones (BubbleTextView), portado do princípio já validado no
projeto irmão RetroPlayer Compose (cinematicPressVisuals).

Idempotente: pode rodar de novo sem duplicar nada.

USO (Termux, dentro da pasta raiz do projeto XaulinXsLauncher3):
    python3 feature_cinematic_1_icon_press.py
"""
from pathlib import Path

def write_if_absent(path_str, content):
    path = Path(path_str)
    if path.exists():
        print(f"SKIP (já existe): {path_str}")
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")
    print(f"CRIADO: {path_str}")

def replace_once(path_str, old, new, label):
    path = Path(path_str)
    assert path.exists(), f"arquivo não encontrado: {path_str} (rode este script na raiz do projeto)"
    content = path.read_text(encoding="utf-8")
    if new in content:
        print(f"SKIP ({label}): já aplicado")
        return
    assert old in content, f"âncora não encontrada em {path_str} ({label}) — o arquivo pode ter mudado, cola de novo o BubbleTextView.java atual"
    assert content.count(old) == 1, f"âncora aparece mais de uma vez em {path_str} ({label})"
    content = content.replace(old, new)
    path.write_text(content, encoding="utf-8")
    print(f"APLICADO: {label}")


# ---------------------------------------------------------------------------
# 1) Novo arquivo, pacote isolado — nenhum risco pro código AOSP original
# ---------------------------------------------------------------------------
write_if_absent(
    "src/com/xaulinxs/customizations/cinematic/CinematicPressEffects.kt",
    '''/*
 * XaulinXs Customizations — não faz parte do AOSP original.
 *
 * Efeito visual de giro/blur/escala ao tocar em um ícone, portado do
 * princípio já validado no RetroPlayer Compose (cinematicPressVisuals):
 * reage ao evento de toque JÁ CAPTURADO pela view real, nunca intercepta
 * ou consome o toque. O clique/long-press nativo do BubbleTextView
 * continua funcionando exatamente como antes — este efeito só observa.
 *
 * Perfil fixo "INSANE" (sem versão reduzida), mesmo princípio do projeto
 * irmão: giro leve em rotationY, escala de destaque, e blur real via
 * RenderEffect quando o aparelho suporta (API 31+); em API 28-30 o giro
 * e a escala continuam, só o blur é omitido (RenderEffect não existe
 * antes de API 31 — omitir aqui não é redução de efeito, é o hardware
 * mais antigo simplesmente não ter o recurso).
 */
package com.xaulinxs.customizations.cinematic

import android.animation.Animator
import android.animation.AnimatorListenerAdapter
import android.animation.ValueAnimator
import android.animation.ObjectAnimator
import android.animation.AnimatorSet
import android.graphics.RenderEffect
import android.graphics.Shader
import android.os.Build
import android.view.MotionEvent
import android.view.View
import android.view.animation.DecelerateInterpolator
import android.view.animation.OvershootInterpolator

object CinematicPressEffects {

    private const val ROTATION_DEGREES = 12f
    private const val SCALE_PEAK = 1.12f
    private const val BLUR_RADIUS_PX = 6f
    private const val DURATION_DOWN_MS = 90L
    private const val DURATION_UP_MS = 220L

    // Evita empilhar animações concorrentes na mesma view se o usuário
    // tocar rápido várias vezes seguidas.
    private val activeAnimators = HashMap<View, AnimatorSet>()

    /**
     * Chamar a partir do onTouchEvent/onDelegateTouchEvent JÁ EXISTENTE,
     * sempre DEPOIS (ou em paralelo, nunca em vez) de deixar a view real
     * processar o evento. Este método nunca retorna valor e nunca chama
     * event.setAction()/consome o evento — é puramente reativo.
     */
    @JvmStatic
    fun onTouchObserved(target: View, event: MotionEvent) {
        when (event.actionMasked) {
            MotionEvent.ACTION_DOWN -> pressIn(target)
            MotionEvent.ACTION_UP,
            MotionEvent.ACTION_CANCEL -> pressOut(target)
        }
    }

    private fun pressIn(target: View) {
        activeAnimators[target]?.cancel()

        applyBlur(target, BLUR_RADIUS_PX)

        val rotate = ObjectAnimator.ofFloat(target, View.ROTATION_Y, 0f, ROTATION_DEGREES)
        val scaleX = ObjectAnimator.ofFloat(target, View.SCALE_X, target.scaleX, SCALE_PEAK)
        val scaleY = ObjectAnimator.ofFloat(target, View.SCALE_Y, target.scaleY, SCALE_PEAK)

        val set = AnimatorSet()
        set.playTogether(rotate, scaleX, scaleY)
        set.duration = DURATION_DOWN_MS
        set.interpolator = DecelerateInterpolator()
        set.addListener(object : AnimatorListenerAdapter() {
            override fun onAnimationEnd(animation: Animator) {
                activeAnimators.remove(target)
            }
        })
        activeAnimators[target] = set
        set.start()
    }

    private fun pressOut(target: View) {
        activeAnimators[target]?.cancel()

        val rotateBack = ObjectAnimator.ofFloat(target, View.ROTATION_Y, target.rotationY, 0f)
        val scaleBackX = ObjectAnimator.ofFloat(target, View.SCALE_X, target.scaleX, 1f)
        val scaleBackY = ObjectAnimator.ofFloat(target, View.SCALE_Y, target.scaleY, 1f)

        val set = AnimatorSet()
        set.playTogether(rotateBack, scaleBackX, scaleBackY)
        set.duration = DURATION_UP_MS
        set.interpolator = OvershootInterpolator(1.5f)
        set.addListener(object : AnimatorListenerAdapter() {
            override fun onAnimationEnd(animation: Animator) {
                applyBlur(target, 0f)
                activeAnimators.remove(target)
            }
        })
        activeAnimators[target] = set
        set.start()
    }

    private fun applyBlur(target: View, radiusPx: Float) {
        if (Build.VERSION.SDK_INT < Build.VERSION_CODES.S) {
            // RenderEffect não existe antes da API 31 — giro/escala seguem
            // funcionando normalmente, só o blur fica de fora neste
            // aparelho especificamente.
            return
        }
        if (radiusPx <= 0f) {
            target.setRenderEffect(null)
            return
        }
        target.setRenderEffect(
            RenderEffect.createBlurEffect(radiusPx, radiusPx, Shader.TileMode.CLAMP)
        )
    }
}
''',
)

# ---------------------------------------------------------------------------
# 2) Hook de UMA linha no BubbleTextView.java — nunca substitui o
#    comportamento original, só observa em paralelo
# ---------------------------------------------------------------------------
replace_once(
    "src/com/android/launcher3/BubbleTextView.java",
    """    @Override
    public boolean onTouchEvent(MotionEvent event) {
        return onDelegateTouchEvent(event);
    }""",
    """    @Override
    public boolean onTouchEvent(MotionEvent event) {
        // XaulinXs Customizations: efeito visual de giro/blur/escala,
        // puramente observacional — não altera o retorno nem consome
        // o evento. O clique/long-press original continua 100% intacto.
        com.xaulinxs.customizations.cinematic.CinematicPressEffects.onTouchObserved(this, event);
        return onDelegateTouchEvent(event);
    }""",
    "hook onTouchEvent do BubbleTextView (ícones do app drawer e da tela inicial)",
)

print("\\nOK — Feature 1/N (giro/blur/escala ao tocar em ícones) aplicada.")
print("Próximo passo: gradlew assembleDebug pra confirmar que compila limpo antes de eu seguir pro efeito de scroll de páginas.")
