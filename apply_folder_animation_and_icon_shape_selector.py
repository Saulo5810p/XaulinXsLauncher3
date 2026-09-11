#!/usr/bin/env python3
"""
XaulinXs Customizations - Reativação da animação elástica de pasta +
Seletor de formato de ícone.

1) Reativa enableExpressiveFolderExpansion() e enableLauncherIconShapes()
   no stub Flags.java (estavam em false desde a reversão do popup Compose).
   Atenção: enableLauncherIconShapes muda DatabaseHelper.SCHEMA_VERSION de
   32->34 (efeito colateral já conhecido e aceito em sessão anterior).

2) Novos arquivos:
   - IconShapeSwatchView.kt: view que desenha o formato REAL de um
     IconShapeModel (usa o mesmo pathString/PathParser que o ThemeManager
     usa pra recortar os ícones de verdade).
   - IconShapeSelectorPreference.kt: Preference custom que monta a barra
     horizontal de quadradinhos (um por formato disponível), escreve
     direto em ThemeManager.PREF_ICON_SHAPE - o próprio ThemeManager já
     escuta essa key e propaga a mudança pra workspace/gaveta sozinho.
   - xaulinxs_icon_shape_selector.xml: layout da preference (título +
     resumo padrão + barra de swatches).
   - xaulinxs_icon_shape_dimens.xml: dimens isoladas da feature.

3) Registra a preference na categoria "Ícone" das configurações
   (xaulinxs_cat_icon) e adiciona as 2 strings de título/resumo.

A lista de formatos vem de ShapesProvider.iconShapes, que já muda
sozinha conforme a flag enableLauncherIconShapes (1 formato desligada,
5 ligada) - nada aqui precisa mudar se a flag for religada/desligada de
novo no futuro.

Uso:
    python3 apply_folder_animation_and_icon_shape_selector.py /caminho/para/XaulinXsLauncher3

Idempotente: rodar de novo não duplica nada.
"""

import sys
import pathlib

# ---------------------------------------------------------------------------
# 1) Flags.java
# ---------------------------------------------------------------------------

FLAGS_MARKER = "XaulinXs: animação elástica de pasta + habilita seletor de formato"

FLAGS_PRIOR_FOLDER = '    public static boolean enableExpressiveFolderExpansion() { return false; }'
FLAGS_NEW_FOLDER = (
    '    public static boolean enableExpressiveFolderExpansion() { return true; } '
    '// XaulinXs: animação elástica de pasta + habilita seletor de formato de ícone junto com enableLauncherIconShapes'
)

FLAGS_PRIOR_SHAPES = '    public static boolean enableLauncherIconShapes() { return false; }'
FLAGS_NEW_SHAPES = (
    '    public static boolean enableLauncherIconShapes() { return true; } '
    '// XaulinXs: 5 formatos de ícone (círculo/quadrado/cookie4/cookie7/arco) via ShapesProvider + muda DatabaseHelper.SCHEMA_VERSION 32->34'
)

# ---------------------------------------------------------------------------
# 2) Novos arquivos Kotlin/XML
# ---------------------------------------------------------------------------

SWATCH_VIEW_MARKER = "Quadradinho selecionável que desenha o formato REAL"
SWATCH_VIEW_CONTENT = '''/*
 * XaulinXs Customizations — não faz parte do AOSP original.
 *
 * Quadradinho selecionável que desenha o formato REAL de um
 * IconShapeModel (mesmo pathString usado por ThemeManager pra recortar
 * os ícones de verdade) — não é um ícone decorativo aproximado, é o
 * mesmo contorno vetorial que o launcher aplica quando esse shape é
 * escolhido. O path SVG-like de ShapesProvider usa um viewport 0-100;
 * aqui ele é escalado pro tamanho real da view via Matrix.
 */
package com.xaulinxs.customizations.icons

import android.content.Context
import android.graphics.Canvas
import android.graphics.Matrix
import android.graphics.Paint
import android.graphics.Path
import android.graphics.RectF
import android.util.AttributeSet
import android.view.View
import androidx.core.graphics.PathParser
import com.android.launcher3.shapes.IconShapeModel

private const val PATH_VIEWPORT_SIZE = 100f

/**
 * Desenha [shape] preenchido, com um contorno de seleção quando [isSelected]
 * é true. Clique/seleção são tratados pelo container (a barra), esta view só
 * desenha e expõe [isSelected] como estado visual.
 */
class IconShapeSwatchView @JvmOverloads constructor(
    context: Context,
    attrs: AttributeSet? = null,
) : View(context, attrs) {

    private val fillPaint = Paint(Paint.ANTI_ALIAS_FLAG).apply { style = Paint.Style.FILL }
    private val strokePaint = Paint(Paint.ANTI_ALIAS_FLAG).apply { style = Paint.Style.STROKE }
    private val rawPath = Path()
    private val scaledPath = Path()
    private val matrix = Matrix()

    var shape: IconShapeModel? = null
        set(value) {
            field = value
            rawPath.reset()
            value?.let { runCatching { rawPath.set(PathParser.createPathFromPathData(it.pathString)) } }
            updateScaledPath()
            invalidate()
        }

    var fillColor: Int = 0
        set(value) {
            field = value
            fillPaint.color = value
            invalidate()
        }

    var strokeColor: Int = 0
        set(value) {
            field = value
            strokePaint.color = value
            invalidate()
        }

    var strokeWidthPx: Float = 0f
        set(value) {
            field = value
            strokePaint.strokeWidth = value
            updateScaledPath()
            invalidate()
        }

    var isSwatchSelected: Boolean = false
        set(value) {
            field = value
            invalidate()
        }

    override fun onSizeChanged(w: Int, h: Int, oldw: Int, oldh: Int) {
        super.onSizeChanged(w, h, oldw, oldh)
        updateScaledPath()
    }

    private fun updateScaledPath() {
        scaledPath.reset()
        if (rawPath.isEmpty || width <= 0 || height <= 0) return
        // Encolhe um pouco o viewport pra sobrar espaço pro stroke de
        // seleção não ser cortado nas bordas da view.
        val inset = strokeWidthPx.coerceAtLeast(1f) * 2f
        val target = RectF(inset, inset, width - inset, height - inset)
        matrix.reset()
        matrix.setRectToRect(
            RectF(0f, 0f, PATH_VIEWPORT_SIZE, PATH_VIEWPORT_SIZE),
            target,
            Matrix.ScaleToFit.CENTER,
        )
        rawPath.transform(matrix, scaledPath)
    }

    override fun onDraw(canvas: Canvas) {
        super.onDraw(canvas)
        if (scaledPath.isEmpty) return
        canvas.drawPath(scaledPath, fillPaint)
        if (isSwatchSelected) {
            canvas.drawPath(scaledPath, strokePaint)
        }
    }
}
'''

SELECTOR_PREF_MARKER = "Barra de quadradinhos selecionáveis (um por vez) com o formato REAL"
SELECTOR_PREF_CONTENT = '''/*
 * XaulinXs Customizations — não faz parte do AOSP original.
 *
 * Barra de quadradinhos selecionáveis (um por vez) com o formato REAL de
 * cada IconShapeModel disponível em ShapesProvider — a lista muda sozinha
 * conforme Flags.enableLauncherIconShapes(): com a flag ligada, ganha os
 * 5 formatos (círculo/quadrado/cookie 4/cookie 7/arco) que o próprio AOSP
 * já implementa via ThemeManager; com a flag desligada, sobra só círculo.
 *
 * Não existe lógica de aplicação de formato aqui: escreve a key escolhida
 * direto em ThemeManager.PREF_ICON_SHAPE (LauncherPrefs), que o próprio
 * ThemeManager já escuta (verifyIconState() via LauncherPrefChangeListener)
 * e propaga pra workspace/gaveta de apps sozinho. String vazia = padrão
 * (comportamento idêntico a nunca ter mexido nessa preference).
 */
package com.xaulinxs.customizations.settings

import android.content.Context
import android.graphics.Color
import android.util.AttributeSet
import android.util.TypedValue
import android.widget.LinearLayout
import androidx.preference.Preference
import androidx.preference.PreferenceViewHolder
import com.android.launcher3.LauncherPrefs
import com.android.launcher3.R
import com.android.launcher3.graphics.ThemeManager
import com.android.launcher3.shapes.ShapesProvider
import com.xaulinxs.customizations.icons.IconShapeSwatchView

class IconShapeSelectorPreference @JvmOverloads constructor(
    context: Context,
    attrs: AttributeSet? = null,
) : Preference(context, attrs) {

    private val swatchSizePx = (48 * context.resources.displayMetrics.density).toInt()
    private val swatchGapPx = (12 * context.resources.displayMetrics.density).toInt()
    private val strokeWidthPx = 2.5f * context.resources.displayMetrics.density

    init {
        isPersistent = false
        isSelectable = false
        layoutResource = R.layout.xaulinxs_icon_shape_selector
    }

    override fun onBindViewHolder(holder: PreferenceViewHolder) {
        super.onBindViewHolder(holder)
        val container = holder.itemView.findViewById<LinearLayout>(
            R.id.xaulinxs_icon_shape_row
        )
        container.removeAllViews()

        val shapes = ShapesProvider.iconShapes
        val storedKey = LauncherPrefs.get(context).get(ThemeManager.PREF_ICON_SHAPE)
        val swatches = mutableListOf<Pair<IconShapeSwatchView, String>>()

        shapes.forEach { shapeModel ->
            val swatch = IconShapeSwatchView(context).apply {
                layoutParams = LinearLayout.LayoutParams(swatchSizePx, swatchSizePx).apply {
                    marginEnd = swatchGapPx
                }
                shape = shapeModel
                fillColor = resolveNeutralFillColor()
                strokeColor = resolveAccentStrokeColor()
                this.strokeWidthPx = this@IconShapeSelectorPreference.strokeWidthPx
                contentDescription = context.getString(shapeModel.titleId)
                // Chave vazia = padrão: representamos isso selecionando o
                // primeiro shape da lista (círculo, sempre índice 0, com a
                // flag ligada ou desligada), pra sempre existir exatamente
                // um quadradinho marcado, mesmo antes de qualquer toque.
                isSwatchSelected = storedKey == shapeModel.key ||
                    (storedKey.isEmpty() && shapeModel === shapes.first())
            }
            swatches += swatch to shapeModel.key
            container.addView(swatch)
        }

        swatches.forEach { (swatch, key) ->
            swatch.setOnClickListener {
                LauncherPrefs.get(context).put(ThemeManager.PREF_ICON_SHAPE, key)
                swatches.forEach { (s, k) -> s.isSwatchSelected = (k == key) }
            }
        }
    }

    private fun resolveNeutralFillColor(): Int {
        val typedValue = TypedValue()
        return if (context.theme.resolveAttribute(
                android.R.attr.textColorSecondary, typedValue, true
            )
        ) {
            typedValue.data
        } else {
            Color.GRAY
        }
    }

    private fun resolveAccentStrokeColor(): Int {
        val typedValue = TypedValue()
        return if (context.theme.resolveAttribute(
                android.R.attr.colorAccent, typedValue, true
            )
        ) {
            typedValue.data
        } else {
            Color.WHITE
        }
    }
}
'''

LAYOUT_MARKER = "IconShapeSelectorPreference: título e resumo"
LAYOUT_CONTENT = '''<?xml version="1.0" encoding="utf-8"?>
<!--
     XaulinXs Customizations — não faz parte do AOSP original.
     Layout custom da IconShapeSelectorPreference: título e resumo no
     mesmo formato/IDs padrão de qualquer androidx.preference.Preference
     (@android:id/title, @android:id/summary), com a barra de
     quadradinhos de formato logo abaixo, dentro da mesma preference —
     não é um dialog separado.
-->
<LinearLayout
    xmlns:android="http://schemas.android.com/apk/res/android"
    android:layout_width="match_parent"
    android:layout_height="wrap_content"
    android:orientation="vertical"
    android:paddingStart="16dp"
    android:paddingEnd="16dp"
    android:paddingTop="12dp"
    android:paddingBottom="16dp"
    android:minHeight="?android:attr/listPreferredItemHeightSmall">

    <TextView
        android:id="@android:id/title"
        android:layout_width="match_parent"
        android:layout_height="wrap_content"
        android:textAppearance="?android:attr/textAppearanceListItem"
        android:textColor="?android:attr/textColorPrimary"
        android:ellipsize="marquee" />

    <TextView
        android:id="@android:id/summary"
        android:layout_width="match_parent"
        android:layout_height="wrap_content"
        android:layout_marginTop="2dp"
        android:textAppearance="?android:attr/textAppearanceListItemSecondary"
        android:textColor="?android:attr/textColorSecondary" />

    <HorizontalScrollView
        android:layout_width="match_parent"
        android:layout_height="wrap_content"
        android:layout_marginTop="@dimen/xaulinxs_icon_shape_row_top_margin"
        android:scrollbars="none"
        android:clipToPadding="false">

        <LinearLayout
            android:id="@+id/xaulinxs_icon_shape_row"
            android:layout_width="wrap_content"
            android:layout_height="wrap_content"
            android:orientation="horizontal"
            android:gravity="center_vertical" />

    </HorizontalScrollView>

</LinearLayout>
'''

DIMENS_MARKER = "barra de formato de ícone"
DIMENS_CONTENT = '''<?xml version="1.0" encoding="utf-8"?>
<!--
     XaulinXs Customizations — barra de formato de ícone.
     Arquivo isolado, mesmo padrão de xaulinxs_popup_dimens.xml: fácil de
     revisar/remover essa feature específica sem mexer em outras dimens.
-->
<resources>
    <dimen name="xaulinxs_icon_shape_row_top_margin">10dp</dimen>
</resources>
'''

# ---------------------------------------------------------------------------
# 3) strings.xml + launcher_preferences.xml (edições em arquivos existentes)
# ---------------------------------------------------------------------------

STRINGS_MARKER = "xaulinxs_icon_shape_title"
STRINGS_ANCHOR = (
    '    <string name="xaulinxs_legacy_icon_bg_shadow_summary">Apps antigos sem ícone '
    'adaptativo ganham hoje um fundo branco sintético + sombra; ativando isso, o fundo '
    'vira transparente e a sombra some (ícones adaptativos modernos não são afetados)</string>\n'
)
STRINGS_ADDITION = (
    STRINGS_ANCHOR.rstrip('\n') + '\n\n'
    '    <!-- Formato do ícone: barra de quadradinhos selecionáveis, um formato\n'
    '         por vez. A lista de formatos disponíveis vem de ShapesProvider e\n'
    '         muda sozinha conforme Flags.enableLauncherIconShapes() - com 1\n'
    '         formato (círculo) ou 5, dependendo da flag, sem precisar tocar\n'
    '         nesta string/preference quando a flag mudar de novo no futuro. -->\n'
    '    <string name="xaulinxs_icon_shape_title">Formato do ícone</string>\n'
    '    <string name="xaulinxs_icon_shape_summary">Toque num formato pra aplicar a todos '
    'os ícones e pastas. O primeiro (círculo) é o padrão</string>\n'
)

PREFS_XML_MARKER = "xaulinxs_icon_shape"
PREFS_XML_ANCHOR = (
    '                android:key="xaulinxs_legacy_icon_bg_shadow_removed"\n'
    '                android:title="@string/xaulinxs_legacy_icon_bg_shadow_title"\n'
    '                android:summary="@string/xaulinxs_legacy_icon_bg_shadow_summary"\n'
    '                android:persistent="false" />\n'
    '\n'
    '        </PreferenceScreen>'
)
PREFS_XML_ADDITION = (
    '                android:key="xaulinxs_legacy_icon_bg_shadow_removed"\n'
    '                android:title="@string/xaulinxs_legacy_icon_bg_shadow_title"\n'
    '                android:summary="@string/xaulinxs_legacy_icon_bg_shadow_summary"\n'
    '                android:persistent="false" />\n'
    '\n'
    '            <com.xaulinxs.customizations.settings.IconShapeSelectorPreference\n'
    '                android:key="xaulinxs_icon_shape"\n'
    '                android:title="@string/xaulinxs_icon_shape_title"\n'
    '                android:summary="@string/xaulinxs_icon_shape_summary"\n'
    '                android:persistent="false" />\n'
    '\n'
    '        </PreferenceScreen>'
)


def patch_flags(repo: pathlib.Path) -> bool:
    path = repo / "aosp-stubs/com/android/launcher3/Flags.java"
    if not path.exists():
        print(f"[ERRO] {path} não encontrado.")
        return False
    content = path.read_text(encoding="utf-8")
    if FLAGS_MARKER in content and "enableLauncherIconShapes() { return true; }" in content:
        print("[SKIP] Flags.java: já reativado (idempotente).")
        return True

    changed = content
    if FLAGS_PRIOR_FOLDER in changed:
        changed = changed.replace(FLAGS_PRIOR_FOLDER, FLAGS_NEW_FOLDER, 1)
    elif "enableExpressiveFolderExpansion() { return true; }" not in changed:
        print("[ERRO] Flags.java: linha de enableExpressiveFolderExpansion não encontrada "
              "no formato esperado — não mexido, verifique manualmente.")
        return False

    if FLAGS_PRIOR_SHAPES in changed:
        changed = changed.replace(FLAGS_PRIOR_SHAPES, FLAGS_NEW_SHAPES, 1)
    elif "enableLauncherIconShapes() { return true; }" not in changed:
        print("[ERRO] Flags.java: linha de enableLauncherIconShapes não encontrada "
              "no formato esperado — não mexido, verifique manualmente.")
        return False

    if changed == content:
        print("[SKIP] Flags.java: nada a mudar (idempotente).")
        return True

    path.write_text(changed, encoding="utf-8")
    print("[OK]   Flags.java: enableExpressiveFolderExpansion + enableLauncherIconShapes reativadas.")
    return True


def write_new_file(path: pathlib.Path, content: str, marker: str, label: str) -> bool:
    if path.exists():
        current = path.read_text(encoding="utf-8")
        if marker in current:
            print(f"[SKIP] {label}: já existe (idempotente).")
            return True
        print(f"[ERRO] {label}: arquivo já existe com conteúdo diferente do esperado — "
              f"abortando esta parte sem sobrescrever.")
        return False
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")
    print(f"[OK]   {label}: criado.")
    return True


def patch_strings(repo: pathlib.Path) -> bool:
    path = repo / "res/values/xaulinxs_strings.xml"
    if not path.exists():
        print(f"[ERRO] {path} não encontrado.")
        return False
    content = path.read_text(encoding="utf-8")
    if STRINGS_MARKER in content:
        print("[SKIP] xaulinxs_strings.xml: já aplicado (idempotente).")
        return True
    if STRINGS_ANCHOR not in content:
        print("[ERRO] xaulinxs_strings.xml: âncora de inserção não encontrada — "
              "arquivo pode ter sido editado manualmente. Abortando sem sobrescrever.")
        return False
    new_content = content.replace(STRINGS_ANCHOR, STRINGS_ADDITION, 1)
    path.write_text(new_content, encoding="utf-8")
    print("[OK]   xaulinxs_strings.xml: strings do formato de ícone adicionadas.")
    return True


def patch_preferences_xml(repo: pathlib.Path) -> bool:
    path = repo / "res/xml/launcher_preferences.xml"
    if not path.exists():
        print(f"[ERRO] {path} não encontrado.")
        return False
    content = path.read_text(encoding="utf-8")
    if PREFS_XML_MARKER in content:
        print("[SKIP] launcher_preferences.xml: já aplicado (idempotente).")
        return True
    if PREFS_XML_ANCHOR not in content:
        print("[ERRO] launcher_preferences.xml: âncora de inserção não encontrada — "
              "arquivo pode ter sido editado manualmente. Abortando sem sobrescrever.")
        return False
    new_content = content.replace(PREFS_XML_ANCHOR, PREFS_XML_ADDITION, 1)
    path.write_text(new_content, encoding="utf-8")
    print("[OK]   launcher_preferences.xml: IconShapeSelectorPreference registrada na categoria Ícone.")
    return True


def main():
    if len(sys.argv) != 2:
        print("Uso: python3 apply_folder_animation_and_icon_shape_selector.py /caminho/para/XaulinXsLauncher3")
        sys.exit(1)

    repo = pathlib.Path(sys.argv[1]).resolve()
    if not repo.is_dir():
        print(f"[ERRO] Diretório não encontrado: {repo}")
        sys.exit(1)

    ok = True
    ok &= patch_flags(repo)
    ok &= write_new_file(
        repo / "modules/customizations/src/com/xaulinxs/customizations/icons/IconShapeSwatchView.kt",
        SWATCH_VIEW_CONTENT, SWATCH_VIEW_MARKER, "IconShapeSwatchView.kt (novo)",
    )
    ok &= write_new_file(
        repo / "modules/customizations/src/com/xaulinxs/customizations/settings/IconShapeSelectorPreference.kt",
        SELECTOR_PREF_CONTENT, SELECTOR_PREF_MARKER, "IconShapeSelectorPreference.kt (novo)",
    )
    ok &= write_new_file(
        repo / "res/layout/xaulinxs_icon_shape_selector.xml",
        LAYOUT_CONTENT, LAYOUT_MARKER, "xaulinxs_icon_shape_selector.xml (novo)",
    )
    ok &= write_new_file(
        repo / "res/values/xaulinxs_icon_shape_dimens.xml",
        DIMENS_CONTENT, DIMENS_MARKER, "xaulinxs_icon_shape_dimens.xml (novo)",
    )
    ok &= patch_strings(repo)
    ok &= patch_preferences_xml(repo)

    if not ok:
        print("\n[FALHOU] Alguma parte não pôde ser aplicada — veja os [ERRO] acima. "
              "Nada foi sobrescrito às cegas.")
        sys.exit(1)

    print("\n[SUCESSO] Animação elástica de pasta reativada. Nova barra 'Formato do ícone' "
          "disponível em Configurações > XaulinXs Customizations > Ícone. Rode "
          "assembleNoQuickstepDebug. Lembrete: enableLauncherIconShapes muda o SCHEMA_VERSION "
          "do banco (32->34) — comportamento já esperado/aceito.")


if __name__ == "__main__":
    main()
