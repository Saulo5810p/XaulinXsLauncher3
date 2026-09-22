#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
XaulinXsLauncher3 — aplica duas mudanças nesta rodada:

1) FIX: slider "Largura" da QSB não tinha efeito em nenhum valor (não só
   acima de 100%). Causa raiz real: a lógica original fazia
   `(view.layoutParams as? LinearLayout.LayoutParams)?.let { ... }` dentro
   de OseWidgetView.applyXaulinXsQsbAppearance(), mas o BubbleTextView da
   QSB é inflado com `View.inflate(context, layout, null)` (root=null) e
   seu host (OseWidgetView) é filho direto de Hotseat, que estende
   CellLayout — o LayoutParams real nesse caminho é sempre
   CellLayoutLayoutParams, nunca LinearLayout.LayoutParams. O cast falhava
   silenciosamente sempre, então o slider nunca teve efeito nenhum,
   independente do valor. Fix: Largura passa a usar scaleX (combinado com
   o scaleX/scaleY já usado por Tamanho), o mesmo mecanismo que já
   funciona de verdade nesta view. Também eleva MAX_WIDTH_PERCENT de 100
   para 200, alinhando com o teto de Tamanho (pedido do usuário).

2) NOVA FEATURE: cor manual (paleta + sliders RGB + editor hex) para o
   fundo do Menu de aplicativo, na categoria "Menu de aplicativo" das
   Settings — só tem efeito quando "Fundo desfocado no menu de apps"
   estiver DESATIVADO (mesma condição que já rege a transparência sem
   blur existente). A transparência já existente continua se aplicando
   por cima da cor manual.

Uso: rode este script na raiz de um clone do repo
     (https://github.com/Saulo5810p/XaulinXsLauncher3), com Python 3.

Idempotente: pode ser rodado múltiplas vezes; detecta o que já foi
aplicado e pula. Se algum arquivo já tiver conteúdo conflitante
(diferente do esperado E diferente do já aplicado), aborta SÓ aquele
arquivo com um aviso claro, sem tocar nele, e continua com o resto.
"""

import base64
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent
EXIT_CODE = 0


def fail(msg: str) -> None:
    global EXIT_CODE
    print(f"[CONFLITO] {msg}", file=sys.stderr)
    EXIT_CODE = 1


def ok(msg: str) -> None:
    print(f"[OK] {msg}")


def skip(msg: str) -> None:
    print(f"[SKIP] {msg}")


def read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def write(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def patch_unique(path: Path, old: str, new: str, marker: str, label: str) -> None:
    """
    Aplica um patch old->new em um arquivo já existente, exigindo que
    `old` apareça exatamente uma vez. Idempotente via `marker`: se o
    marker já está no arquivo, pula. Se nem `old` nem `marker` batem,
    reporta conflito (arquivo mudou de um jeito inesperado) sem tocar.
    """
    if not path.exists():
        fail(f"{label}: arquivo não encontrado em {path}")
        return
    content = read(path)
    if marker in content:
        skip(f"{label}: já aplicado (marker presente)")
        return
    count = content.count(old)
    if count == 0:
        fail(
            f"{label}: trecho esperado não encontrado em {path} — "
            f"arquivo pode ter sido editado manualmente de forma "
            f"incompatível com este script. Nada foi alterado neste arquivo."
        )
        return
    if count > 1:
        fail(
            f"{label}: trecho esperado aparece {count} vezes em {path} "
            f"(esperado exatamente 1) — abortando este arquivo por segurança."
        )
        return
    write(path, content.replace(old, new, 1))
    ok(f"{label}: patch aplicado em {path}")


def write_new_file(path: Path, content_b64: str, marker: str, label: str) -> None:
    content = base64.b64decode(content_b64).decode("utf-8")
    if path.exists():
        existing = read(path)
        if marker in existing:
            skip(f"{label}: já aplicado (marker presente)")
            return
        if existing.strip() == content.strip():
            skip(f"{label}: conteúdo já idêntico")
            return
        fail(
            f"{label}: {path} já existe com conteúdo diferente do "
            f"esperado por este script — abortando este arquivo por "
            f"segurança, sem sobrescrever."
        )
        return
    write(path, content)
    ok(f"{label}: criado {path}")


# ---------------------------------------------------------------------
# 1) QsbConfig.kt — eleva MAX_WIDTH_PERCENT de 100 para 200
# ---------------------------------------------------------------------

QSB_CONFIG_PATH = REPO_ROOT / "modules/customizations/src/com/xaulinxs/customizations/qsb/QsbConfig.kt"

QSB_CONFIG_OLD = """    const val MIN_WIDTH_PERCENT = 50
    const val MAX_WIDTH_PERCENT = 100
    const val DEFAULT_WIDTH_PERCENT = 100"""

QSB_CONFIG_NEW = """    // XaulinXs Customizations: alinhado ao teto de 200% do slider "Tamanho"
    // (MAX_SIZE_PERCENT acima) — não fazia sentido Tamanho ir até 200% e
    // Largura travar em 100%. Ver XAULINXS_QSB_WIDTH_SCALEX_FIX em
    // OseWidgetView.kt: agora ambos os sliders escalam via scaleX/scaleY,
    // então a mesma faixa máxima se aplica igualmente aos dois.
    const val MIN_WIDTH_PERCENT = 50
    const val MAX_WIDTH_PERCENT = 200
    const val DEFAULT_WIDTH_PERCENT = 100"""

QSB_CONFIG_MARKER = "// XaulinXs Customizations: alinhado ao teto de 200% do slider \"Tamanho\""

# ---------------------------------------------------------------------
# 2) OseWidgetView.kt — troca weight quebrado por scaleX combinado
# ---------------------------------------------------------------------

OSE_WIDGET_VIEW_PATH = REPO_ROOT / "src/com/android/launcher3/qsb/OseWidgetView.kt"

OSE_WIDGET_VIEW_OLD = """    /**
     * XaulinXs Customizations: aplica os 4 sliders da QsbConfigActivity
     * (Tamanho, Largura, Transparência, Cor) na view inflada da QSB.
     * Tamanho e Largura são independentes (por isso dois sliders
     * separados em vez de uma única "escala"): Tamanho escala a view
     * inteira (scaleX/scaleY, mantém proporção); Largura reduz só a
     * largura via layout_weight fracionário, então dá pra ter uma QSB
     * mais estreita sem achatar o texto/ícone.
     */
    private fun applyXaulinXsQsbAppearance(view: BubbleTextView) {
        val sizeFraction = QsbConfig.getSizePercent(context) / 100f
        view.scaleX = sizeFraction
        view.scaleY = sizeFraction

        val widthFraction = QsbConfig.getWidthPercent(context) / 100f
        (view.layoutParams as? LinearLayout.LayoutParams)?.let { params ->
            params.weight = widthFraction
            view.layoutParams = params
        }

        val transparencyPercent = QsbConfig.getTransparencyPercent(context)
        view.alpha = 1f - (transparencyPercent / 100f)

        view.backgroundTintList = ColorStateList.valueOf(QsbConfig.getBarColor(context))
    }"""

OSE_WIDGET_VIEW_NEW = """    /**
     * XaulinXs Customizations: aplica os 4 sliders da QsbConfigActivity
     * (Tamanho, Largura, Transparência, Cor) na view inflada da QSB.
     *
     * XAULINXS_QSB_WIDTH_SCALEX_FIX: a implementação original de Largura
     * usava `(view.layoutParams as? LinearLayout.LayoutParams)?.let { ... }`
     * — nunca tinha efeito nenhum, com o slider em qualquer valor. Causa
     * raiz: este BubbleTextView é inflado via
     * `View.inflate(context, R.layout.ose_default_bubbletext_layout, null)`
     * com root=null (ver getErrorView() acima) — os atributos
     * `layout_width="0dp"`/`layout_weight="1"` do XML nunca viram um
     * `LinearLayout.LayoutParams` de verdade nesse caminho, e o pai real
     * deste host (OseWidgetView) dentro da Hotseat é um CellLayout
     * (Hotseat.addView(mQsb) sem LayoutParams explícito), cujo
     * generateLayoutParams produz CellLayoutLayoutParams — nunca
     * LinearLayout.LayoutParams. O cast falhava silenciosamente sempre, e
     * o `?.let` nunca executava.
     *
     * Fix: Largura agora usa o mesmo mecanismo que já funciona pro
     * Tamanho (scaleX/scaleY), mas só no eixo X, combinando os dois
     * fatores — Tamanho aplica a ambos eixos, Largura aplica só ao X por
     * cima. Isso mantém "Tamanho" controlando a escala uniforme
     * (ícone+texto+altura da barra) e "Largura" controlando só a
     * largura, sem achatar a altura nem esticar o ícone/texto
     * verticalmente. clipChildren/clipToPadding já estão desligados
     * neste host (ver XAULINXS_QSB_SIZE_SLIDER_CLIP_FIX no init acima),
     * então crescer acima de 100% em X não é cortado.
     */
    private fun applyXaulinXsQsbAppearance(view: BubbleTextView) {
        val sizeFraction = QsbConfig.getSizePercent(context) / 100f
        val widthFraction = QsbConfig.getWidthPercent(context) / 100f

        view.scaleX = sizeFraction * widthFraction
        view.scaleY = sizeFraction

        val transparencyPercent = QsbConfig.getTransparencyPercent(context)
        view.alpha = 1f - (transparencyPercent / 100f)

        view.backgroundTintList = ColorStateList.valueOf(QsbConfig.getBarColor(context))
    }"""

OSE_WIDGET_VIEW_MARKER = "XAULINXS_QSB_WIDTH_SCALEX_FIX"

# ---------------------------------------------------------------------
# 3) ActivityAllAppsContainerView.java — gancho da cor manual
# ---------------------------------------------------------------------

ALLAPPS_CONTAINER_PATH = REPO_ROOT / "src/com/android/launcher3/allapps/ActivityAllAppsContainerView.java"

ALLAPPS_CONTAINER_OLD = """        // XaulinXs Customizations: quando o blur do menu de apps está
        // desligado, este era o retângulo opaco (mBottomSheetBackgroundColorBlurFallback)
        // pintado por cima de TUDO em drawOnScrimWithScaleAndBottomOffset —
        // inclusive por cima da WallpaperGradientView e de qualquer alpha
        // vindo de AllAppsState.getWorkspaceScrimColor()/WallpaperScrimHelper,
        // por isso a transparência não tinha efeito nenhum visualmente
        // mesmo com o valor correto sendo calculado em outro lugar. Aqui é
        // o ponto real que precisa respeitar o slider.
        return com.xaulinxs.customizations.theme.WallpaperScrimHelperKt.applyAllAppsTransparency(
                getContext(), mBottomSheetBackgroundColorBlurFallback);
    }
    // XAULINXS_ALLAPPS_TRANSPARENCY_REAL_HOOK"""

ALLAPPS_CONTAINER_NEW = """        // XaulinXs Customizations: quando o blur do menu de apps está
        // desligado, este era o retângulo opaco (mBottomSheetBackgroundColorBlurFallback)
        // pintado por cima de TUDO em drawOnScrimWithScaleAndBottomOffset —
        // inclusive por cima da WallpaperGradientView e de qualquer alpha
        // vindo de AllAppsState.getWorkspaceScrimColor()/WallpaperScrimHelper,
        // por isso a transparência não tinha efeito nenhum visualmente
        // mesmo com o valor correto sendo calculado em outro lugar. Aqui é
        // o ponto real que precisa respeitar o slider.
        //
        // XAULINXS_ALLAPPS_COLOR_HOOK: cor manual (paleta/sliders/hex) tem
        // prioridade sobre mBottomSheetBackgroundColorBlurFallback quando
        // ativada — condicionada a este mesmo bloco (fundo desfocado já
        // desligado), atendendo ao pedido do usuário de só valer com o
        // blur desativado. A transparência abaixo continua sendo aplicada
        // por cima em qualquer um dos dois casos.
        Integer colorOverride = com.xaulinxs.customizations.theme.XaulinXsAllAppsColor
                .getColorOverrideIfEnabled(getContext());
        int fallbackColor = colorOverride != null
                ? colorOverride
                : mBottomSheetBackgroundColorBlurFallback;
        return com.xaulinxs.customizations.theme.WallpaperScrimHelperKt.applyAllAppsTransparency(
                getContext(), fallbackColor);
    }
    // XAULINXS_ALLAPPS_TRANSPARENCY_REAL_HOOK"""

ALLAPPS_CONTAINER_MARKER = "XAULINXS_ALLAPPS_COLOR_HOOK"

# ---------------------------------------------------------------------
# 4) launcher_preferences.xml — novas entradas na categoria allapps
# ---------------------------------------------------------------------

LAUNCHER_PREFS_PATH = REPO_ROOT / "res/xml/launcher_preferences.xml"

LAUNCHER_PREFS_OLD = """            <com.xaulinxs.customizations.settings.AllAppsTransparencyPercentPreference
                android:key="xaulinxs_allapps_transparency_percent"
                android:title="@string/xaulinxs_allapps_transparency_percent_title"
                android:summary="@string/xaulinxs_allapps_transparency_percent_summary"
                android:persistent="false" />

        </PreferenceScreen>

        <!-- Balões: menus de contexto (long-press) -->"""

LAUNCHER_PREFS_NEW = """            <com.xaulinxs.customizations.settings.AllAppsTransparencyPercentPreference
                android:key="xaulinxs_allapps_transparency_percent"
                android:title="@string/xaulinxs_allapps_transparency_percent_title"
                android:summary="@string/xaulinxs_allapps_transparency_percent_summary"
                android:persistent="false" />

            <com.xaulinxs.customizations.settings.AllAppsColorEnabledPreference
                android:key="xaulinxs_allapps_color_enabled"
                android:title="@string/xaulinxs_allapps_color_enabled_title"
                android:summary="@string/xaulinxs_allapps_color_enabled_summary"
                android:persistent="false" />

            <com.xaulinxs.customizations.settings.AllAppsColorPickerPreference
                android:key="xaulinxs_allapps_color_picker"
                android:title="@string/xaulinxs_allapps_color_picker_title"
                android:persistent="false" />

        </PreferenceScreen>

        <!-- Balões: menus de contexto (long-press) -->"""

LAUNCHER_PREFS_MARKER = "xaulinxs_allapps_color_enabled"

# ---------------------------------------------------------------------
# 5) xaulinxs_strings.xml — novas strings
# ---------------------------------------------------------------------

STRINGS_PATH = REPO_ROOT / "res/values/xaulinxs_strings.xml"

STRINGS_OLD = """    <string name="xaulinxs_allapps_transparency_percent_title">Nível de transparência</string>
    <string name="xaulinxs_allapps_transparency_percent_summary" formatted="false">0% = totalmente transparente (mostra a tela inicial); 100% = opaco</string>
    <string name="xaulinxs_popup_blur_title">Blur nos balões de contexto</string>"""

STRINGS_NEW = """    <string name="xaulinxs_allapps_transparency_percent_title">Nível de transparência</string>
    <string name="xaulinxs_allapps_transparency_percent_summary" formatted="false">0% = totalmente transparente (mostra a tela inicial); 100% = opaco</string>
    <string name="xaulinxs_allapps_color_enabled_title">Cor manual do fundo</string>
    <string name="xaulinxs_allapps_color_enabled_summary">Usa uma cor fixa escolhida por você no fundo do menu de apps em vez da cor padrão do tema — só funciona com "Fundo desfocado no menu de apps" DESATIVADO. A transparência acima continua se aplicando</string>
    <string name="xaulinxs_allapps_color_picker_title">Escolher cor (paleta, sliders ou hex)</string>
    <string name="xaulinxs_popup_blur_title">Blur nos balões de contexto</string>"""

STRINGS_MARKER = "xaulinxs_allapps_color_enabled_title"

# ---------------------------------------------------------------------
# Arquivos novos (conteúdo completo em base64)
# ---------------------------------------------------------------------

ALLAPPS_COLOR_DATA_PATH = REPO_ROOT / "modules/customizations/src/com/xaulinxs/customizations/theme/XaulinXsAllAppsColor.kt"
ALLAPPS_COLOR_ENABLED_PREF_PATH = REPO_ROOT / "modules/customizations/src/com/xaulinxs/customizations/settings/AllAppsColorEnabledPreference.kt"
ALLAPPS_COLOR_PICKER_PREF_PATH = REPO_ROOT / "modules/customizations/src/com/xaulinxs/customizations/settings/AllAppsColorPickerPreference.kt"

NEW_FILES_B64 = {
    "allapps_color_data": "LyoKICogWGF1bGluWHMgQ3VzdG9taXphdGlvbnMg4oCUIG7Do28gZmF6IHBhcnRlIGRvIEFPU1Agb3JpZ2luYWwuCiAqCiAqIENvciBtYW51YWwgZG8gZnVuZG8gZG8gTWVudSBkZSBhcGxpY2F0aXZvIChjYXRlZ29yaWEgIk1lbnUgZGUKICogYXBsaWNhdGl2byIgZGFzIFNldHRpbmdzKSwgY29tIHBhbGV0YSArIHNsaWRlcnMgUkdCICsgZWRpdG9yIGhleCDigJQKICogcGVkaWRvIGV4cGzDrWNpdG8gZG8gdXN1w6FyaW8sIGRpc3RpbnRvIGRlIFhhdWxpblhzTWFudWFsQ29sb3IgKHF1ZQogKiBhZmV0YSDDrWNvbmVzIHRlbcOhdGljb3MgKyBvIHbDqXUgY29tIGJsdXIgbGlnYWRvKSBlIGRlCiAqIFhhdWxpblhzQmFsbG9vbkNvbG9yIChiYWzDtWVzL21lbnVzIGRlIGNvbnRleHRvKS4gTWVzbW8gcGFkcsOjbwogKiBlc3RydXR1cmFsIGRlc3NhcyBkdWFzOiB1bSBwYXIgRU5BQkxFRC9BUkdCIHZpYQogKiBMYXVuY2hlclByZWZzLmJhY2tlZFVwSXRlbSgpLgogKgogKiBDb25kacOnw6NvIGRlIGF0aXZhw6fDo28gcGVkaWRhIHBlbG8gdXN1w6FyaW86IHPDsyB0ZW0gZWZlaXRvIHF1YW5kbyBvCiAqICJGdW5kbyBkZXNmb2NhZG8gbm8gbWVudSBkZSBhcHBzIiAoVGhlbWVkU2NyaW1QcmVmZXJlbmNlIC8KICogVEhFTUVEX1NDUklNX0VOQUJMRUQpIGVzdGl2ZXIgREVTQVRJVkFETyDigJQgbWVzbWEgY29uZGnDp8OjbyBxdWUgasOhCiAqIHJlZ2UgQUxMQVBQU19UUkFOU1BBUkVOQ1lfRU5BQkxFRCBlbSBXYWxscGFwZXJTY3JpbUhlbHBlci5rdC4gUXVhbmRvCiAqIG8gYmx1ciBlc3TDoSBsaWdhZG8sIGVzdGEgY29yIMOpIGlnbm9yYWRhIGUgbyBmdW5kbyBjb250aW51YSBzZW5kbyBvCiAqIG1Cb3R0b21TaGVldEJhY2tncm91bmRDb2xvck92ZXJCbHVyIG5vcm1hbCBkbyBBT1NQLgogKgogKiBBIHRyYW5zcGFyw6puY2lhIGRvIG1lbnUgZGUgYXBwcyAoQUxMQVBQU19UUkFOU1BBUkVOQ1lfUEVSQ0VOVCkgasOhIMOpCiAqIGFwbGljYWRhIHBvciBjaW1hIGRlIHF1YWxxdWVyIGJhc2VDb2xvciBlbSBhcHBseUFsbEFwcHNUcmFuc3BhcmVuY3koKQogKiDigJQgcGVkaWRvIGRvIHVzdcOhcmlvICgiZmF6ZXIgY29tIHF1ZSBhIGZlYXR1cmUgZGUgVHJhbnNwYXLDqm5jaWEgc2UKICogYXBsaXF1ZSBhIGVsZSB0YW1iw6ltIikgasOhIGNhaSBkZSBncmHDp2E6IGdldENvbG9yT3ZlcnJpZGVJZkVuYWJsZWQoKQogKiBzw7MgcHJlY2lzYSBzdWJzdGl0dWlyIG8gYmFzZUNvbG9yIGRlIGVudHJhZGEsIHF1ZW0gYXBsaWNhIG8gYWxwaGEgZG8KICogc2xpZGVyIGNvbnRpbnVhIHNlbmRvIGEgbWVzbWEgZnVuw6fDo28gZGUgc2VtcHJlLgogKi8KcGFja2FnZSBjb20ueGF1bGlueHMuY3VzdG9taXphdGlvbnMudGhlbWUKCmltcG9ydCBhbmRyb2lkLmNvbnRlbnQuQ29udGV4dAppbXBvcnQgY29tLmFuZHJvaWQubGF1bmNoZXIzLkxhdW5jaGVyUHJlZnMKaW1wb3J0IGNvbS5hbmRyb2lkLmxhdW5jaGVyMy5MYXVuY2hlclByZWZzLkNvbXBhbmlvbi5iYWNrZWRVcEl0ZW0KaW1wb3J0IGNvbS54YXVsaW54cy5jdXN0b21pemF0aW9ucy5zZXR0aW5ncy5UaGVtZWRTY3JpbVByZWZlcmVuY2UuQ29tcGFuaW9uLlRIRU1FRF9TQ1JJTV9FTkFCTEVECgpwcml2YXRlIGNvbnN0IHZhbCBLRVlfQUxMQVBQU19DT0xPUl9FTkFCTEVEID0gInhhdWxpbnhzX2FsbGFwcHNfY29sb3JfZW5hYmxlZCIKcHJpdmF0ZSBjb25zdCB2YWwgS0VZX0FMTEFQUFNfQ09MT1JfQVJHQiA9ICJ4YXVsaW54c19hbGxhcHBzX2NvbG9yX2FyZ2IiCgovLyBNZXNtbyByb3hvIE1hdGVyaWFsIHVzYWRvIGNvbW8gZGVmYXVsdCBub3Mgb3V0cm9zIGNvbG9yIHBpY2tlcnMgZG8KLy8gcHJvamV0byAoUXNiQ29uZmlnLkRFRkFVTFRfQkFSX0NPTE9SLCBYYXVsaW5Yc01hbnVhbENvbG9yLkRFRkFVTFRfQ09MT1IpLAovLyBwb3IgY29uc2lzdMOqbmNpYSB2aXN1YWwgZW50cmUgYXMgdGVsYXMgZGUgcGVyc29uYWxpemHDp8Ojby4KcHJpdmF0ZSBjb25zdCB2YWwgREVGQVVMVF9BTExBUFBTX0NPTE9SID0gMHhGRjY3NTBBNC50b0ludCgpCgpvYmplY3QgWGF1bGluWHNBbGxBcHBzQ29sb3IgewoKICAgIHZhbCBBTExBUFBTX0NPTE9SX0VOQUJMRUQgPSBiYWNrZWRVcEl0ZW0oS0VZX0FMTEFQUFNfQ09MT1JfRU5BQkxFRCwgZmFsc2UpCiAgICB2YWwgQUxMQVBQU19DT0xPUl9BUkdCID0gYmFja2VkVXBJdGVtKEtFWV9BTExBUFBTX0NPTE9SX0FSR0IsIERFRkFVTFRfQUxMQVBQU19DT0xPUikKCiAgICAvKioKICAgICAqIENvciBtYW51YWwgKEFSR0Igb3BhY28pIHBhcmEgbyBmdW5kbyBkbyBtZW51IGRlIGFwcHMsIG91IG51bGwgc2UgYQogICAgICogZmVhdHVyZSBuw6NvIGRldmUgc2UgYXBsaWNhciBhZ29yYSDigJQgc2VqYSBwb3JxdWUgZXN0w6EgZGVzbGlnYWRhLAogICAgICogc2VqYSBwb3JxdWUgbyBmdW5kbyBkZXNmb2NhZG8gZXN0w6EgYXRpdm8gKGNvbmRpw6fDo28gZXhpZ2lkYSBwZWxvCiAgICAgKiB1c3XDoXJpbykuIE5lc3NlIGNhc28gbyBjaGFtYWRvciBkZXZlIHVzYXIgbyBiYXNlQ29sb3Igb3JpZ2luYWwuCiAgICAgKi8KICAgIEBKdm1TdGF0aWMKICAgIGZ1biBnZXRDb2xvck92ZXJyaWRlSWZFbmFibGVkKGNvbnRleHQ6IENvbnRleHQpOiBJbnQ/IHsKICAgICAgICB2YWwgcHJlZnMgPSBMYXVuY2hlclByZWZzLmdldChjb250ZXh0KQogICAgICAgIGlmIChwcmVmcy5nZXQoVEhFTUVEX1NDUklNX0VOQUJMRUQpKSByZXR1cm4gbnVsbAogICAgICAgIGlmICghcHJlZnMuZ2V0KEFMTEFQUFNfQ09MT1JfRU5BQkxFRCkpIHJldHVybiBudWxsCiAgICAgICAgcmV0dXJuIHByZWZzLmdldChBTExBUFBTX0NPTE9SX0FSR0IpCiAgICB9Cn0KCi8vIFhBVUxJTlhTX0FMTEFQUFNfQ09MT1JfREFUQV9GSUxFCg==",
    "allapps_color_enabled_pref": "LyoKICogWGF1bGluWHMgQ3VzdG9taXphdGlvbnMg4oCUIG7Do28gZmF6IHBhcnRlIGRvIEFPU1Agb3JpZ2luYWwuCiAqLwpwYWNrYWdlIGNvbS54YXVsaW54cy5jdXN0b21pemF0aW9ucy5zZXR0aW5ncwoKaW1wb3J0IGFuZHJvaWQuY29udGVudC5Db250ZXh0CmltcG9ydCBhbmRyb2lkLnV0aWwuQXR0cmlidXRlU2V0CmltcG9ydCBhbmRyb2lkeC5wcmVmZXJlbmNlLlN3aXRjaFByZWZlcmVuY2UKaW1wb3J0IGNvbS5hbmRyb2lkLmxhdW5jaGVyMy5MYXVuY2hlclByZWZzCmltcG9ydCBjb20ueGF1bGlueHMuY3VzdG9taXphdGlvbnMudGhlbWUuWGF1bGluWHNBbGxBcHBzQ29sb3IKaW1wb3J0IGNvbS54YXVsaW54cy5jdXN0b21pemF0aW9ucy50aGVtZS5YYXVsaW5Yc0FsbEFwcHNUcmFuc3BhcmVuY3lSZWRyYXcKCmNsYXNzIEFsbEFwcHNDb2xvckVuYWJsZWRQcmVmZXJlbmNlIEBKdm1PdmVybG9hZHMgY29uc3RydWN0b3IoCiAgICBjb250ZXh0OiBDb250ZXh0LAogICAgYXR0cnM6IEF0dHJpYnV0ZVNldD8gPSBudWxsLAopIDogU3dpdGNoUHJlZmVyZW5jZShjb250ZXh0LCBhdHRycykgewoKICAgIGluaXQgewogICAgICAgIGlzUGVyc2lzdGVudCA9IGZhbHNlCiAgICAgICAgaXNDaGVja2VkID0gTGF1bmNoZXJQcmVmcy5nZXQoY29udGV4dCkuZ2V0KFhhdWxpblhzQWxsQXBwc0NvbG9yLkFMTEFQUFNfQ09MT1JfRU5BQkxFRCkKICAgICAgICBzZXRPblByZWZlcmVuY2VDaGFuZ2VMaXN0ZW5lciB7IF8sIG5ld1ZhbHVlIC0+CiAgICAgICAgICAgIExhdW5jaGVyUHJlZnMuZ2V0KGNvbnRleHQpLnB1dChYYXVsaW5Yc0FsbEFwcHNDb2xvci5BTExBUFBTX0NPTE9SX0VOQUJMRUQsIG5ld1ZhbHVlIGFzIEJvb2xlYW4pCiAgICAgICAgICAgIFhhdWxpblhzQWxsQXBwc1RyYW5zcGFyZW5jeVJlZHJhdy5yZXF1ZXN0UmVkcmF3KGNvbnRleHQpCiAgICAgICAgICAgIHRydWUKICAgICAgICB9CiAgICB9Cn0KCi8vIFhBVUxJTlhTX0FMTEFQUFNfQ09MT1JfRU5BQkxFRF9QUkVGRVJFTkNFX0ZJTEUK",
    "allapps_color_picker_pref": "LyoKICogWGF1bGluWHMgQ3VzdG9taXphdGlvbnMg4oCUIG7Do28gZmF6IHBhcnRlIGRvIEFPU1Agb3JpZ2luYWwuCiAqCiAqIEVkaXRvciBkZSBjb3IgbWFudWFsIGRvIE1lbnUgZGUgYXBsaWNhdGl2bzogcGFsZXRhIGRlIHN3YXRjaGVzIHLDoXBpZG9zICsKICogY2FtcG8gaGV4ICsgMyBzbGlkZXJzIFJHQiwgdG9kb3Mgc2luY3Jvbml6YWRvcyBlbnRyZSBzaSwgY29tIHByZXZpZXcgYW8KICogdml2byBkZW50cm8gZG8gcHLDs3ByaW8gZGnDoWxvZ28uIE1lc21vIHBhZHLDo28gZGUgaGV4K1JHQiBqw6EgdXNhZG8gcG9yCiAqIE1hbnVhbENvbG9yUGlja2VyUHJlZmVyZW5jZSAow61jb25lcykvQmFsbG9vbkNvbG9yUGlja2VyUHJlZmVyZW5jZQogKiAoYmFsw7VlcykvRm9sZGVyQ29sb3JQaWNrZXJQcmVmZXJlbmNlIChwYXN0YXMpLCBjb20gcGFsZXRhIGFkaWNpb25hZGEgcG9yCiAqIHBlZGlkbyBleHBsw61jaXRvIGRvIHVzdcOhcmlvIHBhcmEgZXN0YSBmZWF0dXJlLgogKgogKiBVc2EgYW5kcm9pZC5hcHAuQWxlcnREaWFsb2cgKGZyYW1ld29yayksIG7Do28gYW5kcm9pZHguYXBwY29tcGF0IOKAlCBhIHRlbGEKICogZGUgU2V0dGluZ3MgKEhvbWVTZXR0aW5ncy5UaGVtZSkgaGVyZGEgZGUgdW0gdGVtYSBwdXJvIGRvIEFuZHJvaWQsIG7Do28gdW0KICogVGhlbWUuQXBwQ29tcGF0LiBBbGVydERpYWxvZyBkbyBBcHBDb21wYXQgZXhpZ2UgdW0gdGVtYSBBcHBDb21wYXQgZQogKiBjcmFzaGEgKElsbGVnYWxTdGF0ZUV4Y2VwdGlvbikgbmVzc2UgY29udGV4dG8uCiAqLwpwYWNrYWdlIGNvbS54YXVsaW54cy5jdXN0b21pemF0aW9ucy5zZXR0aW5ncwoKaW1wb3J0IGFuZHJvaWQuYXBwLkFsZXJ0RGlhbG9nCmltcG9ydCBhbmRyb2lkLmNvbnRlbnQuQ29udGV4dAppbXBvcnQgYW5kcm9pZC5ncmFwaGljcy5Db2xvcgppbXBvcnQgYW5kcm9pZC5ncmFwaGljcy5kcmF3YWJsZS5HcmFkaWVudERyYXdhYmxlCmltcG9ydCBhbmRyb2lkLnRleHQuRWRpdGFibGUKaW1wb3J0IGFuZHJvaWQudGV4dC5JbnB1dFR5cGUKaW1wb3J0IGFuZHJvaWQudGV4dC5UZXh0V2F0Y2hlcgppbXBvcnQgYW5kcm9pZC51dGlsLkF0dHJpYnV0ZVNldAppbXBvcnQgYW5kcm9pZC52aWV3LkdyYXZpdHkKaW1wb3J0IGFuZHJvaWQudmlldy5WaWV3CmltcG9ydCBhbmRyb2lkLndpZGdldC5FZGl0VGV4dAppbXBvcnQgYW5kcm9pZC53aWRnZXQuSG9yaXpvbnRhbFNjcm9sbFZpZXcKaW1wb3J0IGFuZHJvaWQud2lkZ2V0LkxpbmVhckxheW91dAppbXBvcnQgYW5kcm9pZC53aWRnZXQuU2Vla0JhcgppbXBvcnQgYW5kcm9pZC53aWRnZXQuVGV4dFZpZXcKaW1wb3J0IGFuZHJvaWR4LnByZWZlcmVuY2UuUHJlZmVyZW5jZQppbXBvcnQgY29tLmFuZHJvaWQubGF1bmNoZXIzLkxhdW5jaGVyUHJlZnMKaW1wb3J0IGNvbS5hbmRyb2lkLmxhdW5jaGVyMy5SCmltcG9ydCBjb20ueGF1bGlueHMuY3VzdG9taXphdGlvbnMudGhlbWUuWGF1bGluWHNBbGxBcHBzQ29sb3IKCmNsYXNzIEFsbEFwcHNDb2xvclBpY2tlclByZWZlcmVuY2UgQEp2bU92ZXJsb2FkcyBjb25zdHJ1Y3RvcigKICAgIGNvbnRleHQ6IENvbnRleHQsCiAgICBhdHRyczogQXR0cmlidXRlU2V0PyA9IG51bGwsCikgOiBQcmVmZXJlbmNlKGNvbnRleHQsIGF0dHJzKSB7CgogICAgaW5pdCB7CiAgICAgICAgaXNQZXJzaXN0ZW50ID0gZmFsc2UKICAgICAgICB1cGRhdGVTdW1tYXJ5KCkKICAgIH0KCiAgICBvdmVycmlkZSBmdW4gb25DbGljaygpIHsKICAgICAgICB2YWwgcHJlZnMgPSBMYXVuY2hlclByZWZzLmdldChjb250ZXh0KQogICAgICAgIHZhbCBjdXJyZW50Q29sb3IgPSBwcmVmcy5nZXQoWGF1bGluWHNBbGxBcHBzQ29sb3IuQUxMQVBQU19DT0xPUl9BUkdCKQogICAgICAgIHZhbCBkZW5zaXR5ID0gY29udGV4dC5yZXNvdXJjZXMuZGlzcGxheU1ldHJpY3MuZGVuc2l0eQogICAgICAgIHZhbCBwcmV2aWV3U2l6ZVB4ID0gKDU2ICogZGVuc2l0eSkudG9JbnQoKQogICAgICAgIHZhbCBwYWRkaW5nUHggPSAoMjQgKiBkZW5zaXR5KS50b0ludCgpCiAgICAgICAgdmFsIHN3YXRjaFNpemVQeCA9ICg0MCAqIGRlbnNpdHkpLnRvSW50KCkKICAgICAgICB2YWwgc3dhdGNoTWFyZ2luUHggPSAoOCAqIGRlbnNpdHkpLnRvSW50KCkKCiAgICAgICAgdmFyIGlzU3luY2luZyA9IGZhbHNlCgogICAgICAgIHZhbCBwcmV2aWV3ID0gVmlldyhjb250ZXh0KS5hcHBseSB7IHNldEJhY2tncm91bmRDb2xvcihjdXJyZW50Q29sb3IpIH0KCiAgICAgICAgdmFsIGhleElucHV0ID0gRWRpdFRleHQoY29udGV4dCkuYXBwbHkgewogICAgICAgICAgICBpbnB1dFR5cGUgPSBJbnB1dFR5cGUuVFlQRV9DTEFTU19URVhUCiAgICAgICAgICAgIHNldFRleHQoU3RyaW5nLmZvcm1hdCgiIyUwNlgiLCAweEZGRkZGRiBhbmQgY3VycmVudENvbG9yKSkKICAgICAgICAgICAgc2V0U2VsZWN0aW9uKHRleHQubGVuZ3RoKQogICAgICAgIH0KCiAgICAgICAgZnVuIG1ha2VTbGlkZXIobGFiZWw6IFN0cmluZywgaW5pdGlhbFZhbHVlOiBJbnQpOiBQYWlyPExpbmVhckxheW91dCwgU2Vla0Jhcj4gewogICAgICAgICAgICB2YWwgcm93ID0gTGluZWFyTGF5b3V0KGNvbnRleHQpLmFwcGx5IHsKICAgICAgICAgICAgICAgIG9yaWVudGF0aW9uID0gTGluZWFyTGF5b3V0LkhPUklaT05UQUwKICAgICAgICAgICAgICAgIGdyYXZpdHkgPSBHcmF2aXR5LkNFTlRFUl9WRVJUSUNBTAogICAgICAgICAgICB9CiAgICAgICAgICAgIHZhbCBsYWJlbFZpZXcgPSBUZXh0Vmlldyhjb250ZXh0KS5hcHBseSB7CiAgICAgICAgICAgICAgICB0ZXh0ID0gbGFiZWwKICAgICAgICAgICAgICAgIHZhbCBsYWJlbFdpZHRoID0gKDI0ICogZGVuc2l0eSkudG9JbnQoKQogICAgICAgICAgICAgICAgbGF5b3V0UGFyYW1zID0gTGluZWFyTGF5b3V0LkxheW91dFBhcmFtcyhsYWJlbFdpZHRoLCBMaW5lYXJMYXlvdXQuTGF5b3V0UGFyYW1zLldSQVBfQ09OVEVOVCkKICAgICAgICAgICAgfQogICAgICAgICAgICB2YWwgc2Vla0JhciA9IFNlZWtCYXIoY29udGV4dCkuYXBwbHkgewogICAgICAgICAgICAgICAgbWF4ID0gMjU1CiAgICAgICAgICAgICAgICBwcm9ncmVzcyA9IGluaXRpYWxWYWx1ZQogICAgICAgICAgICAgICAgbGF5b3V0UGFyYW1zID0gTGluZWFyTGF5b3V0LkxheW91dFBhcmFtcygwLCBMaW5lYXJMYXlvdXQuTGF5b3V0UGFyYW1zLldSQVBfQ09OVEVOVCwgMWYpCiAgICAgICAgICAgIH0KICAgICAgICAgICAgcm93LmFkZFZpZXcobGFiZWxWaWV3KQogICAgICAgICAgICByb3cuYWRkVmlldyhzZWVrQmFyKQogICAgICAgICAgICByZXR1cm4gcm93IHRvIHNlZWtCYXIKICAgICAgICB9CgogICAgICAgIHZhbCAocmVkUm93LCByZWRTZWVrKSA9IG1ha2VTbGlkZXIoIlIiLCBDb2xvci5yZWQoY3VycmVudENvbG9yKSkKICAgICAgICB2YWwgKGdyZWVuUm93LCBncmVlblNlZWspID0gbWFrZVNsaWRlcigiRyIsIENvbG9yLmdyZWVuKGN1cnJlbnRDb2xvcikpCiAgICAgICAgdmFsIChibHVlUm93LCBibHVlU2VlaykgPSBtYWtlU2xpZGVyKCJCIiwgQ29sb3IuYmx1ZShjdXJyZW50Q29sb3IpKQoKICAgICAgICBmdW4gY3VycmVudFNsaWRlckNvbG9yKCk6IEludCA9CiAgICAgICAgICAgIENvbG9yLnJnYihyZWRTZWVrLnByb2dyZXNzLCBncmVlblNlZWsucHJvZ3Jlc3MsIGJsdWVTZWVrLnByb2dyZXNzKQoKICAgICAgICBmdW4gdXBkYXRlRnJvbUNvbG9yKGNvbG9yOiBJbnQpIHsKICAgICAgICAgICAgaXNTeW5jaW5nID0gdHJ1ZQogICAgICAgICAgICBwcmV2aWV3LnNldEJhY2tncm91bmRDb2xvcihjb2xvcikKICAgICAgICAgICAgaGV4SW5wdXQuc2V0VGV4dChTdHJpbmcuZm9ybWF0KCIjJTA2WCIsIDB4RkZGRkZGIGFuZCBjb2xvcikpCiAgICAgICAgICAgIGhleElucHV0LnNldFNlbGVjdGlvbihoZXhJbnB1dC50ZXh0Lmxlbmd0aCkKICAgICAgICAgICAgcmVkU2Vlay5wcm9ncmVzcyA9IENvbG9yLnJlZChjb2xvcikKICAgICAgICAgICAgZ3JlZW5TZWVrLnByb2dyZXNzID0gQ29sb3IuZ3JlZW4oY29sb3IpCiAgICAgICAgICAgIGJsdWVTZWVrLnByb2dyZXNzID0gQ29sb3IuYmx1ZShjb2xvcikKICAgICAgICAgICAgaXNTeW5jaW5nID0gZmFsc2UKICAgICAgICB9CgogICAgICAgIGZ1biB1cGRhdGVGcm9tU2xpZGVycygpIHsKICAgICAgICAgICAgaWYgKGlzU3luY2luZykgcmV0dXJuCiAgICAgICAgICAgIGlzU3luY2luZyA9IHRydWUKICAgICAgICAgICAgdmFsIGNvbG9yID0gY3VycmVudFNsaWRlckNvbG9yKCkKICAgICAgICAgICAgcHJldmlldy5zZXRCYWNrZ3JvdW5kQ29sb3IoY29sb3IpCiAgICAgICAgICAgIGhleElucHV0LnNldFRleHQoU3RyaW5nLmZvcm1hdCgiIyUwNlgiLCAweEZGRkZGRiBhbmQgY29sb3IpKQogICAgICAgICAgICBoZXhJbnB1dC5zZXRTZWxlY3Rpb24oaGV4SW5wdXQudGV4dC5sZW5ndGgpCiAgICAgICAgICAgIGlzU3luY2luZyA9IGZhbHNlCiAgICAgICAgfQoKICAgICAgICB2YWwgc2xpZGVyTGlzdGVuZXIgPSBvYmplY3QgOiBTZWVrQmFyLk9uU2Vla0JhckNoYW5nZUxpc3RlbmVyIHsKICAgICAgICAgICAgb3ZlcnJpZGUgZnVuIG9uUHJvZ3Jlc3NDaGFuZ2VkKHNlZWtCYXI6IFNlZWtCYXI/LCBwcm9ncmVzczogSW50LCBmcm9tVXNlcjogQm9vbGVhbikgewogICAgICAgICAgICAgICAgaWYgKGZyb21Vc2VyKSB1cGRhdGVGcm9tU2xpZGVycygpCiAgICAgICAgICAgIH0KICAgICAgICAgICAgb3ZlcnJpZGUgZnVuIG9uU3RhcnRUcmFja2luZ1RvdWNoKHNlZWtCYXI6IFNlZWtCYXI/KSB7fQogICAgICAgICAgICBvdmVycmlkZSBmdW4gb25TdG9wVHJhY2tpbmdUb3VjaChzZWVrQmFyOiBTZWVrQmFyPykge30KICAgICAgICB9CiAgICAgICAgcmVkU2Vlay5zZXRPblNlZWtCYXJDaGFuZ2VMaXN0ZW5lcihzbGlkZXJMaXN0ZW5lcikKICAgICAgICBncmVlblNlZWsuc2V0T25TZWVrQmFyQ2hhbmdlTGlzdGVuZXIoc2xpZGVyTGlzdGVuZXIpCiAgICAgICAgYmx1ZVNlZWsuc2V0T25TZWVrQmFyQ2hhbmdlTGlzdGVuZXIoc2xpZGVyTGlzdGVuZXIpCgogICAgICAgIGhleElucHV0LmFkZFRleHRDaGFuZ2VkTGlzdGVuZXIob2JqZWN0IDogVGV4dFdhdGNoZXIgewogICAgICAgICAgICBvdmVycmlkZSBmdW4gYmVmb3JlVGV4dENoYW5nZWQoczogQ2hhclNlcXVlbmNlPywgYTogSW50LCBiOiBJbnQsIGM6IEludCkge30KICAgICAgICAgICAgb3ZlcnJpZGUgZnVuIG9uVGV4dENoYW5nZWQoczogQ2hhclNlcXVlbmNlPywgYTogSW50LCBiOiBJbnQsIGM6IEludCkge30KICAgICAgICAgICAgb3ZlcnJpZGUgZnVuIGFmdGVyVGV4dENoYW5nZWQoczogRWRpdGFibGU/KSB7CiAgICAgICAgICAgICAgICBpZiAoaXNTeW5jaW5nKSByZXR1cm4KICAgICAgICAgICAgICAgIHZhbCBwYXJzZWQgPSBwYXJzZUhleE9yTnVsbChzPy50b1N0cmluZygpKSA/OiByZXR1cm4KICAgICAgICAgICAgICAgIGlzU3luY2luZyA9IHRydWUKICAgICAgICAgICAgICAgIHByZXZpZXcuc2V0QmFja2dyb3VuZENvbG9yKHBhcnNlZCkKICAgICAgICAgICAgICAgIHJlZFNlZWsucHJvZ3Jlc3MgPSBDb2xvci5yZWQocGFyc2VkKQogICAgICAgICAgICAgICAgZ3JlZW5TZWVrLnByb2dyZXNzID0gQ29sb3IuZ3JlZW4ocGFyc2VkKQogICAgICAgICAgICAgICAgYmx1ZVNlZWsucHJvZ3Jlc3MgPSBDb2xvci5ibHVlKHBhcnNlZCkKICAgICAgICAgICAgICAgIGlzU3luY2luZyA9IGZhbHNlCiAgICAgICAgICAgIH0KICAgICAgICB9KQoKICAgICAgICAvLyBQYWxldGEgZGUgc3dhdGNoZXMgcsOhcGlkb3M6IGxpbmhhIGhvcml6b250YWwgcm9sw6F2ZSBjb20gY29yZXMKICAgICAgICAvLyBNYXRlcmlhbCBjb211bnMgKyBhIGNvciBhdHVhbG1lbnRlIHNlbGVjaW9uYWRhIGVtIGRlc3RhcXVlCiAgICAgICAgLy8gKGJvcmRhIG1haXMgZ3Jvc3NhKS4gVG9jYXIgdW0gc3dhdGNoIGFwbGljYSBhIGNvciBuYSBob3JhIG5vcwogICAgICAgIC8vIG91dHJvcyBkb2lzIGNvbnRyb2xlcyAoaGV4ICsgc2xpZGVycyksIHNlbSBmZWNoYXIgbyBkacOhbG9nbyDigJQKICAgICAgICAvLyBvIHVzdcOhcmlvIGFpbmRhIHBvZGUgcmVmaW5hciBjb20gb3Mgc2xpZGVycy9oZXggZGVwb2lzLgogICAgICAgIHZhbCBwYWxldHRlU2Nyb2xsID0gSG9yaXpvbnRhbFNjcm9sbFZpZXcoY29udGV4dCkuYXBwbHkgewogICAgICAgICAgICBpc0hvcml6b250YWxTY3JvbGxCYXJFbmFibGVkID0gZmFsc2UKICAgICAgICB9CiAgICAgICAgdmFsIHBhbGV0dGVSb3cgPSBMaW5lYXJMYXlvdXQoY29udGV4dCkuYXBwbHkgewogICAgICAgICAgICBvcmllbnRhdGlvbiA9IExpbmVhckxheW91dC5IT1JJWk9OVEFMCiAgICAgICAgfQogICAgICAgIHBhbGV0dGVTY3JvbGwuYWRkVmlldyhwYWxldHRlUm93KQoKICAgICAgICBsYXRlaW5pdCB2YXIgcmVmcmVzaFBhbGV0dGVTZWxlY3Rpb246ICgpIC0+IFVuaXQKICAgICAgICB2YWwgc3dhdGNoVmlld3MgPSBtdXRhYmxlTGlzdE9mPFBhaXI8SW50LCBWaWV3Pj4oKQoKICAgICAgICBmb3IgKHN3YXRjaENvbG9yIGluIFhBVUxJTlhTX0FMTEFQUFNfQ09MT1JfUEFMRVRURSkgewogICAgICAgICAgICB2YWwgc3dhdGNoID0gVmlldyhjb250ZXh0KS5hcHBseSB7CiAgICAgICAgICAgICAgICBiYWNrZ3JvdW5kID0gR3JhZGllbnREcmF3YWJsZSgpLmFwcGx5IHsKICAgICAgICAgICAgICAgICAgICBzaGFwZSA9IEdyYWRpZW50RHJhd2FibGUuT1ZBTAogICAgICAgICAgICAgICAgICAgIHNldENvbG9yKHN3YXRjaENvbG9yKQogICAgICAgICAgICAgICAgICAgIHNldFN0cm9rZSgoMiAqIGRlbnNpdHkpLnRvSW50KCksIENvbG9yLmFyZ2IoNjAsIDAsIDAsIDApKQogICAgICAgICAgICAgICAgfQogICAgICAgICAgICAgICAgbGF5b3V0UGFyYW1zID0gTGluZWFyTGF5b3V0LkxheW91dFBhcmFtcyhzd2F0Y2hTaXplUHgsIHN3YXRjaFNpemVQeCkuYXBwbHkgewogICAgICAgICAgICAgICAgICAgIG1hcmdpbkVuZCA9IHN3YXRjaE1hcmdpblB4CiAgICAgICAgICAgICAgICB9CiAgICAgICAgICAgICAgICBzZXRPbkNsaWNrTGlzdGVuZXIgewogICAgICAgICAgICAgICAgICAgIHVwZGF0ZUZyb21Db2xvcihzd2F0Y2hDb2xvcikKICAgICAgICAgICAgICAgICAgICByZWZyZXNoUGFsZXR0ZVNlbGVjdGlvbigpCiAgICAgICAgICAgICAgICB9CiAgICAgICAgICAgIH0KICAgICAgICAgICAgc3dhdGNoVmlld3MgKz0gc3dhdGNoQ29sb3IgdG8gc3dhdGNoCiAgICAgICAgICAgIHBhbGV0dGVSb3cuYWRkVmlldyhzd2F0Y2gpCiAgICAgICAgfQoKICAgICAgICByZWZyZXNoUGFsZXR0ZVNlbGVjdGlvbiA9IHsKICAgICAgICAgICAgdmFsIHNlbGVjdGVkID0gY3VycmVudFNsaWRlckNvbG9yKCkKICAgICAgICAgICAgZm9yICgoc3dhdGNoQ29sb3IsIHN3YXRjaFZpZXcpIGluIHN3YXRjaFZpZXdzKSB7CiAgICAgICAgICAgICAgICB2YWwgaXNTZWxlY3RlZCA9IHN3YXRjaENvbG9yID09IHNlbGVjdGVkCiAgICAgICAgICAgICAgICAoc3dhdGNoVmlldy5iYWNrZ3JvdW5kIGFzIEdyYWRpZW50RHJhd2FibGUpLnNldFN0cm9rZSgKICAgICAgICAgICAgICAgICAgICAoKGlmIChpc1NlbGVjdGVkKSA0IGVsc2UgMikgKiBkZW5zaXR5KS50b0ludCgpLAogICAgICAgICAgICAgICAgICAgIGlmIChpc1NlbGVjdGVkKSBzZWxlY3RlZCBlbHNlIENvbG9yLmFyZ2IoNjAsIDAsIDAsIDApLAogICAgICAgICAgICAgICAgKQogICAgICAgICAgICB9CiAgICAgICAgfQoKICAgICAgICByZWZyZXNoUGFsZXR0ZVNlbGVjdGlvbigpCgogICAgICAgIHZhbCBjb250YWluZXIgPSBMaW5lYXJMYXlvdXQoY29udGV4dCkuYXBwbHkgewogICAgICAgICAgICBvcmllbnRhdGlvbiA9IExpbmVhckxheW91dC5WRVJUSUNBTAogICAgICAgICAgICBzZXRQYWRkaW5nKHBhZGRpbmdQeCwgcGFkZGluZ1B4LCBwYWRkaW5nUHgsIHBhZGRpbmdQeCkKICAgICAgICAgICAgYWRkVmlldygKICAgICAgICAgICAgICAgIHByZXZpZXcsCiAgICAgICAgICAgICAgICBMaW5lYXJMYXlvdXQuTGF5b3V0UGFyYW1zKHByZXZpZXdTaXplUHgsIHByZXZpZXdTaXplUHgpLmFwcGx5IHsKICAgICAgICAgICAgICAgICAgICBncmF2aXR5ID0gR3Jhdml0eS5DRU5URVJfSE9SSVpPTlRBTAogICAgICAgICAgICAgICAgICAgIGJvdHRvbU1hcmdpbiA9IHBhZGRpbmdQeCAvIDIKICAgICAgICAgICAgICAgIH0sCiAgICAgICAgICAgICkKICAgICAgICAgICAgYWRkVmlldygKICAgICAgICAgICAgICAgIHBhbGV0dGVTY3JvbGwsCiAgICAgICAgICAgICAgICBMaW5lYXJMYXlvdXQuTGF5b3V0UGFyYW1zKAogICAgICAgICAgICAgICAgICAgIExpbmVhckxheW91dC5MYXlvdXRQYXJhbXMuTUFUQ0hfUEFSRU5ULAogICAgICAgICAgICAgICAgICAgIExpbmVhckxheW91dC5MYXlvdXRQYXJhbXMuV1JBUF9DT05URU5ULAogICAgICAgICAgICAgICAgKS5hcHBseSB7IGJvdHRvbU1hcmdpbiA9IHBhZGRpbmdQeCAvIDIgfSwKICAgICAgICAgICAgKQogICAgICAgICAgICBhZGRWaWV3KHJlZFJvdykKICAgICAgICAgICAgYWRkVmlldyhncmVlblJvdykKICAgICAgICAgICAgYWRkVmlldyhibHVlUm93KQogICAgICAgICAgICBhZGRWaWV3KGhleElucHV0KQogICAgICAgIH0KCiAgICAgICAgQWxlcnREaWFsb2cuQnVpbGRlcihjb250ZXh0KQogICAgICAgICAgICAuc2V0VGl0bGUoUi5zdHJpbmcueGF1bGlueHNfYWxsYXBwc19jb2xvcl9waWNrZXJfdGl0bGUpCiAgICAgICAgICAgIC5zZXRWaWV3KGNvbnRhaW5lcikKICAgICAgICAgICAgLnNldFBvc2l0aXZlQnV0dG9uKFIuc3RyaW5nLnhhdWxpbnhzX21hbnVhbF9jb2xvcl9zYXZlKSB7IF8sIF8gLT4KICAgICAgICAgICAgICAgIHZhbCBwYXJzZWQgPSBwYXJzZUhleE9yTnVsbChoZXhJbnB1dC50ZXh0Py50b1N0cmluZygpKSA/OiBjdXJyZW50U2xpZGVyQ29sb3IoKQogICAgICAgICAgICAgICAgcHJlZnMucHV0KFhhdWxpblhzQWxsQXBwc0NvbG9yLkFMTEFQUFNfQ09MT1JfQVJHQiwgcGFyc2VkIG9yIC0weDEwMDAwMDApCiAgICAgICAgICAgICAgICB1cGRhdGVTdW1tYXJ5KCkKICAgICAgICAgICAgICAgIGNvbS54YXVsaW54cy5jdXN0b21pemF0aW9ucy50aGVtZS5YYXVsaW5Yc0FsbEFwcHNUcmFuc3BhcmVuY3lSZWRyYXcucmVxdWVzdFJlZHJhdyhjb250ZXh0KQogICAgICAgICAgICB9CiAgICAgICAgICAgIC5zZXROZWdhdGl2ZUJ1dHRvbihhbmRyb2lkLlIuc3RyaW5nLmNhbmNlbCwgbnVsbCkKICAgICAgICAgICAgLnNob3coKQogICAgfQoKICAgIHByaXZhdGUgZnVuIHVwZGF0ZVN1bW1hcnkoKSB7CiAgICAgICAgdmFsIGNvbG9yID0gTGF1bmNoZXJQcmVmcy5nZXQoY29udGV4dCkuZ2V0KFhhdWxpblhzQWxsQXBwc0NvbG9yLkFMTEFQUFNfQ09MT1JfQVJHQikKICAgICAgICBzdW1tYXJ5ID0gU3RyaW5nLmZvcm1hdCgiIyUwNlgiLCAweEZGRkZGRiBhbmQgY29sb3IpCiAgICB9CgogICAgcHJpdmF0ZSBmdW4gcGFyc2VIZXhPck51bGwoaW5wdXQ6IFN0cmluZz8pOiBJbnQ/IHsKICAgICAgICBpZiAoaW5wdXQuaXNOdWxsT3JCbGFuaygpKSByZXR1cm4gbnVsbAogICAgICAgIHZhbCBjbGVhbiA9IGlucHV0LnJlbW92ZVByZWZpeCgiIyIpLnRyaW0oKQogICAgICAgIGlmIChjbGVhbi5sZW5ndGggIT0gNiAmJiBjbGVhbi5sZW5ndGggIT0gOCkgcmV0dXJuIG51bGwKICAgICAgICByZXR1cm4gdHJ5IHsKICAgICAgICAgICAgdmFsIGFyZ2IgPSBpZiAoY2xlYW4ubGVuZ3RoID09IDYpICJGRiRjbGVhbiIgZWxzZSBjbGVhbgogICAgICAgICAgICAoYXJnYi50b0xvbmcoMTYpIGFuZCAweEZGRkZGRkZGTCkudG9JbnQoKQogICAgICAgIH0gY2F0Y2ggKGU6IE51bWJlckZvcm1hdEV4Y2VwdGlvbikgewogICAgICAgICAgICBudWxsCiAgICAgICAgfQogICAgfQoKICAgIGNvbXBhbmlvbiBvYmplY3QgewogICAgICAgIC8vIFBhbGV0YSBmaXhhIGRlIGNvcmVzIE1hdGVyaWFsIGNvbXVucyAodG9ucyA0MDAtNzAwLCBqw6EgQVJHQgogICAgICAgIC8vIG9wYWNvcykgcGFyYSBzZWxlw6fDo28gcsOhcGlkYSDigJQgbsOjbyBkZXBlbmRlIGRlIHdhbGxwYXBlci9Nb25ldCwKICAgICAgICAvLyBqw6EgcXVlIGVzdGEgZmVhdHVyZSBleGlzdGUganVzdGFtZW50ZSBwYXJhIG8gY2FzbyBkZSBvIHVzdcOhcmlvCiAgICAgICAgLy8gcXVlcmVyIHVtYSBjb3IgZml4YSBwcsOzcHJpYS4KICAgICAgICBwcml2YXRlIHZhbCBYQVVMSU5YU19BTExBUFBTX0NPTE9SX1BBTEVUVEUgPSBpbnRBcnJheU9mKAogICAgICAgICAgICAweEZGRTUzOTM1LnRvSW50KCksIC8vIHZlcm1lbGhvCiAgICAgICAgICAgIDB4RkZEODFCNjAudG9JbnQoKSwgLy8gcm9zYQogICAgICAgICAgICAweEZGOEUyNEFBLnRvSW50KCksIC8vIHJveG8KICAgICAgICAgICAgMHhGRjVFMzVCMS50b0ludCgpLCAvLyByb3hvIHByb2Z1bmRvCiAgICAgICAgICAgIDB4RkYzOTQ5QUIudG9JbnQoKSwgLy8gw61uZGlnbwogICAgICAgICAgICAweEZGMUU4OEU1LnRvSW50KCksIC8vIGF6dWwKICAgICAgICAgICAgMHhGRjAwODk3Qi50b0ludCgpLCAvLyB2ZXJkZS1henVsYWRvCiAgICAgICAgICAgIDB4RkY0M0EwNDcudG9JbnQoKSwgLy8gdmVyZGUKICAgICAgICAgICAgMHhGRkZERDgzNS50b0ludCgpLCAvLyBhbWFyZWxvCiAgICAgICAgICAgIDB4RkZGQjhDMDAudG9JbnQoKSwgLy8gbGFyYW5qYQogICAgICAgICAgICAweEZGNkQ0QzQxLnRvSW50KCksIC8vIG1hcnJvbQogICAgICAgICAgICAweEZGNTQ2RTdBLnRvSW50KCksIC8vIGF6dWwgYWNpbnplbnRhZG8KICAgICAgICAgICAgMHhGRjAwMDAwMC50b0ludCgpLCAvLyBwcmV0bwogICAgICAgICAgICAweEZGRkZGRkZGLnRvSW50KCksIC8vIGJyYW5jbwogICAgICAgICkKICAgIH0KfQoKLy8gWEFVTElOWFNfQUxMQVBQU19DT0xPUl9QSUNLRVJfUFJFRkVSRU5DRV9GSUxFCg==",
}


def main() -> int:
    print("=== XaulinXsLauncher3 — QSB largura 200% + cor manual do menu de apps ===\\n")

    patch_unique(QSB_CONFIG_PATH, QSB_CONFIG_OLD, QSB_CONFIG_NEW, QSB_CONFIG_MARKER,
                 "QsbConfig.kt (MAX_WIDTH_PERCENT 100->200)")

    patch_unique(OSE_WIDGET_VIEW_PATH, OSE_WIDGET_VIEW_OLD, OSE_WIDGET_VIEW_NEW, OSE_WIDGET_VIEW_MARKER,
                 "OseWidgetView.kt (fix Largura via scaleX)")

    patch_unique(ALLAPPS_CONTAINER_PATH, ALLAPPS_CONTAINER_OLD, ALLAPPS_CONTAINER_NEW, ALLAPPS_CONTAINER_MARKER,
                 "ActivityAllAppsContainerView.java (gancho cor manual)")

    write_new_file(ALLAPPS_COLOR_DATA_PATH, NEW_FILES_B64["allapps_color_data"],
                    "XAULINXS_ALLAPPS_COLOR_DATA_FILE", "XaulinXsAllAppsColor.kt (novo)")

    write_new_file(ALLAPPS_COLOR_ENABLED_PREF_PATH, NEW_FILES_B64["allapps_color_enabled_pref"],
                    "XAULINXS_ALLAPPS_COLOR_ENABLED_PREFERENCE_FILE", "AllAppsColorEnabledPreference.kt (novo)")

    write_new_file(ALLAPPS_COLOR_PICKER_PREF_PATH, NEW_FILES_B64["allapps_color_picker_pref"],
                    "XAULINXS_ALLAPPS_COLOR_PICKER_PREFERENCE_FILE", "AllAppsColorPickerPreference.kt (novo)")

    patch_unique(LAUNCHER_PREFS_PATH, LAUNCHER_PREFS_OLD, LAUNCHER_PREFS_NEW, LAUNCHER_PREFS_MARKER,
                 "launcher_preferences.xml (entradas da categoria Menu de aplicativo)")

    patch_unique(STRINGS_PATH, STRINGS_OLD, STRINGS_NEW, STRINGS_MARKER,
                 "xaulinxs_strings.xml (novas strings)")

    print()
    if EXIT_CODE == 0:
        print("=== Tudo aplicado (ou já estava aplicado) sem conflitos. ===")
    else:
        print("=== Concluído com CONFLITOS em um ou mais arquivos — veja acima. ===", file=sys.stderr)
    return EXIT_CODE


if __name__ == "__main__":
    sys.exit(main())
