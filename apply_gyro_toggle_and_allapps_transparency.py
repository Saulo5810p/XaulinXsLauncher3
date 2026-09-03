#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
XaulinXs Customizations — script de entrega.

Aplica 3 mudanças no repo (rode a partir da RAIZ do checkout, ex.:
~/XaulinXsLauncher3):

  1) Interruptor liga/desliga para o tilt por giroscópio (Workspace
     coverflow), em "XaulinXs Customizations" -> "Inclinação por
     giroscópio".

  2) Transparência do menu de apps SEM blur — novo interruptor +
     slider 0-100% em "XaulinXs Customizations" -> "Transparência do
     menu de apps (sem blur)". Só tem efeito quando "Fundo desfocado
     no menu de apps" (blur) está DESATIVADO; a feature antiga de
     transparência (SCRIM_OPACITY_PERCENT) continua existindo mas foi
     renomeada nas strings para deixar claro que é a variante COM
     blur/tonalidade do wallpaper.

  3) Fix da QSB: cor/tamanho/largura/transparência da barra de busca
     agora atualizam na hora ao mudar em "Configurar barra de busca",
     sem precisar de "Forçar parada". Causa raiz: a config só era
     aplicada uma vez, na inflação da view.

Idempotente: pode rodar várias vezes seguidas sem duplicar nada. Cada
arquivo novo é pulado se já existir com o conteúdo esperado (hash
SHA256); cada patch em arquivo existente é pulado se o marcador dele já
estiver presente.

Uso:
    python3 apply_gyro_toggle_and_allapps_transparency.py
"""

import hashlib
import re
import sys
from pathlib import Path

ROOT = Path.cwd()


def fail(msg: str) -> None:
    print(f"[ERRO] {msg}")
    sys.exit(1)


def ok(msg: str) -> None:
    print(f"[OK]   {msg}")


def skip(msg: str) -> None:
    print(f"[SKIP] {msg}")


def sha256(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def write_new_file(rel_path: str, content: str) -> None:
    """Cria um arquivo novo. Se já existir com o MESMO conteúdo, pula
    (idempotente). Se já existir com conteúdo DIFERENTE, aborta sem
    sobrescrever (conflito real precisa de decisão manual)."""
    path = ROOT / rel_path
    if path.exists():
        existing = path.read_text(encoding="utf-8")
        if sha256(existing) == sha256(content):
            skip(f"{rel_path} (já existe, idêntico)")
            return
        fail(
            f"{rel_path} já existe com conteúdo DIFERENTE do esperado — "
            "não vou sobrescrever. Verifique manualmente antes de rodar de novo."
        )
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")
    ok(f"{rel_path} (criado)")


def patch_file(rel_path: str, marker: str, old: str, new: str, label: str) -> None:
    """Aplica um patch old->new num arquivo existente. Se `marker` já
    estiver no arquivo, considera já aplicado e pula. Se `old` não for
    encontrado (nem `marker`), aborta — sinal de que o arquivo mudou
    e o patch precisa ser revisado."""
    path = ROOT / rel_path
    if not path.exists():
        fail(f"{rel_path} não encontrado — checkout inesperado, abortando.")
    content = path.read_text(encoding="utf-8")
    if marker in content:
        skip(f"{label} (marcador já presente em {rel_path})")
        return
    count = content.count(old)
    if count == 0:
        fail(
            f"{label}: trecho esperado não encontrado em {rel_path}. "
            "O arquivo pode ter mudado desde que este script foi gerado — "
            "não vou aplicar um patch às cegas."
        )
    if count > 1:
        fail(
            f"{label}: trecho esperado aparece {count} vezes em {rel_path} "
            "(deveria ser único) — abortando para não aplicar no lugar errado."
        )
    path.write_text(content.replace(old, new, 1), encoding="utf-8")
    ok(f"{label} ({rel_path})")


def append_line_in_xml(rel_path: str, marker: str, old: str, new: str, label: str) -> None:
    patch_file(rel_path, marker, old, new, label)


# ---------------------------------------------------------------------------
# 1) Novos arquivos — Feature 1 (toggle giroscópio) e Feature 2 (transparência)
# ---------------------------------------------------------------------------

GYRO_TILT_SETTING_KT = '''/*
 * XaulinXs Customizations — não faz parte do AOSP original.
 *
 * Interruptor liga/desliga do tilt por giroscópio (GyroTiltProvider +
 * uso em CinematicCoverFlowEffect). Segue o mesmo padrão de preferência
 * "backed up" já usado por POPUP_BLUR_ENABLED/THEMED_SCRIM_ENABLED.
 */
package com.xaulinxs.customizations.cinematic

import android.content.Context
import com.android.launcher3.LauncherPrefs
import com.android.launcher3.LauncherPrefs.Companion.backedUpItem

object XaulinXsGyroTiltSetting {
    private const val KEY_ENABLED = "xaulinxs_gyro_tilt_enabled"

    @JvmField
    val GYRO_TILT_ENABLED = backedUpItem(KEY_ENABLED, true)

    @JvmStatic
    fun isEnabled(context: Context): Boolean =
        LauncherPrefs.get(context).get(GYRO_TILT_ENABLED)
}

// XAULINXS_GYRO_TILT_SETTING_FILE
'''

GYRO_TILT_PREFERENCE_KT = '''/*
 * XaulinXs Customizations — não faz parte do AOSP original.
 */
package com.xaulinxs.customizations.settings

import android.content.Context
import android.util.AttributeSet
import androidx.preference.SwitchPreference
import com.android.launcher3.LauncherPrefs
import com.xaulinxs.customizations.cinematic.GyroTiltProvider
import com.xaulinxs.customizations.cinematic.XaulinXsGyroTiltSetting.GYRO_TILT_ENABLED

class GyroTiltPreference @JvmOverloads constructor(
    context: Context,
    attrs: AttributeSet? = null,
) : SwitchPreference(context, attrs) {

    init {
        isPersistent = false
        isChecked = LauncherPrefs.get(context).get(GYRO_TILT_ENABLED)
        setOnPreferenceChangeListener { _, newValue ->
            val enabled = newValue as Boolean
            LauncherPrefs.get(context).put(GYRO_TILT_ENABLED, enabled)
            GyroTiltProvider.notifySettingChanged(context, enabled)
            true
        }
    }
}

// XAULINXS_GYRO_TILT_PREFERENCE_FILE
'''

ALLAPPS_TRANSPARENCY_ENABLED_PREFERENCE_KT = '''/*
 * XaulinXs Customizations — não faz parte do AOSP original.
 */
package com.xaulinxs.customizations.settings

import android.content.Context
import android.util.AttributeSet
import androidx.preference.SwitchPreference
import com.android.launcher3.LauncherPrefs
import com.xaulinxs.customizations.theme.ALLAPPS_TRANSPARENCY_ENABLED
import com.xaulinxs.customizations.theme.XaulinXsAllAppsTransparencyRedraw

class AllAppsTransparencyEnabledPreference @JvmOverloads constructor(
    context: Context,
    attrs: AttributeSet? = null,
) : SwitchPreference(context, attrs) {

    init {
        isPersistent = false
        isChecked = LauncherPrefs.get(context).get(ALLAPPS_TRANSPARENCY_ENABLED)
        setOnPreferenceChangeListener { _, newValue ->
            LauncherPrefs.get(context).put(ALLAPPS_TRANSPARENCY_ENABLED, newValue as Boolean)
            XaulinXsAllAppsTransparencyRedraw.requestRedraw(context)
            true
        }
    }
}

// XAULINXS_ALLAPPS_TRANSPARENCY_ENABLED_PREFERENCE_FILE
'''

ALLAPPS_TRANSPARENCY_PERCENT_PREFERENCE_KT = '''/*
 * XaulinXs Customizations — não faz parte do AOSP original.
 */
package com.xaulinxs.customizations.settings

import android.content.Context
import android.util.AttributeSet
import androidx.preference.SeekBarPreference
import com.android.launcher3.LauncherPrefs
import com.xaulinxs.customizations.theme.ALLAPPS_TRANSPARENCY_MAX_PERCENT
import com.xaulinxs.customizations.theme.ALLAPPS_TRANSPARENCY_MIN_PERCENT
import com.xaulinxs.customizations.theme.ALLAPPS_TRANSPARENCY_PERCENT
import com.xaulinxs.customizations.theme.XaulinXsAllAppsTransparencyRedraw

class AllAppsTransparencyPercentPreference @JvmOverloads constructor(
    context: Context,
    attrs: AttributeSet? = null,
) : SeekBarPreference(context, attrs) {

    init {
        isPersistent = false
        min = ALLAPPS_TRANSPARENCY_MIN_PERCENT
        max = ALLAPPS_TRANSPARENCY_MAX_PERCENT
        showSeekBarValue = true
        value = LauncherPrefs.get(context).get(ALLAPPS_TRANSPARENCY_PERCENT)
        setOnPreferenceChangeListener { _, newValue ->
            LauncherPrefs.get(context).put(ALLAPPS_TRANSPARENCY_PERCENT, newValue as Int)
            XaulinXsAllAppsTransparencyRedraw.requestRedraw(context)
            true
        }
    }
}

// XAULINXS_ALLAPPS_TRANSPARENCY_PERCENT_PREFERENCE_FILE
'''

ALLAPPS_TRANSPARENCY_REDRAW_KT = '''/*
 * XaulinXs Customizations — não faz parte do AOSP original.
 *
 * getWorkspaceScrimColor() só é recalculado quando o Launcher entra no
 * estado ALL_APPS (WorkspaceStateTransitionAnimation.setState) — é o
 * mesmo comportamento documentado em ScrimOpacityPreference para
 * SCRIM_OPACITY_PERCENT ("a cor do véu é recalculada do zero toda vez
 * que o App Drawer abre"). Isso já é suficiente para o caso normal: o
 * usuário muda o slider, fecha as configs, abre o menu de apps e vê o
 * valor novo. Este helper cobre só o caso em que o menu de apps já
 * está aberto/em transição enquanto a config muda — força um
 * invalidate() pontual no ScrimView pra refletir na hora.
 */
package com.xaulinxs.customizations.theme

import android.content.Context
import com.android.launcher3.Launcher

object XaulinXsAllAppsTransparencyRedraw {
    @JvmStatic
    fun requestRedraw(context: Context) {
        try {
            // reapplyState() força o StateManager a rodar de novo o setScrim()
            // do estado atual, que é o que efetivamente chama
            // getWorkspaceScrimColor(mLauncher) e empurra a cor recalculada
            // pro ScrimView — invalidate() sozinho não bastaria, pois só
            // redesenha com a cor JÁ setada, sem recalculá-la.
            Launcher.getLauncher(context)?.stateManager?.reapplyState()
        } catch (_: Exception) {
            // Contexto pode não ter um Launcher associado (ex.: preference
            // aberta sem o launcher em memória) — sem problema, o valor
            // já foi salvo e será aplicado na próxima vez que o menu de
            // apps abrir de verdade (getWorkspaceScrimColor recalcula do zero).
        }
    }
}

// XAULINXS_ALLAPPS_TRANSPARENCY_REDRAW_FILE
'''


def apply_new_files() -> None:
    write_new_file(
        "src/com/xaulinxs/customizations/cinematic/XaulinXsGyroTiltSetting.kt",
        GYRO_TILT_SETTING_KT,
    )
    write_new_file(
        "modules/customizations/src/com/xaulinxs/customizations/settings/GyroTiltPreference.kt",
        GYRO_TILT_PREFERENCE_KT,
    )
    write_new_file(
        "modules/customizations/src/com/xaulinxs/customizations/settings/"
        "AllAppsTransparencyEnabledPreference.kt",
        ALLAPPS_TRANSPARENCY_ENABLED_PREFERENCE_KT,
    )
    write_new_file(
        "modules/customizations/src/com/xaulinxs/customizations/settings/"
        "AllAppsTransparencyPercentPreference.kt",
        ALLAPPS_TRANSPARENCY_PERCENT_PREFERENCE_KT,
    )
    write_new_file(
        "modules/customizations/src/com/xaulinxs/customizations/theme/"
        "XaulinXsAllAppsTransparencyRedraw.kt",
        ALLAPPS_TRANSPARENCY_REDRAW_KT,
    )


# ---------------------------------------------------------------------------
# 2) Patches em arquivos existentes
# ---------------------------------------------------------------------------

def apply_gyro_provider_patch() -> None:
    rel = "src/com/xaulinxs/customizations/cinematic/GyroTiltProvider.kt"
    marker = "XAULINXS_GYRO_PROVIDER_TOGGLE_SUPPORT"

    old_subscribe_and_register = '''    /**
     * Inscreve uma View para manter o sensor de giroscópio ativo enquanto
     * ela estiver anexada à janela. Chamar uma vez, tipicamente em
     * onAttachedToWindow/init da View interessada (Workspace, AllApps).
     * Seguro chamar múltiplas vezes para a mesma View.
     */
    @JvmStatic
    fun subscribe(view: View) {
        view.removeOnAttachStateChangeListener(attachListener)
        view.addOnAttachStateChangeListener(attachListener)
        if (view.isAttachedToWindow) {
            subscribedViews.add(view)
            ensureRegistered(view.context)
        }
    }

    private fun ensureRegistered(context: Context) {
        if (listenerRegistered) return
        val mgr = context.applicationContext
            .getSystemService(Context.SENSOR_SERVICE) as? SensorManager ?: return
        val sensor = mgr.getDefaultSensor(Sensor.TYPE_ACCELEROMETER) ?: return
        sensorManager = mgr
        accelerometer = sensor
        mgr.registerListener(sensorListener, sensor, SensorManager.SENSOR_DELAY_UI)
        listenerRegistered = true
    }'''

    new_subscribe_and_register = '''    /**
     * Inscreve uma View para manter o sensor de giroscópio ativo enquanto
     * ela estiver anexada à janela. Chamar uma vez, tipicamente em
     * onAttachedToWindow/init da View interessada (Workspace, AllApps).
     * Seguro chamar múltiplas vezes para a mesma View.
     *
     * Se o interruptor XaulinXsGyroTiltSetting estiver desativado, a
     * inscrição é ignorada (sensor nunca é registrado, tiltX/tiltY
     * permanecem 0) — ver notifySettingChanged() para o caso do usuário
     * desativar com o sensor já em uso.
     */
    @JvmStatic
    fun subscribe(view: View) {
        view.removeOnAttachStateChangeListener(attachListener)
        view.addOnAttachStateChangeListener(attachListener)
        if (view.isAttachedToWindow) {
            subscribedViews.add(view)
            ensureRegistered(view.context)
        }
    }

    /**
     * Chamar quando o interruptor de configurações mudar em runtime
     * (XaulinXsGyroTiltPreference). Se foi desativado, desregistra o
     * sensor imediatamente mesmo com views ainda anexadas; se foi
     * reativado, tenta re-registrar usando qualquer view já inscrita.
     */
    @JvmStatic
    fun notifySettingChanged(context: Context, enabled: Boolean) {
        if (!enabled) {
            unregister()
            return
        }
        val anyView = subscribedViews.firstOrNull() ?: return
        ensureRegistered(anyView.context)
    }

    private fun ensureRegistered(context: Context) {
        if (listenerRegistered) return
        if (!com.xaulinxs.customizations.cinematic.XaulinXsGyroTiltSetting.isEnabled(context)) return
        val mgr = context.applicationContext
            .getSystemService(Context.SENSOR_SERVICE) as? SensorManager ?: return
        val sensor = mgr.getDefaultSensor(Sensor.TYPE_ACCELEROMETER) ?: return
        sensorManager = mgr
        accelerometer = sensor
        mgr.registerListener(sensorListener, sensor, SensorManager.SENSOR_DELAY_UI)
        listenerRegistered = true
    }'''

    patch_file(
        rel, marker, old_subscribe_and_register, new_subscribe_and_register,
        "GyroTiltProvider: subscribe()/ensureRegistered() respeitando o toggle",
    )

    # Marcador final (só é gravado se o patch acima realmente rodou;
    # se o patch acima foi SKIP por já ter o marker em outro lugar, este
    # segundo patch_file também vira SKIP porque já vai achar o marker).
    old_tail = "// XAULINXS_GYRO_PROVIDER_FILE"
    new_tail = "// XAULINXS_GYRO_PROVIDER_FILE\n// XAULINXS_GYRO_PROVIDER_TOGGLE_SUPPORT"
    patch_file(rel, marker, old_tail, new_tail, "GyroTiltProvider: marcador final")


def apply_wallpaper_scrim_helper_patch() -> None:
    rel = "modules/customizations/src/com/xaulinxs/customizations/theme/WallpaperScrimHelper.kt"
    marker = "XAULINXS_ALLAPPS_TRANSPARENCY_V2_FILE"

    old = '''package com.xaulinxs.customizations.theme

import android.content.Context
import androidx.core.graphics.ColorUtils
import com.android.launcher3.LauncherPrefs
import com.android.launcher3.Utilities
import com.android.launcher3.util.WallpaperColorHints
import com.xaulinxs.customizations.settings.ThemedScrimPreference.Companion.THEMED_SCRIM_ENABLED
import com.xaulinxs.customizations.theme.XaulinXsManualColor
import com.android.launcher3.LauncherPrefs.Companion.backedUpItem

private const val SCRIM_ALPHA_LIGHT = 140
private const val SCRIM_ALPHA_DARK = 160
private const val SHADE_RATIO_LIGHT = 0.15f
private const val SHADE_RATIO_DARK = 0.55f

// XaulinXs Customizations: percentual de opacidade do véu escolhido pelo
// usuário no slider "Transparência do fundo do menu de apps". 100%
// preserva o alpha original (SCRIM_ALPHA_LIGHT/DARK acima); 0% deixa o véu
// totalmente transparente (só o blur real do XaulinXsDepthController fica visível).
const val SCRIM_OPACITY_MIN_PERCENT = 0
const val SCRIM_OPACITY_MAX_PERCENT = 100
private const val KEY_SCRIM_OPACITY_PERCENT = "xaulinxs_scrim_opacity_percent"
val SCRIM_OPACITY_PERCENT = backedUpItem(KEY_SCRIM_OPACITY_PERCENT, SCRIM_OPACITY_MAX_PERCENT)

object WallpaperScrimHelper {

    @JvmStatic
    fun getScrimColorIfEnabled(context: Context): Int? {
        if (!LauncherPrefs.get(context).get(THEMED_SCRIM_ENABLED)) return null
        return getScrimColor(context)
    }

    fun getScrimColor(context: Context): Int? {
        // XaulinXs Customizations: cor manual (se ativada) tem prioridade sobre a do wallpaper.
        val primaryColor = XaulinXsManualColor.getBaseColorIfEnabled(context)
            ?: WallpaperColorHints.get(context).colors?.primaryColor?.toArgb()
            ?: return null
        val isDark = Utilities.isDarkTheme(context)
        val shaded =
            if (isDark) {
                ColorUtils.blendARGB(primaryColor, android.graphics.Color.BLACK, SHADE_RATIO_DARK)
            } else {
                ColorUtils.blendARGB(primaryColor, android.graphics.Color.WHITE, SHADE_RATIO_LIGHT)
            }
        val baseAlpha = if (isDark) SCRIM_ALPHA_DARK else SCRIM_ALPHA_LIGHT
        // XaulinXs Customizations: escala o alpha base pelo percentual do slider.
        val opacityPercent = LauncherPrefs.get(context).get(SCRIM_OPACITY_PERCENT)
            .coerceIn(SCRIM_OPACITY_MIN_PERCENT, SCRIM_OPACITY_MAX_PERCENT)
        val alpha = (baseAlpha * opacityPercent / 100).coerceIn(0, 255)
        return ColorUtils.setAlphaComponent(shaded, alpha)
    }
}'''

    new = '''package com.xaulinxs.customizations.theme

import android.content.Context
import androidx.core.graphics.ColorUtils
import com.android.launcher3.LauncherPrefs
import com.android.launcher3.Utilities
import com.android.launcher3.util.WallpaperColorHints
import com.xaulinxs.customizations.settings.ThemedScrimPreference.Companion.THEMED_SCRIM_ENABLED
import com.xaulinxs.customizations.theme.XaulinXsManualColor
import com.android.launcher3.LauncherPrefs.Companion.backedUpItem

private const val SCRIM_ALPHA_LIGHT = 140
private const val SCRIM_ALPHA_DARK = 160
private const val SHADE_RATIO_LIGHT = 0.15f
private const val SHADE_RATIO_DARK = 0.55f

// XaulinXs Customizations: percentual de opacidade do véu escolhido pelo
// usuário no slider "Transparência do fundo do menu de apps". 100%
// preserva o alpha original (SCRIM_ALPHA_LIGHT/DARK acima); 0% deixa o véu
// totalmente transparente (só o blur real do XaulinXsDepthController fica visível).
const val SCRIM_OPACITY_MIN_PERCENT = 0
const val SCRIM_OPACITY_MAX_PERCENT = 100
private const val KEY_SCRIM_OPACITY_PERCENT = "xaulinxs_scrim_opacity_percent"
val SCRIM_OPACITY_PERCENT = backedUpItem(KEY_SCRIM_OPACITY_PERCENT, SCRIM_OPACITY_MAX_PERCENT)

// XaulinXs Customizations: NOVA transparência do menu de apps (agosto/2026),
// feature separada de SCRIM_OPACITY_PERCENT acima. A diferença é a condição
// de ativação: SCRIM_OPACITY_PERCENT só tem efeito quando o blur do drawer
// (THEMED_SCRIM_ENABLED) está LIGADO — ver getScrimColorIfEnabled() abaixo,
// que corta com "return null" se o blur estiver desligado. Essa nova
// feature faz o oposto por pedido explícito do usuário: só tem efeito
// quando o blur está DESLIGADO, revelando a Workspace por trás do drawer
// sem nenhum desfoque. 0% no slider = totalmente transparente (workspace
// 100% visível); 100% = opaco.
const val ALLAPPS_TRANSPARENCY_MIN_PERCENT = 0
const val ALLAPPS_TRANSPARENCY_MAX_PERCENT = 100
private const val KEY_ALLAPPS_TRANSPARENCY_ENABLED = "xaulinxs_allapps_transparency_enabled"
private const val KEY_ALLAPPS_TRANSPARENCY_PERCENT = "xaulinxs_allapps_transparency_percent"
val ALLAPPS_TRANSPARENCY_ENABLED = backedUpItem(KEY_ALLAPPS_TRANSPARENCY_ENABLED, false)
val ALLAPPS_TRANSPARENCY_PERCENT =
    backedUpItem(KEY_ALLAPPS_TRANSPARENCY_PERCENT, ALLAPPS_TRANSPARENCY_MAX_PERCENT)

object WallpaperScrimHelper {

    @JvmStatic
    fun getScrimColorIfEnabled(context: Context): Int? {
        val prefs = LauncherPrefs.get(context)
        if (prefs.get(THEMED_SCRIM_ENABLED)) return getScrimColor(context)
        // Blur desligado: se a nova transparência estiver ativada, ela
        // assume o fundo do drawer no lugar do véu temático do wallpaper —
        // cor sólida de fundo do tema, com alpha controlado pelo slider,
        // sem nenhum desfoque envolvido.
        if (prefs.get(ALLAPPS_TRANSPARENCY_ENABLED)) return getPlainTransparentScrimColor(context)
        return null
    }

    fun getScrimColor(context: Context): Int? {
        // XaulinXs Customizations: cor manual (se ativada) tem prioridade sobre a do wallpaper.
        val primaryColor = XaulinXsManualColor.getBaseColorIfEnabled(context)
            ?: WallpaperColorHints.get(context).colors?.primaryColor?.toArgb()
            ?: return null
        val isDark = Utilities.isDarkTheme(context)
        val shaded =
            if (isDark) {
                ColorUtils.blendARGB(primaryColor, android.graphics.Color.BLACK, SHADE_RATIO_DARK)
            } else {
                ColorUtils.blendARGB(primaryColor, android.graphics.Color.WHITE, SHADE_RATIO_LIGHT)
            }
        val baseAlpha = if (isDark) SCRIM_ALPHA_DARK else SCRIM_ALPHA_LIGHT
        // XaulinXs Customizations: escala o alpha base pelo percentual do slider.
        val opacityPercent = LauncherPrefs.get(context).get(SCRIM_OPACITY_PERCENT)
            .coerceIn(SCRIM_OPACITY_MIN_PERCENT, SCRIM_OPACITY_MAX_PERCENT)
        val alpha = (baseAlpha * opacityPercent / 100).coerceIn(0, 255)
        return ColorUtils.setAlphaComponent(shaded, alpha)
    }

    /**
     * Cor de fundo "lisa" (sem blur) para a nova transparência do menu de
     * apps: reaproveita a cor de fundo padrão do tema do sistema (mesma
     * usada pelo AOSP original em getWorkspaceScrimColor quando nenhuma
     * customização está ativa) e só ajusta o alpha pelo percentual do
     * slider — nada de tonalidade extraída do wallpaper nem shading, para
     * não ser confundida com o véu temático de SCRIM_OPACITY_PERCENT.
     */
    private fun getPlainTransparentScrimColor(context: Context): Int {
        val baseColor = com.android.launcher3.util.Themes.getAttrColor(
            context, com.android.launcher3.R.attr.allAppsScrimColor
        )
        val percent = LauncherPrefs.get(context).get(ALLAPPS_TRANSPARENCY_PERCENT)
            .coerceIn(ALLAPPS_TRANSPARENCY_MIN_PERCENT, ALLAPPS_TRANSPARENCY_MAX_PERCENT)
        val baseAlpha = android.graphics.Color.alpha(baseColor)
        val alpha = (baseAlpha * percent / 100).coerceIn(0, 255)
        return ColorUtils.setAlphaComponent(baseColor, alpha)
    }
}

// XAULINXS_ALLAPPS_TRANSPARENCY_V2_FILE'''

    patch_file(rel, marker, old, new, "WallpaperScrimHelper: nova transparência sem blur")


def apply_qsb_live_update_patch() -> None:
    rel = "src/com/android/launcher3/qsb/OseWidgetView.kt"
    marker = "XaulinXs Customizations: os 4 sliders/cor da QsbConfigActivity só"

    old = '''    @SuppressLint("UseCompatLoadingForDrawables")
    override fun getErrorView(): View {
        val view =
            View.inflate(context, R.layout.ose_default_bubbletext_layout, null) as BubbleTextView
        applyXaulinXsQsbAppearance(view)
        val oseInfo = context.appComponent.getOseManager().oseInfo.value'''

    new = '''    @SuppressLint("UseCompatLoadingForDrawables")
    override fun getErrorView(): View {
        val view =
            View.inflate(context, R.layout.ose_default_bubbletext_layout, null) as BubbleTextView
        applyXaulinXsQsbAppearance(view)
        // XaulinXs Customizations: os 4 sliders/cor da QsbConfigActivity só
        // eram aplicados nesta linha, na inflação — mudar a config em
        // runtime não refletia na QSB já visível (só aparecia após "Forçar
        // parada" recriar a Activity do zero). Fix: observa as 4 prefs via
        // LauncherPrefs.addListener e reaplica na hora, sem precisar
        // recriar a view. Desregistrado automaticamente quando a view sai
        // de tela via registerLifecycleTask (mesmo padrão já usado abaixo
        // para o appsStore.addUpdateListener).
        val prefs = com.android.launcher3.LauncherPrefs.get(context)
        val qsbAppearanceListener =
            object : com.android.launcher3.LauncherPrefChangeListener {
                override fun onPrefChanged(key: String) {
                    applyXaulinXsQsbAppearance(view)
                }
            }
        view.registerLifecycleTask {
            prefs.addListener(
                qsbAppearanceListener,
                QsbConfig.SIZE_PERCENT,
                QsbConfig.WIDTH_PERCENT,
                QsbConfig.TRANSPARENCY_PERCENT,
                QsbConfig.BAR_COLOR,
            )
            SafeCloseable {
                prefs.removeListener(
                    qsbAppearanceListener,
                    QsbConfig.SIZE_PERCENT,
                    QsbConfig.WIDTH_PERCENT,
                    QsbConfig.TRANSPARENCY_PERCENT,
                    QsbConfig.BAR_COLOR,
                )
            }
        }
        val oseInfo = context.appComponent.getOseManager().oseInfo.value'''

    patch_file(rel, marker, old, new, "OseWidgetView: QSB atualiza cor/tamanho/largura/transparência em tempo real")


def apply_strings_patch() -> None:
    rel = "res/values/xaulinxs_strings.xml"
    marker = "xaulinxs_allapps_transparency_enabled_title"

    old_scrim_strings = (
        '<string name="xaulinxs_scrim_opacity_title">Transparência do fundo do menu de apps</string>\n'
        '    <string name="xaulinxs_scrim_opacity_summary">Ajusta a opacidade do véu atrás '
        'da gaveta de apps (aplica na próxima vez que abrir)</string>'
    )
    new_scrim_strings = (
        '<string name="xaulinxs_scrim_opacity_title">Transparência do véu temático (com blur)</string>\n'
        '    <string name="xaulinxs_scrim_opacity_summary">Ajusta a opacidade do véu colorido '
        'do wallpaper atrás da gaveta de apps — só tem efeito com "Fundo desfocado no menu de '
        'apps" ativado</string>\n'
        '    <string name="xaulinxs_allapps_transparency_enabled_title">Transparência do menu '
        'de apps (sem blur)</string>\n'
        '    <string name="xaulinxs_allapps_transparency_enabled_summary">Mostra a tela inicial '
        'por trás da gaveta de apps, sem nenhum desfoque — só funciona com "Fundo desfocado no '
        'menu de apps" DESATIVADO</string>\n'
        '    <string name="xaulinxs_allapps_transparency_percent_title">Nível de transparência</string>\n'
        '    <string name="xaulinxs_allapps_transparency_percent_summary">0% = totalmente '
        'transparente (mostra a tela inicial); 100% = opaco</string>'
    )

    old_widget_blur_strings = (
        '<string name="xaulinxs_widget_blur_title">Desfoque dos widgets</string>\n'
        '    <string name="xaulinxs_widget_blur_summary">Deixa a aparência de cada widget '
        'embaçada (0 = nítido)</string>'
    )
    new_widget_blur_strings = (
        '<string name="xaulinxs_widget_blur_title">Desfoque dos widgets</string>\n'
        '    <string name="xaulinxs_widget_blur_summary">Deixa a aparência de cada widget '
        'embaçada (0 = nítido)</string>\n'
        '    <string name="xaulinxs_gyro_tilt_title">Inclinação por giroscópio</string>\n'
        '    <string name="xaulinxs_gyro_tilt_summary">Inclina a tela inicial (efeito '
        'coverflow) conforme você move o aparelho na mão</string>'
    )

    patch_file(rel, marker, old_scrim_strings, new_scrim_strings,
               "strings: renomear transparência antiga + strings da nova")
    patch_file(rel, "xaulinxs_gyro_tilt_title", old_widget_blur_strings, new_widget_blur_strings,
               "strings: título/resumo do interruptor de giroscópio")


def apply_preferences_xml_patch() -> None:
    rel = "res/xml/launcher_preferences.xml"
    marker = "AllAppsTransparencyPercentPreference"

    old = '''        <com.xaulinxs.customizations.settings.WidgetBlurPreference
            android:key="xaulinxs_widget_blur_intensity"
            android:title="@string/xaulinxs_widget_blur_title"
            android:summary="@string/xaulinxs_widget_blur_summary"
            android:persistent="false" />'''

    new = '''        <com.xaulinxs.customizations.settings.WidgetBlurPreference
            android:key="xaulinxs_widget_blur_intensity"
            android:title="@string/xaulinxs_widget_blur_title"
            android:summary="@string/xaulinxs_widget_blur_summary"
            android:persistent="false" />

        <com.xaulinxs.customizations.settings.GyroTiltPreference
            android:key="xaulinxs_gyro_tilt_enabled"
            android:title="@string/xaulinxs_gyro_tilt_title"
            android:summary="@string/xaulinxs_gyro_tilt_summary"
            android:persistent="false" />

        <com.xaulinxs.customizations.settings.AllAppsTransparencyEnabledPreference
            android:key="xaulinxs_allapps_transparency_enabled"
            android:title="@string/xaulinxs_allapps_transparency_enabled_title"
            android:summary="@string/xaulinxs_allapps_transparency_enabled_summary"
            android:persistent="false" />

        <com.xaulinxs.customizations.settings.AllAppsTransparencyPercentPreference
            android:key="xaulinxs_allapps_transparency_percent"
            android:title="@string/xaulinxs_allapps_transparency_percent_title"
            android:summary="@string/xaulinxs_allapps_transparency_percent_summary"
            android:persistent="false" />'''

    patch_file(rel, marker, old, new, "launcher_preferences.xml: 3 novas entradas na tela")


def main() -> None:
    print(f"Aplicando patches em: {ROOT}\\n")

    if not (ROOT / "src" / "com" / "android" / "launcher3").exists():
        fail(
            "Não parece a raiz do checkout do XaulinXsLauncher3 "
            "(src/com/android/launcher3 não encontrado). Rode este script "
            "de dentro da pasta do repositório."
        )

    apply_new_files()
    print()
    apply_gyro_provider_patch()
    apply_wallpaper_scrim_helper_patch()
    apply_qsb_live_update_patch()
    apply_strings_patch()
    apply_preferences_xml_patch()

    print()
    print("Tudo aplicado. Resumo do que foi feito:")
    print("  1) Interruptor 'Inclinação por giroscópio' em XaulinXs Customizations")
    print("  2) Interruptor + slider 'Transparência do menu de apps (sem blur)'")
    print("     (só ativo quando o blur do menu de apps estiver DESLIGADO)")
    print("  3) QSB: cor/tamanho/largura/transparência agora atualizam na hora,")
    print("     sem precisar de 'Forçar parada'")
    print()
    print("Build: ./gradlew assembleNoQuickstepDebug")


if __name__ == "__main__":
    main()

