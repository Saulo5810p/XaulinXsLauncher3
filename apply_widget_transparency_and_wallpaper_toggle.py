#!/usr/bin/env python3
"""
Feature nova: Transparência dos widgets (slider 0-100, categoria "Widget"
das configurações, ao lado do desfoque já existente).

Fix: wallpaper próprio do R's Home3 (XaulinXsWallpaperView) ficava com uma
"borda faltando" mostrando o wallpaper real do sistema por trás. Causa
raiz: onDraw() não desenhava NADA quando getCurrentWallpaper() retornava
null (1º frame antes do arquivo default terminar de ser copiado em
background, ou falha de decode) — a View ficava transparente por
acidente. Fix: nesse caso, pinta um fundo sólido opaco em vez de nada.

Feature nova: interruptor "Usar wallpaper do R's Home3" (categoria "Área
de trabalho" das configurações, junto de "Trocar wallpaper"). Ligado
(padrão) = comportamento atual. Desligado = XaulinXsWallpaperView não
desenha nada, DE PROPÓSITO, deixando o wallpaper real do sistema do
usuário aparecer por trás.

Rode este script na RAIZ do checkout local do repo (mesmo diretório do
gradlew), dentro do Termux.

Idempotente: se tudo já estiver aplicado, o script não faz nada e avisa.
Se encontrar um arquivo já existente com conteúdo DIFERENTE do esperado
(conflito real), aborta esse arquivo sem sobrescrever e avisa no final.
"""
import sys
from pathlib import Path

ROOT = Path(".")

# ---------------------------------------------------------------------------
# Arquivo 1 (novo): XaulinXsWidgetTransparency.kt
# ---------------------------------------------------------------------------
FILE_TRANSPARENCY_OBJ = ROOT / "modules/customizations/src/com/xaulinxs/customizations/blur/XaulinXsWidgetTransparency.kt"
CONTENT_TRANSPARENCY_OBJ = '''/*
 * XaulinXs Customizations — não faz parte do AOSP original.
 *
 * Transparência dos widgets (categoria "Widget" das configurações,
 * slider 0-100, pedida junto do fix do wallpaper próprio do app).
 * Independente do desfoque (XaulinXsWidgetBlur): desfoque usa
 * RenderEffect (borra o conteúdo do widget), transparência usa
 * View.setAlpha (deixa o widget mais "fraco"/see-through). As duas
 * podem ser combinadas sem conflito, pois mexem em propriedades
 * diferentes da View.
 */
package com.xaulinxs.customizations.blur

import android.view.View
import com.android.launcher3.LauncherPrefs
import com.android.launcher3.LauncherPrefs.Companion.backedUpItem

object XaulinXsWidgetTransparency {
    const val MIN_PERCENT = 0
    const val MAX_PERCENT = 100

    private const val KEY_TRANSPARENCY = "xaulinxs_widget_transparency_percent"

    @JvmField
    val WIDGET_TRANSPARENCY_PERCENT = backedUpItem(KEY_TRANSPARENCY, MIN_PERCENT)

    /**
     * Aplica a transparência atual à View do widget. [percent] é
     * "o quanto o widget fica transparente": 0 = totalmente opaco
     * (padrão, sem mudança visual), 100 = totalmente invisível.
     */
    @JvmStatic
    fun applyTo(view: View) {
        val percent =
            LauncherPrefs.get(view.context).get(WIDGET_TRANSPARENCY_PERCENT)
                .coerceIn(MIN_PERCENT, MAX_PERCENT)
        view.alpha = 1f - (percent / 100f)
    }
}
'''

# ---------------------------------------------------------------------------
# Arquivo 2 (novo): WidgetTransparencyPreference.kt
# ---------------------------------------------------------------------------
FILE_TRANSPARENCY_PREF = ROOT / "modules/customizations/src/com/xaulinxs/customizations/settings/WidgetTransparencyPreference.kt"
CONTENT_TRANSPARENCY_PREF = '''/*
 * XaulinXs Customizations — não faz parte do AOSP original.
 */
package com.xaulinxs.customizations.settings

import android.content.Context
import android.util.AttributeSet
import androidx.preference.SeekBarPreference
import com.android.launcher3.LauncherPrefs
import com.xaulinxs.customizations.blur.XaulinXsWidgetTransparency
import com.xaulinxs.customizations.blur.XaulinXsWidgetTransparency.WIDGET_TRANSPARENCY_PERCENT

class WidgetTransparencyPreference @JvmOverloads constructor(
    context: Context,
    attrs: AttributeSet? = null,
) : SeekBarPreference(context, attrs) {

    init {
        isPersistent = false
        min = XaulinXsWidgetTransparency.MIN_PERCENT
        max = XaulinXsWidgetTransparency.MAX_PERCENT
        showSeekBarValue = true
        value = LauncherPrefs.get(context).get(WIDGET_TRANSPARENCY_PERCENT)
        setOnPreferenceChangeListener { _, newValue ->
            LauncherPrefs.get(context).put(WIDGET_TRANSPARENCY_PERCENT, newValue as Int)
            true
        }
    }
}
'''

# ---------------------------------------------------------------------------
# Arquivo 3 (novo): XaulinXsInAppWallpaperSetting.kt
# ---------------------------------------------------------------------------
FILE_WALLPAPER_SETTING = ROOT / "modules/customizations/src/com/xaulinxs/customizations/theme/XaulinXsInAppWallpaperSetting.kt"
CONTENT_WALLPAPER_SETTING = '''/*
 * XaulinXs Customizations — não faz parte do AOSP original.
 *
 * Interruptor pedido pelo usuário: liga/desliga o wallpaper PRÓPRIO do
 * R's Home3 (XaulinXsInAppWallpaper). Ligado (padrão) = comportamento
 * atual, nosso wallpaper desenhado por baixo do Workspace. Desligado =
 * XaulinXsWallpaperView não desenha nada, deixando o wallpaper real do
 * sistema aparecer por trás (ela já é o 1º filho do DragLayer, atrás de
 * tudo, então não precisa esconder a View — só parar de pintar).
 */
package com.xaulinxs.customizations.theme

import com.android.launcher3.LauncherPrefs.Companion.backedUpItem
import com.android.launcher3.util.Executors
import java.util.concurrent.CopyOnWriteArrayList

object XaulinXsInAppWallpaperSetting {

    @JvmField
    val IN_APP_WALLPAPER_ENABLED = backedUpItem("xaulinxs_in_app_wallpaper_enabled", true)

    private val listeners = CopyOnWriteArrayList<() -> Unit>()

    @JvmStatic
    fun addOnChangedListener(listener: () -> Unit) {
        listeners.add(listener)
    }

    @JvmStatic
    fun removeOnChangedListener(listener: () -> Unit) {
        listeners.remove(listener)
    }

    @JvmStatic
    fun notifyChanged() {
        Executors.MAIN_EXECUTOR.execute { listeners.forEach { it() } }
    }
}
'''

# ---------------------------------------------------------------------------
# Arquivo 4 (novo): InAppWallpaperEnabledPreference.kt
# ---------------------------------------------------------------------------
FILE_WALLPAPER_PREF = ROOT / "modules/customizations/src/com/xaulinxs/customizations/settings/InAppWallpaperEnabledPreference.kt"
CONTENT_WALLPAPER_PREF = '''/*
 * XaulinXs Customizations — não faz parte do AOSP original.
 */
package com.xaulinxs.customizations.settings

import android.content.Context
import android.util.AttributeSet
import androidx.preference.SwitchPreference
import com.android.launcher3.LauncherPrefs
import com.xaulinxs.customizations.theme.XaulinXsInAppWallpaperSetting
import com.xaulinxs.customizations.theme.XaulinXsInAppWallpaperSetting.IN_APP_WALLPAPER_ENABLED

class InAppWallpaperEnabledPreference @JvmOverloads constructor(
    context: Context,
    attrs: AttributeSet? = null,
) : SwitchPreference(context, attrs) {

    init {
        isPersistent = false
        isChecked = LauncherPrefs.get(context).get(IN_APP_WALLPAPER_ENABLED)
        setOnPreferenceChangeListener { _, newValue ->
            val enabled = newValue as Boolean
            LauncherPrefs.get(context).put(IN_APP_WALLPAPER_ENABLED, enabled)
            XaulinXsInAppWallpaperSetting.notifyChanged()
            true
        }
    }
}
'''

# ---------------------------------------------------------------------------
# Arquivo 5 (SOBRESCRITO por completo): XaulinXsWallpaperView.kt
# ---------------------------------------------------------------------------
FILE_WALLPAPER_VIEW = ROOT / "modules/customizations/src/com/xaulinxs/customizations/theme/XaulinXsWallpaperView.kt"

OLD_WALLPAPER_VIEW = '''/*
 * XaulinXs Customizations — não faz parte do AOSP original.
 *
 * Desenha o wallpaper PRÓPRIO do R's Home3 (ver XaulinXsInAppWallpaper)
 * como plano de fundo da tela inicial. É colocada como o primeiro filho
 * do DragLayer em res/layout/launcher.xml — ou seja, o mais no fundo
 * possível, atrás até do Workspace — então ela ocupa visualmente o lugar
 * onde o wallpaper real do sistema apareceria, mesmo sem mudar nenhuma
 * flag de transparência de janela.
 *
 * Escala em center-crop (preenche a View inteira, cortando o excesso,
 * sem distorcer) — o mesmo comportamento visual de um wallpaper normal.
 */
package com.xaulinxs.customizations.theme

import android.content.Context
import android.graphics.Canvas
import android.graphics.Matrix
import android.graphics.Paint
import android.graphics.RenderEffect
import android.graphics.Shader
import android.os.Build
import android.util.AttributeSet
import android.view.View

class XaulinXsWallpaperView @JvmOverloads constructor(
    context: Context,
    attrs: AttributeSet? = null,
) : View(context, attrs) {

    private val paint = Paint(Paint.ANTI_ALIAS_FLAG or Paint.FILTER_BITMAP_FLAG)
    private val matrix = Matrix()
    private val onWallpaperChanged: () -> Unit = { post { invalidate() } }
    private val onBlurPrefChanged: () -> Unit = { post { applyBlurEffect() } }

    override fun onAttachedToWindow() {
        super.onAttachedToWindow()
        XaulinXsInAppWallpaper.addOnChangedListener(onWallpaperChanged)
        XaulinXsWorkspaceBlur.addOnChangedListener(onBlurPrefChanged)
        applyBlurEffect()
    }

    override fun onDetachedFromWindow() {
        super.onDetachedFromWindow()
        XaulinXsInAppWallpaper.removeOnChangedListener(onWallpaperChanged)
        XaulinXsWorkspaceBlur.removeOnChangedListener(onBlurPrefChanged)
    }

    /**
     * XaulinXs feature (info.txt/etapa 3: "Área de trabalho [...] -
     * desfoque"): usa View.setRenderEffect (RenderNode blur, API 31+),
     * que roda inteiramente dentro da NOSSA janela — diferente do blur
     * "de vidro fosco" das outras telas (balões/menu de apps/widgets),
     * que depende de cross-window blur do sistema e já está documentado
     * como bloqueado pelo ROM deste aparelho (ver XaulinXsDepthController).
     * Por desenharmos o próprio wallpaper agora (XaulinXsInAppWallpaper),
     * dá pra aplicar esse blur sem depender de nenhuma permissão ou
     * capability do sistema.
     */
    private fun applyBlurEffect() {
        if (Build.VERSION.SDK_INT < Build.VERSION_CODES.S) return
        val radiusPx = XaulinXsWorkspaceBlur.getBlurRadiusPx(context)
        setRenderEffect(
            if (radiusPx > 0f)
                RenderEffect.createBlurEffect(radiusPx, radiusPx, Shader.TileMode.CLAMP)
            else null
        )
    }

    override fun onDraw(canvas: Canvas) {
        super.onDraw(canvas)
        val bitmap = XaulinXsInAppWallpaper.getCurrentWallpaper(context) ?: return
        val viewW = width.toFloat()
        val viewH = height.toFloat()
        if (viewW <= 0f || viewH <= 0f) return

        val bmpW = bitmap.width.toFloat()
        val bmpH = bitmap.height.toFloat()
        // center-crop: escala pelo maior fator entre largura/altura, pra
        // preencher a View inteira, e centraliza o excesso cortado.
        val scale = maxOf(viewW / bmpW, viewH / bmpH)
        val scaledW = bmpW * scale
        val scaledH = bmpH * scale
        matrix.reset()
        matrix.setScale(scale, scale)
        matrix.postTranslate((viewW - scaledW) / 2f, (viewH - scaledH) / 2f)
        canvas.drawBitmap(bitmap, matrix, paint)
    }
}
'''

NEW_WALLPAPER_VIEW = '''/*
 * XaulinXs Customizations — não faz parte do AOSP original.
 *
 * Desenha o wallpaper PRÓPRIO do R's Home3 (ver XaulinXsInAppWallpaper)
 * como plano de fundo da tela inicial. É colocada como o primeiro filho
 * do DragLayer em res/layout/launcher.xml — ou seja, o mais no fundo
 * possível, atrás até do Workspace — então ela ocupa visualmente o lugar
 * onde o wallpaper real do sistema apareceria, mesmo sem mudar nenhuma
 * flag de transparência de janela.
 *
 * Escala em center-crop (preenche a View inteira, cortando o excesso,
 * sem distorcer) — o mesmo comportamento visual de um wallpaper normal.
 *
 * FIX (borda faltando mostrando o wallpaper real do sistema): antes,
 * quando getCurrentWallpaper() retornava null (ex.: no 1º frame, antes
 * do arquivo default terminar de ser copiado em background, ou se o
 * decode falhasse), onDraw simplesmente não desenhava nada — a View
 * ficava com um retângulo/borda transparente vazando o wallpaper real
 * do sistema por trás. Agora, sempre que não há bitmap pronto, a View
 * pinta uma cor de fallback sólida e opaca (nunca fica transparente por
 * acidente).
 *
 * NOVO: interruptor "usar wallpaper do app" (XaulinXsInAppWallpaperSetting).
 * Quando desligado, esse é um caso DELIBERADO de não desenhar nada — a
 * View deixa o wallpaper real do sistema aparecer por trás de propósito,
 * ao contrário do bug acima (que era um null não intencional).
 */
package com.xaulinxs.customizations.theme

import android.content.Context
import android.graphics.Canvas
import android.graphics.Color
import android.graphics.Matrix
import android.graphics.Paint
import android.graphics.RenderEffect
import android.graphics.Shader
import android.os.Build
import android.util.AttributeSet
import android.view.View
import com.android.launcher3.LauncherPrefs

class XaulinXsWallpaperView @JvmOverloads constructor(
    context: Context,
    attrs: AttributeSet? = null,
) : View(context, attrs) {

    private val paint = Paint(Paint.ANTI_ALIAS_FLAG or Paint.FILTER_BITMAP_FLAG)
    private val matrix = Matrix()
    private val onWallpaperChanged: () -> Unit = { post { invalidate() } }
    private val onBlurPrefChanged: () -> Unit = { post { applyBlurEffect() } }
    private val onEnabledPrefChanged: () -> Unit = { post { applyBlurEffect(); invalidate() } }

    override fun onAttachedToWindow() {
        super.onAttachedToWindow()
        XaulinXsInAppWallpaper.addOnChangedListener(onWallpaperChanged)
        XaulinXsWorkspaceBlur.addOnChangedListener(onBlurPrefChanged)
        XaulinXsInAppWallpaperSetting.addOnChangedListener(onEnabledPrefChanged)
        applyBlurEffect()
    }

    override fun onDetachedFromWindow() {
        super.onDetachedFromWindow()
        XaulinXsInAppWallpaper.removeOnChangedListener(onWallpaperChanged)
        XaulinXsWorkspaceBlur.removeOnChangedListener(onBlurPrefChanged)
        XaulinXsInAppWallpaperSetting.removeOnChangedListener(onEnabledPrefChanged)
    }

    /**
     * XaulinXs feature (info.txt/etapa 3: "Área de trabalho [...] -
     * desfoque"): usa View.setRenderEffect (RenderNode blur, API 31+),
     * que roda inteiramente dentro da NOSSA janela — diferente do blur
     * "de vidro fosco" das outras telas (balões/menu de apps/widgets),
     * que depende de cross-window blur do sistema e já está documentado
     * como bloqueado pelo ROM deste aparelho (ver XaulinXsDepthController).
     * Por desenharmos o próprio wallpaper agora (XaulinXsInAppWallpaper),
     * dá pra aplicar esse blur sem depender de nenhuma permissão ou
     * capability do sistema. Quando o interruptor do wallpaper do app
     * está desligado, não há nada nosso pra borrar — pula o blur.
     */
    private fun applyBlurEffect() {
        if (Build.VERSION.SDK_INT < Build.VERSION_CODES.S) return
        if (!isInAppWallpaperEnabled()) {
            setRenderEffect(null)
            return
        }
        val radiusPx = XaulinXsWorkspaceBlur.getBlurRadiusPx(context)
        setRenderEffect(
            if (radiusPx > 0f)
                RenderEffect.createBlurEffect(radiusPx, radiusPx, Shader.TileMode.CLAMP)
            else null
        )
    }

    private fun isInAppWallpaperEnabled(): Boolean =
        LauncherPrefs.get(context).get(XaulinXsInAppWallpaperSetting.IN_APP_WALLPAPER_ENABLED)

    override fun onDraw(canvas: Canvas) {
        super.onDraw(canvas)

        if (!isInAppWallpaperEnabled()) {
            // Interruptor desligado: não pintar nada, de propósito — o
            // wallpaper real do sistema (por trás desta janela) aparece.
            return
        }

        val viewW = width.toFloat()
        val viewH = height.toFloat()
        if (viewW <= 0f || viewH <= 0f) return

        val bitmap = XaulinXsInAppWallpaper.getCurrentWallpaper(context)
        if (bitmap == null) {
            // FIX: sem bitmap pronto ainda (1º frame / decode falhou) —
            // pinta um fundo sólido opaco em vez de deixar a View
            // transparente, pra nunca vazar o wallpaper real do sistema
            // atrás por acidente enquanto o interruptor estiver ligado.
            canvas.drawColor(FALLBACK_COLOR)
            return
        }

        val bmpW = bitmap.width.toFloat()
        val bmpH = bitmap.height.toFloat()
        // center-crop: escala pelo maior fator entre largura/altura, pra
        // preencher a View inteira, e centraliza o excesso cortado.
        val scale = maxOf(viewW / bmpW, viewH / bmpH)
        val scaledW = bmpW * scale
        val scaledH = bmpH * scale
        matrix.reset()
        matrix.setScale(scale, scale)
        matrix.postTranslate((viewW - scaledW) / 2f, (viewH - scaledH) / 2f)
        canvas.drawBitmap(bitmap, matrix, paint)
    }

    private companion object {
        const val FALLBACK_COLOR = Color.BLACK
    }
}
'''

# ---------------------------------------------------------------------------
# Arquivo 6 (editado): LauncherAppWidgetHostView.java — 2 chamadas novas
# ---------------------------------------------------------------------------
FILE_HOST_VIEW = ROOT / "src/com/android/launcher3/widget/LauncherAppWidgetHostView.java"

OLD_HOST_1 = '''        checkIfAutoAdvance();
        com.xaulinxs.customizations.blur.XaulinXsWidgetBlur.applyTo(this);
        // XaulinXs Customizations: força a fonte customizada também'''
NEW_HOST_1 = '''        checkIfAutoAdvance();
        com.xaulinxs.customizations.blur.XaulinXsWidgetBlur.applyTo(this);
        com.xaulinxs.customizations.blur.XaulinXsWidgetTransparency.applyTo(this);
        // XaulinXs Customizations: força a fonte customizada também'''

OLD_HOST_2 = '''        checkIfAutoAdvance();
        com.xaulinxs.customizations.blur.XaulinXsWidgetBlur.applyTo(this);
    }

    @Override
    protected void onDetachedFromWindow() {'''
NEW_HOST_2 = '''        checkIfAutoAdvance();
        com.xaulinxs.customizations.blur.XaulinXsWidgetBlur.applyTo(this);
        com.xaulinxs.customizations.blur.XaulinXsWidgetTransparency.applyTo(this);
    }

    @Override
    protected void onDetachedFromWindow() {'''

# ---------------------------------------------------------------------------
# Arquivo 7 (editado): res/xml/launcher_preferences.xml
# ---------------------------------------------------------------------------
FILE_PREFS_XML = ROOT / "res/xml/launcher_preferences.xml"

OLD_PREFS_WALLPAPER = '''            <Preference
                android:key="xaulinxs_change_wallpaper"
                android:title="@string/xaulinxs_change_wallpaper_title"
                android:summary="@string/xaulinxs_change_wallpaper_summary"
                android:persistent="false">
                <intent
                    android:targetPackage="r.home3"
                    android:targetClass="com.xaulinxs.customizations.settings.WallpaperPickerActivity" />
            </Preference>

            <com.xaulinxs.customizations.settings.WorkspaceBlurPreference'''
NEW_PREFS_WALLPAPER = '''            <Preference
                android:key="xaulinxs_change_wallpaper"
                android:title="@string/xaulinxs_change_wallpaper_title"
                android:summary="@string/xaulinxs_change_wallpaper_summary"
                android:persistent="false">
                <intent
                    android:targetPackage="r.home3"
                    android:targetClass="com.xaulinxs.customizations.settings.WallpaperPickerActivity" />
            </Preference>

            <com.xaulinxs.customizations.settings.InAppWallpaperEnabledPreference
                android:key="xaulinxs_in_app_wallpaper_enabled"
                android:title="@string/xaulinxs_in_app_wallpaper_enabled_title"
                android:summary="@string/xaulinxs_in_app_wallpaper_enabled_summary"
                android:persistent="false" />

            <com.xaulinxs.customizations.settings.WorkspaceBlurPreference'''

OLD_PREFS_WIDGET = '''            <com.xaulinxs.customizations.settings.WidgetBlurPreference
                android:key="xaulinxs_widget_blur_intensity"
                android:title="@string/xaulinxs_widget_blur_title"
                android:summary="@string/xaulinxs_widget_blur_summary"
                android:persistent="false" />

            <!-- TODO: transparência do widget (slider 0-100) pedida no
                 info.txt ainda não existe — só o blur atual. -->

        </PreferenceScreen>'''
NEW_PREFS_WIDGET = '''            <com.xaulinxs.customizations.settings.WidgetBlurPreference
                android:key="xaulinxs_widget_blur_intensity"
                android:title="@string/xaulinxs_widget_blur_title"
                android:summary="@string/xaulinxs_widget_blur_summary"
                android:persistent="false" />

            <com.xaulinxs.customizations.settings.WidgetTransparencyPreference
                android:key="xaulinxs_widget_transparency_percent"
                android:title="@string/xaulinxs_widget_transparency_title"
                android:summary="@string/xaulinxs_widget_transparency_summary"
                android:persistent="false" />

        </PreferenceScreen>'''

# ---------------------------------------------------------------------------
# Arquivo 8 (editado): res/values/xaulinxs_strings.xml
# ---------------------------------------------------------------------------
FILE_STRINGS_XML = ROOT / "res/values/xaulinxs_strings.xml"

OLD_STRINGS = '''    <string name="xaulinxs_workspace_blur_title">Desfoque da tela inicial</string>
    <string name="xaulinxs_workspace_blur_summary">0% = sem desfoque (padrão). Desfoca o wallpaper próprio do launcher atrás dos ícones (precisa de Android 12+)</string>'''
NEW_STRINGS = '''    <string name="xaulinxs_workspace_blur_title">Desfoque da tela inicial</string>
    <string name="xaulinxs_workspace_blur_summary">0% = sem desfoque (padrão). Desfoca o wallpaper próprio do launcher atrás dos ícones (precisa de Android 12+)</string>
    <string name="xaulinxs_in_app_wallpaper_enabled_title">Usar wallpaper do R\\'s Home3</string>
    <string name="xaulinxs_in_app_wallpaper_enabled_summary">Ativado (padrão): usa o wallpaper próprio do launcher. Desativado: mostra o wallpaper do sistema do seu aparelho</string>
    <string name="xaulinxs_widget_transparency_title">Transparência dos widgets</string>
    <string name="xaulinxs_widget_transparency_summary">0% = opaco (padrão). Deixa os widgets mais transparentes, revelando o que está atrás deles</string>'''


def write_new_file(path: Path, content: str, errors: list) -> None:
    if path.exists():
        current = path.read_text(encoding="utf-8")
        if current == content:
            print(f"[=] já aplicado, pulando: {path}")
            return
        errors.append(
            f"[!] CONFLITO: {path} já existe com conteúdo diferente do "
            f"esperado. Não sobrescrevi — verifique manualmente."
        )
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")
    print(f"[+] criado: {path}")


def apply_patch(path: Path, old: str, new: str, label: str, errors: list) -> None:
    if not path.exists():
        errors.append(f"[!] arquivo não encontrado: {path} (patch '{label}')")
        return
    text = path.read_text(encoding="utf-8")
    if new in text:
        print(f"[=] já aplicado, pulando: {label} ({path})")
        return
    if old not in text:
        errors.append(
            f"[!] CONFLITO em {path} (patch '{label}'): trecho esperado não "
            f"encontrado — o arquivo pode ter mudado. Verifique manualmente."
        )
        return
    text = text.replace(old, new, 1)
    path.write_text(text, encoding="utf-8")
    print(f"[+] patch aplicado: {label} ({path})")


def main() -> int:
    if not Path("gradlew").exists():
        print("ERRO: rode este script na raiz do checkout (onde está o gradlew).")
        return 1

    errors: list[str] = []

    write_new_file(FILE_TRANSPARENCY_OBJ, CONTENT_TRANSPARENCY_OBJ, errors)
    write_new_file(FILE_TRANSPARENCY_PREF, CONTENT_TRANSPARENCY_PREF, errors)
    write_new_file(FILE_WALLPAPER_SETTING, CONTENT_WALLPAPER_SETTING, errors)
    write_new_file(FILE_WALLPAPER_PREF, CONTENT_WALLPAPER_PREF, errors)

    # XaulinXsWallpaperView.kt: sobrescrita completa (muitas mudanças
    # espalhadas pelo arquivo) — só aplica se bater exatamente com a
    # versão conhecida ANTES do fix; senão, conflito real.
    if not FILE_WALLPAPER_VIEW.exists():
        errors.append(f"[!] arquivo não encontrado: {FILE_WALLPAPER_VIEW}")
    else:
        current = FILE_WALLPAPER_VIEW.read_text(encoding="utf-8")
        if current == NEW_WALLPAPER_VIEW:
            print(f"[=] já aplicado, pulando: {FILE_WALLPAPER_VIEW}")
        elif current == OLD_WALLPAPER_VIEW:
            FILE_WALLPAPER_VIEW.write_text(NEW_WALLPAPER_VIEW, encoding="utf-8")
            print(f"[+] atualizado: {FILE_WALLPAPER_VIEW}")
        else:
            errors.append(
                f"[!] CONFLITO: {FILE_WALLPAPER_VIEW} tem conteúdo "
                f"diferente do esperado (antes ou depois do fix) — não "
                f"sobrescrevi. Verifique manualmente."
            )

    apply_patch(FILE_HOST_VIEW, OLD_HOST_1, NEW_HOST_1, "updateAppWidget()", errors)
    apply_patch(FILE_HOST_VIEW, OLD_HOST_2, NEW_HOST_2, "onAttachedToWindow()", errors)

    apply_patch(FILE_PREFS_XML, OLD_PREFS_WALLPAPER, NEW_PREFS_WALLPAPER, "categoria workspace", errors)
    apply_patch(FILE_PREFS_XML, OLD_PREFS_WIDGET, NEW_PREFS_WIDGET, "categoria widget", errors)

    apply_patch(FILE_STRINGS_XML, OLD_STRINGS, NEW_STRINGS, "strings novas", errors)

    print()
    if errors:
        print("=== CONCLUÍDO COM AVISOS ===")
        for e in errors:
            print(e)
        return 1

    print("=== TUDO APLICADO COM SUCESSO ===")
    print("Resumo:")
    print("  - Slider de Transparência dos widgets (0-100) na categoria Widget")
    print("  - Fix: wallpaper do app não deixa mais vazar o wallpaper real")
    print("    do sistema quando o bitmap ainda não está pronto")
    print("  - Interruptor 'Usar wallpaper do R's Home3' na categoria Área de trabalho")
    print()
    print("Agora rode: ./gradlew assembleNoQuickstepDebug")
    return 0


if __name__ == "__main__":
    sys.exit(main())
