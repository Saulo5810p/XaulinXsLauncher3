#!/usr/bin/env python3
"""
Feature 7: Barra de busca fixa, estilo QuickSearchBox, temática — versão
final e consolidada (cor + opacidade + blur + popup de modo web/texto num
único script), testada do zero contra o código-fonte.zip real. Nenhuma
versão anterior desta feature precisa ter sido aplicada — este script cria
tudo de uma vez.

INVESTIGAÇÃO — por que a barra fica embaixo da doca, sem eu precisar mexer
em layout algum:
Hotseat é um CellLayout que hospeda tanto os ícones (grid) quanto o QSB
(mQsb), e o posicionamento do QSB já é decidido pelo AOSP em
Hotseat.onMeasure()/onLayout(): a altura vem de
DeviceProfile.getHotseatProfile().getQsbHeight() (sempre > 0, lido de
R.dimen.qsb_widget_height) e ele é ancorado à parte de baixo do Hotseat,
com um offset (getQsbOffsetY()) que garante espaço reservado — os ícones
ficam no grid acima, o QSB abaixo. O único jeito do QSB aparecer do LADO
dos ícones em vez de ABAIXO é se launcher:inlineQsb estiver setado no grid
ativo — conferi res/xml/device_profiles.xml e isso só existe no grid
especial "fixed_landscape_mode" (launcher:inlineQsb="landscape"). Nenhum
grid de celular normal (5_by_5/Large Phone, 4_by_4 etc., o que um Galaxy
A35 realmente usa) declara isso, então por padrão fica false = barra
sempre embaixo, largura cheia, centralizada. Ou seja: ao trocar o que
ocupa mQsb (é isso que este script faz), a posição "abaixo da doca,
perto do fim da tela" vem de graça, sem eu precisar tocar em
onMeasure/onLayout/CellLayout. Não incluí nenhuma mudança de layout por
esse motivo — só documentei a investigação aqui pra registro.

DECISÃO DE ESCOPO — não depende de nenhuma outra feature:
A cor da barra é AUTOSSUFICIENTE (WallpaperColorHints + cor manual própria
da barra, com editor hex dedicado) e NÃO depende de nenhuma classe da
feature 5 (editor de cor manual dos ícones) porque essa feature foi feita
em outra sessão e eu não tenho o arquivo real pra confirmar a API dela —
acoplar a uma API que não pude verificar seria repetir o erro que o
HANDOFF pede pra evitar (validar contra o código real antes de usar).
Se você preferir puxar a cor da mesma fonte da feature 5 depois, é uma
troca pequena e isolada.

O QUE ESTE SCRIPT FAZ:
1. Cria modules/customizations/.../search/XaulinXsSearchBarPrefs.kt —
   todas as preferences da barra (liga/desliga, modo web/texto,
   opacidade, cor própria liga/desliga, valor da cor, blur liga/desliga).
2. Cria .../search/XaulinXsSearchBarColors.kt — cor de fundo/texto,
   auto-suficiente (cor própria > WallpaperColorHints > cinza neutro).
3. Cria .../search/XaulinXsSearchBarBlur.kt — recorta a região do
   wallpaper atrás da barra (WallpaperManager.getDrawable(), com
   try/catch total: se falhar por qualquer motivo — permissão negada,
   wallpaper animado, ROM sem suporte — a barra simplesmente não mostra
   o backdrop borrado e segue funcionando normal, sem crash).
4. Cria .../search/XaulinXsSearchBarView.kt — a View da barra em 3
   camadas (backdrop borrado opcional -> tint de cor translúcida ->
   ícone+texto nítidos), com popup de long-press pra trocar entre "busca
   na web" e "texto livre" na hora, reaproveitando o
   XaulinXsPopupBlurHelper (feature 1) pra ficar visualmente consistente
   com os outros balões de contexto do launcher.
5. Cria .../search/XaulinXsSearchBarFactory.kt — ponto único que o
   Hotseat.java consulta; retorna null (= comportamento 100% original)
   quando a feature está desativada.
6. Edita src/com/android/launcher3/Hotseat.java (AOSP) — hook cirúrgico
   no construtor: troca a criação do QSB original pela nossa fábrica,
   com fallback pro QSB original quando desativado.
7. Cria as 5 Preference classes (settings/) — todas na tela "XaulinXs
   Customizations" já existente: liga/desliga, modo web/texto, opacidade,
   cor própria liga/desliga + seletor hex, blur liga/desliga.
8. Edita res/xml/launcher_preferences.xml e res/values/xaulinxs_strings.xml
   — ancorado no fechamento do bloco (não depende de quais outras
   features você já aplicou, ao contrário de versões anteriores deste
   script que assumiam a feature 6 já aplicada).

TRADE-OFFS que você deve saber:
- Blur exige Android 12+ (API 31, RenderEffect) e depende de conseguir ler
  o wallpaper real via WallpaperManager — se sua build não tiver
  MANAGE_EXTERNAL_STORAGE concedida (isso é da feature de fonte
  customizada, que eu não pude conferir), o blur simplesmente não aparece,
  sem quebrar nada.
- A barra não implementa a interface Reorderable que o QSB original
  implementa (usada pra uma animação de translação ligada à nav bar) —
  então esse efeito específico de animação não se aplica à barra custom.
  Não afeta nenhuma outra função.
- O popup de long-press usa android.widget.PopupMenu (API padrão, sempre
  disponível) em vez de um ArrowPopup customizado — mais simples e
  suficiente pra 2 opções, mas o texto do menu segue o estilo padrão do
  sistema, não o visual "balão XaulinXs" das outras telas.
- Segurar o dedo no EditText também abre o popup de modo (troquei o
  long-press padrão de seleção de texto por isso) — é intencional, dado
  que é uma barra de busca, não um campo de edição de texto rico.

Idempotente. Rode a partir da RAIZ do repositório:
    python3 feature_search_bar_final.py
"""
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent
SEARCH_PKG = REPO_ROOT / "modules/customizations/src/com/xaulinxs/customizations/search"
SETTINGS_PKG = REPO_ROOT / "modules/customizations/src/com/xaulinxs/customizations/settings"
HOTSEAT_JAVA = REPO_ROOT / "src/com/android/launcher3/Hotseat.java"
PREFS_XML = REPO_ROOT / "res/xml/launcher_preferences.xml"
STRINGS_XML = REPO_ROOT / "res/values/xaulinxs_strings.xml"


def fail(msg: str):
    print(f"[ERRO] {msg}")
    sys.exit(1)


def require_file(path: Path):
    if not path.exists():
        fail(
            f"Arquivo não encontrado: {path}\n"
            "Confirme que está rodando a partir da raiz do repositório."
        )


def write_if_absent(path: Path, content: str, marker: str):
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists() and marker in path.read_text(encoding="utf-8"):
        print(f"[SKIP] {path.relative_to(REPO_ROOT)} já existe.")
        return
    path.write_text(content, encoding="utf-8")
    print(f"[OK] Criado {path.relative_to(REPO_ROOT)}")


def apply_replace(path: Path, old: str, new: str, step_name: str):
    require_file(path)
    text = path.read_text(encoding="utf-8")
    if new in text:
        print(f"[SKIP] {step_name} já aplicado em {path.relative_to(REPO_ROOT)}.")
        return
    if old not in text:
        fail(
            f"[{step_name}] Âncora esperada não encontrada em {path}.\n"
            "O arquivo pode ter mudado. Cole o conteúdo atual do arquivo pra eu regenerar o patch."
        )
    count = text.count(old)
    if count != 1:
        fail(f"[{step_name}] Âncora encontrada {count} vezes em {path}, esperava 1. Abortando por segurança.")
    path.write_text(text.replace(old, new), encoding="utf-8")
    print(f"[OK] {step_name} aplicado em {path.relative_to(REPO_ROOT)}")


# ---------------------------------------------------------------------
# 1) XaulinXsSearchBarPrefs.kt
# ---------------------------------------------------------------------
write_if_absent(
    SEARCH_PKG / "XaulinXsSearchBarPrefs.kt",
    '''/*
 * XaulinXs Customizations — não faz parte do AOSP original.
 *
 * Todas as preferences da barra de busca própria (Feature 7).
 */
package com.xaulinxs.customizations.search

import com.android.launcher3.LauncherPrefs.Companion.backedUpItem

object XaulinXsSearchBarPrefs {
    val SEARCH_BAR_ENABLED = backedUpItem("xaulinxs_searchbar_enabled", false)

    // true = modo "busca na web" (ação de busca do teclado dispara
    // ACTION_WEB_SEARCH); false = campo de texto livre, sem ação.
    val SEARCH_BAR_WEB_MODE = backedUpItem("xaulinxs_searchbar_web_mode", true)

    val SEARCH_BAR_OPACITY = backedUpItem("xaulinxs_searchbar_opacity", 70)

    val SEARCH_BAR_CUSTOM_COLOR_ENABLED = backedUpItem("xaulinxs_searchbar_custom_color_enabled", false)
    val SEARCH_BAR_CUSTOM_COLOR_VALUE = backedUpItem("xaulinxs_searchbar_custom_color_value", 0xFF6750A4.toInt())

    val SEARCH_BAR_BLUR_ENABLED = backedUpItem("xaulinxs_searchbar_blur_enabled", false)
}
''',
    marker="SEARCH_BAR_ENABLED",
)

# ---------------------------------------------------------------------
# 2) XaulinXsSearchBarColors.kt — auto-suficiente, sem depender da feature 5
# ---------------------------------------------------------------------
write_if_absent(
    SEARCH_PKG / "XaulinXsSearchBarColors.kt",
    '''/*
 * XaulinXs Customizations — não faz parte do AOSP original.
 *
 * Cor de fundo/texto da barra de busca. Auto-suficiente de propósito: usa
 * cor própria da barra (se ativada) ou WallpaperColorHints como fallback —
 * NÃO depende de nenhuma classe da feature de editor de cor manual dos
 * ícones (feature 5, feita em outra sessão), porque essa API não pôde ser
 * verificada contra o código real no momento em que este script foi
 * escrito. Trocar a fonte de cor depois é uma mudança pequena e isolada
 * neste arquivo, se quiser unificar.
 */
package com.xaulinxs.customizations.search

import android.content.Context
import androidx.core.graphics.ColorUtils
import com.android.launcher3.LauncherPrefs
import com.android.launcher3.Utilities
import com.android.launcher3.util.WallpaperColorHints

private const val SHADE_RATIO_LIGHT = 0.15f
private const val SHADE_RATIO_DARK = 0.55f
private val DEFAULT_FALLBACK_COLOR = 0xFF808080.toInt() // cinza neutro, só se não houver cor de wallpaper

object XaulinXsSearchBarColors {

    fun getBackgroundColor(context: Context): Int {
        val prefs = LauncherPrefs.get(context)
        val base = if (prefs.get(XaulinXsSearchBarPrefs.SEARCH_BAR_CUSTOM_COLOR_ENABLED)) {
            prefs.get(XaulinXsSearchBarPrefs.SEARCH_BAR_CUSTOM_COLOR_VALUE)
        } else {
            WallpaperColorHints.get(context).colors?.primaryColor?.toArgb() ?: DEFAULT_FALLBACK_COLOR
        }
        val isDark = Utilities.isDarkTheme(context)
        val shaded =
            if (isDark) {
                ColorUtils.blendARGB(base, android.graphics.Color.BLACK, SHADE_RATIO_DARK)
            } else {
                ColorUtils.blendARGB(base, android.graphics.Color.WHITE, SHADE_RATIO_LIGHT)
            }
        val opacityPercent = prefs.get(XaulinXsSearchBarPrefs.SEARCH_BAR_OPACITY).coerceIn(0, 100)
        val alpha = opacityPercent * 255 / 100
        return ColorUtils.setAlphaComponent(shaded, alpha)
    }

    fun getForegroundColor(context: Context): Int =
        if (Utilities.isDarkTheme(context)) android.graphics.Color.WHITE else android.graphics.Color.BLACK
}
''',
    marker="XaulinXsSearchBarColors",
)

# ---------------------------------------------------------------------
# 3) XaulinXsSearchBarBlur.kt
# ---------------------------------------------------------------------
write_if_absent(
    SEARCH_PKG / "XaulinXsSearchBarBlur.kt",
    '''/*
 * XaulinXs Customizations — não faz parte do AOSP original.
 *
 * Recorta a região real do wallpaper que fica atrás de uma View na tela,
 * pra servir de fundo borrado da barra de busca. Protegido com try/catch
 * total: se WallpaperManager.getDrawable() falhar por qualquer motivo
 * (sem MANAGE_EXTERNAL_STORAGE, wallpaper animado sem bitmap estático,
 * ROM sem suporte), retorna null e o chamador cai de volta pra cor
 * translúcida sozinha, sem crash.
 *
 * O blur em si NÃO é feito aqui: é aplicado depois via
 * View.setRenderEffect() na ImageView que recebe este bitmap (API 31+) —
 * mesmo princípio do blur real do App Drawer (XaulinXsDepthController),
 * só que numa imagem estática em vez da workspace/hotseat ao vivo.
 */
package com.xaulinxs.customizations.search

import android.app.WallpaperManager
import android.content.Context
import android.graphics.Bitmap
import android.graphics.Canvas
import android.graphics.drawable.Drawable
import android.util.Log
import android.view.View

private const val TAG = "XaulinXsSearchBarBlur"

object XaulinXsSearchBarBlur {

    fun getWallpaperBackdropBitmap(context: Context, target: View): Bitmap? {
        return try {
            val metrics = target.resources.displayMetrics
            val screenWidth = metrics.widthPixels
            val screenHeight = metrics.heightPixels

            val wallpaperDrawable: Drawable =
                WallpaperManager.getInstance(context).drawable ?: return null
            val wallpaperWidth = wallpaperDrawable.intrinsicWidth
            val wallpaperHeight = wallpaperDrawable.intrinsicHeight
            if (wallpaperWidth <= 0 || wallpaperHeight <= 0) return null
            if (target.width <= 0 || target.height <= 0) return null

            val scale = maxOf(
                screenWidth.toFloat() / wallpaperWidth,
                screenHeight.toFloat() / wallpaperHeight,
            )
            val offsetX = (wallpaperWidth * scale - screenWidth) / 2f
            val offsetY = (wallpaperHeight * scale - screenHeight) / 2f

            val location = IntArray(2)
            target.getLocationOnScreen(location)

            val cropLeft = (location[0] + offsetX) / scale
            val cropTop = (location[1] + offsetY) / scale
            val cropWidth = target.width / scale
            val cropHeight = target.height / scale
            if (cropWidth <= 0f || cropHeight <= 0f) return null

            val output = Bitmap.createBitmap(target.width, target.height, Bitmap.Config.ARGB_8888)
            val canvas = Canvas(output)
            canvas.scale(target.width / cropWidth, target.height / cropHeight)
            canvas.translate(-cropLeft, -cropTop)
            wallpaperDrawable.setBounds(0, 0, wallpaperWidth, wallpaperHeight)
            wallpaperDrawable.draw(canvas)
            output
        } catch (e: SecurityException) {
            Log.w(TAG, "Sem permissão para ler o wallpaper real", e)
            null
        } catch (e: Exception) {
            Log.w(TAG, "Falha ao recortar o wallpaper para a barra de busca", e)
            null
        }
    }
}
''',
    marker="XaulinXsSearchBarBlur",
)

# ---------------------------------------------------------------------
# 4) XaulinXsSearchBarView.kt — com popup de long-press pro modo web/texto
# ---------------------------------------------------------------------
write_if_absent(
    SEARCH_PKG / "XaulinXsSearchBarView.kt",
    '''/*
 * XaulinXs Customizations — não faz parte do AOSP original.
 *
 * View da barra de busca própria, em 3 camadas (FrameLayout):
 *  1. Backdrop borrado do wallpaper real (opcional, API 31+, com fallback
 *     silencioso se o recorte falhar).
 *  2. Tint translúcido (cor própria da barra, ou wallpaper).
 *  3. Ícone + campo de texto, sempre nítidos por cima.
 *
 * Modo "busca na web": ação de busca do teclado dispara ACTION_WEB_SEARCH
 * (com fallback pra abrir o Google via navegador se não houver app de
 * busca instalado). Modo "campo de texto livre": não dispara nenhuma
 * ação, é só entrada de texto solta.
 *
 * Segurar o dedo na barra (ou no campo de texto) abre um popup pra trocar
 * entre os dois modos na hora, sem precisar ir nas configurações —
 * reaproveita o mesmo XaulinXsPopupBlurHelper usado pelos outros balões
 * de contexto do launcher (feature 1), pra ficar visualmente consistente.
 *
 * Não sobrescreve a busca de apps nativa do App Drawer — é uma barra
 * adicional, isolada, que ocupa o slot do QSB no hotseat (que já fica
 * abaixo da fileira de ícones por design do AOSP — ver comentário no
 * topo de feature_search_bar_final.py).
 */
package com.xaulinxs.customizations.search

import android.app.SearchManager
import android.content.Context
import android.content.Intent
import android.graphics.RenderEffect
import android.graphics.Shader
import android.graphics.drawable.GradientDrawable
import android.net.Uri
import android.os.Build
import android.text.InputType
import android.view.Gravity
import android.view.View
import android.view.ViewOutlineProvider
import android.view.inputmethod.EditorInfo
import android.widget.EditText
import android.widget.FrameLayout
import android.widget.ImageView
import android.widget.LinearLayout
import android.widget.PopupMenu
import android.widget.Toast
import androidx.core.graphics.ColorUtils
import com.android.launcher3.LauncherPrefs
import com.android.launcher3.R
import com.android.launcher3.views.ActivityContext
import com.xaulinxs.customizations.blur.XaulinXsPopupBlurHelper

class XaulinXsSearchBarView(context: Context) : FrameLayout(context) {

    private val editText: EditText
    private var webSearchMode: Boolean =
        LauncherPrefs.get(context).get(XaulinXsSearchBarPrefs.SEARCH_BAR_WEB_MODE)
    private val blurEnabled: Boolean =
        LauncherPrefs.get(context).get(XaulinXsSearchBarPrefs.SEARCH_BAR_BLUR_ENABLED)

    private val pillShape = GradientDrawable().apply {
        setColor(android.graphics.Color.TRANSPARENT)
    }
    private var blurBackdrop: ImageView? = null

    init {
        background = pillShape
        clipToOutline = true
        outlineProvider = ViewOutlineProvider.BACKGROUND
        isLongClickable = true

        if (blurEnabled && Build.VERSION.SDK_INT >= Build.VERSION_CODES.S) {
            blurBackdrop = ImageView(context).apply {
                scaleType = ImageView.ScaleType.FIT_XY
                layoutParams = LayoutParams(LayoutParams.MATCH_PARENT, LayoutParams.MATCH_PARENT)
                setRenderEffect(
                    RenderEffect.createBlurEffect(BLUR_RADIUS_PX, BLUR_RADIUS_PX, Shader.TileMode.CLAMP),
                )
            }
            addView(blurBackdrop)
        }

        val tintOverlay = View(context).apply {
            setBackgroundColor(XaulinXsSearchBarColors.getBackgroundColor(context))
            layoutParams = LayoutParams(LayoutParams.MATCH_PARENT, LayoutParams.MATCH_PARENT)
        }
        addView(tintOverlay)

        val foreground = XaulinXsSearchBarColors.getForegroundColor(context)
        val density = resources.displayMetrics.density
        val paddingH = (16 * density).toInt()

        val content = LinearLayout(context).apply {
            orientation = LinearLayout.HORIZONTAL
            gravity = Gravity.CENTER_VERTICAL
            setPadding(paddingH, 0, paddingH, 0)
            layoutParams = LayoutParams(LayoutParams.MATCH_PARENT, LayoutParams.MATCH_PARENT)
        }

        val icon = ImageView(context).apply {
            setImageResource(android.R.drawable.ic_menu_search)
            setColorFilter(foreground)
            val iconSize = (20 * density).toInt()
            layoutParams = LinearLayout.LayoutParams(iconSize, iconSize).apply {
                marginEnd = (12 * density).toInt()
            }
        }
        content.addView(icon)

        editText = EditText(context).apply {
            setHintTextColor(ColorUtils.setAlphaComponent(foreground, 150))
            setTextColor(foreground)
            isSingleLine = true
            this.background = null
            imeOptions = EditorInfo.IME_ACTION_SEARCH
            inputType = InputType.TYPE_CLASS_TEXT
            layoutParams = LinearLayout.LayoutParams(0, LinearLayout.LayoutParams.MATCH_PARENT, 1f)
            setOnEditorActionListener { _, actionId, _ ->
                if (actionId == EditorInfo.IME_ACTION_SEARCH) {
                    onSubmit(text?.toString().orEmpty())
                    true
                } else {
                    false
                }
            }
            // XaulinXs Customizations: segurar o dedo no campo de texto
            // também abre o popup de modo (substitui a seleção de texto
            // padrão — é uma barra de busca, não um editor de texto rico).
            setOnLongClickListener {
                showModePopup()
                true
            }
        }
        content.addView(editText)
        addView(content)

        updateHint()

        // XaulinXs Customizations: segurar o dedo na barra (fora do campo
        // de texto) abre o popup "busca na web / texto livre".
        setOnLongClickListener {
            showModePopup()
            true
        }
    }

    override fun onSizeChanged(w: Int, h: Int, oldw: Int, oldh: Int) {
        super.onSizeChanged(w, h, oldw, oldh)
        // Pílula perfeitamente arredondada: só sabemos a altura real do
        // slot do QSB depois que o Hotseat mede/faz o layout deste View.
        pillShape.cornerRadius = h / 2f
        invalidateOutline()
        refreshBlurBackdrop()
    }

    private fun refreshBlurBackdrop() {
        val target = blurBackdrop ?: return
        if (width <= 0 || height <= 0) return
        post {
            val bitmap = XaulinXsSearchBarBlur.getWallpaperBackdropBitmap(context, this)
            if (bitmap != null) {
                target.setImageBitmap(bitmap)
            } else {
                removeView(target)
                blurBackdrop = null
            }
        }
    }

    private fun onSubmit(query: String) {
        if (query.isBlank()) return
        if (webSearchMode) {
            performWebSearch(query)
        }
        editText.clearFocus()
    }

    private fun performWebSearch(query: String) {
        try {
            val intent = Intent(Intent.ACTION_WEB_SEARCH)
            intent.putExtra(SearchManager.QUERY, query)
            context.startActivity(intent)
        } catch (e: Exception) {
            try {
                val fallback = Intent(
                    Intent.ACTION_VIEW,
                    Uri.parse("https://www.google.com/search?q=" + Uri.encode(query)),
                )
                fallback.addFlags(Intent.FLAG_ACTIVITY_NEW_TASK)
                context.startActivity(fallback)
            } catch (e2: Exception) {
                Toast.makeText(context, R.string.xaulinxs_searchbar_error, Toast.LENGTH_SHORT).show()
            }
        }
    }

    private fun updateHint() {
        editText.hint = context.getString(
            if (webSearchMode) R.string.xaulinxs_searchbar_hint_web
            else R.string.xaulinxs_searchbar_hint_text
        )
    }

    // XaulinXs Customizations: popup de long-press pra trocar entre "busca
    // na web" e "texto livre" direto na tela inicial, sem precisar abrir
    // as configurações. O switch em XaulinXs Customizations continua
    // sendo a fonte "oficial" — os dois leem/escrevem a mesma preference,
    // então ficam sempre em sincronia.
    private fun showModePopup() {
        val activityContext = ActivityContext.lookupContext(context)
        XaulinXsPopupBlurHelper.onPopupShown(activityContext)
        val popup = PopupMenu(context, this)
        popup.menu.add(0, MENU_ID_WEB, 0, R.string.xaulinxs_searchbar_mode_web)
        popup.menu.add(0, MENU_ID_TEXT, 1, R.string.xaulinxs_searchbar_mode_text)
        popup.setOnMenuItemClickListener { item ->
            val newWebMode = item.itemId == MENU_ID_WEB
            LauncherPrefs.get(context).put(XaulinXsSearchBarPrefs.SEARCH_BAR_WEB_MODE, newWebMode)
            webSearchMode = newWebMode
            updateHint()
            true
        }
        popup.setOnDismissListener {
            XaulinXsPopupBlurHelper.onPopupClosed(activityContext)
        }
        popup.show()
    }

    companion object {
        private const val BLUR_RADIUS_PX = 40f
        private const val MENU_ID_WEB = 1
        private const val MENU_ID_TEXT = 2
    }
}
''',
    marker="showModePopup",
)

# ---------------------------------------------------------------------
# 5) XaulinXsSearchBarFactory.kt
# ---------------------------------------------------------------------
write_if_absent(
    SEARCH_PKG / "XaulinXsSearchBarFactory.kt",
    '''/*
 * XaulinXs Customizations — não faz parte do AOSP original.
 *
 * Ponto único que Hotseat.java consulta para decidir se usa nossa barra
 * de busca própria ou o QSB original do AOSP. Retornar null preserva
 * 100% do comportamento padrão.
 */
package com.xaulinxs.customizations.search

import android.content.Context
import android.view.View
import android.view.ViewGroup
import com.android.launcher3.LauncherPrefs

object XaulinXsSearchBarFactory {
    @JvmStatic
    fun createViewIfEnabled(context: Context, container: ViewGroup): View? {
        if (!LauncherPrefs.get(context).get(XaulinXsSearchBarPrefs.SEARCH_BAR_ENABLED)) return null
        return XaulinXsSearchBarView(context)
    }
}
''',
    marker="XaulinXsSearchBarFactory",
)

# ---------------------------------------------------------------------
# 6) Hook em Hotseat.java (AOSP)
# ---------------------------------------------------------------------
apply_replace(
    HOTSEAT_JAVA,
    old=(
        "    public Hotseat(Context context, AttributeSet attrs, int defStyle) {\n"
        "        super(context, attrs, defStyle);\n"
        "        mQsb = LauncherComponentProvider.get(context).getQsbWidgetFactory().createView(this);\n"
        "\n"
        "        addView(mQsb);\n"
    ),
    new=(
        "    public Hotseat(Context context, AttributeSet attrs, int defStyle) {\n"
        "        super(context, attrs, defStyle);\n"
        "        // XaulinXs Customizations: barra de busca própria (opcional). Quando\n"
        "        // desativada (padrão), createViewIfEnabled() retorna null e o QSB\n"
        "        // original do AOSP é usado normalmente, sem nenhuma mudança de\n"
        "        // comportamento. Quando ativada, ocupa o mesmo slot que o QSB original\n"
        "        // ocuparia — que já fica abaixo da fileira de ícones por design do\n"
        "        // AOSP (Hotseat.onLayout/getQsbOffsetY), sem precisar de nenhum ajuste\n"
        "        // de posição aqui.\n"
        "        View xaulinxsSearchBar =\n"
        "                com.xaulinxs.customizations.search.XaulinXsSearchBarFactory\n"
        "                        .createViewIfEnabled(context, this);\n"
        "        mQsb = xaulinxsSearchBar != null\n"
        "                ? xaulinxsSearchBar\n"
        "                : LauncherComponentProvider.get(context).getQsbWidgetFactory().createView(this);\n"
        "\n"
        "        addView(mQsb);\n"
    ),
    step_name="Hotseat.java: hook da barra de busca própria",
)

# ---------------------------------------------------------------------
# 7) Preference classes
# ---------------------------------------------------------------------
write_if_absent(
    SETTINGS_PKG / "SearchBarEnabledPreference.kt",
    '''/*
 * XaulinXs Customizations — não faz parte do AOSP original.
 */
package com.xaulinxs.customizations.settings

import android.content.Context
import android.util.AttributeSet
import androidx.preference.SwitchPreference
import com.android.launcher3.LauncherPrefs
import com.xaulinxs.customizations.search.XaulinXsSearchBarPrefs

class SearchBarEnabledPreference @JvmOverloads constructor(
    context: Context,
    attrs: AttributeSet? = null,
) : SwitchPreference(context, attrs) {

    init {
        isPersistent = false
        isChecked = LauncherPrefs.get(context).get(XaulinXsSearchBarPrefs.SEARCH_BAR_ENABLED)
        setOnPreferenceChangeListener { _, newValue ->
            LauncherPrefs.get(context).put(XaulinXsSearchBarPrefs.SEARCH_BAR_ENABLED, newValue as Boolean)
            true
        }
    }
}
''',
    marker="SearchBarEnabledPreference",
)

write_if_absent(
    SETTINGS_PKG / "SearchBarWebModePreference.kt",
    '''/*
 * XaulinXs Customizations — não faz parte do AOSP original.
 */
package com.xaulinxs.customizations.settings

import android.content.Context
import android.util.AttributeSet
import androidx.preference.SwitchPreference
import com.android.launcher3.LauncherPrefs
import com.xaulinxs.customizations.search.XaulinXsSearchBarPrefs

class SearchBarWebModePreference @JvmOverloads constructor(
    context: Context,
    attrs: AttributeSet? = null,
) : SwitchPreference(context, attrs) {

    init {
        isPersistent = false
        isChecked = LauncherPrefs.get(context).get(XaulinXsSearchBarPrefs.SEARCH_BAR_WEB_MODE)
        setOnPreferenceChangeListener { _, newValue ->
            LauncherPrefs.get(context).put(XaulinXsSearchBarPrefs.SEARCH_BAR_WEB_MODE, newValue as Boolean)
            true
        }
    }
}
''',
    marker="SearchBarWebModePreference",
)

write_if_absent(
    SETTINGS_PKG / "SearchBarOpacityPreference.kt",
    '''/*
 * XaulinXs Customizations — não faz parte do AOSP original.
 */
package com.xaulinxs.customizations.settings

import android.content.Context
import android.util.AttributeSet
import androidx.preference.SeekBarPreference
import com.android.launcher3.LauncherPrefs
import com.xaulinxs.customizations.search.XaulinXsSearchBarPrefs

class SearchBarOpacityPreference @JvmOverloads constructor(
    context: Context,
    attrs: AttributeSet? = null,
) : SeekBarPreference(context, attrs) {

    init {
        isPersistent = false
        min = 10
        max = 100
        showSeekBarValue = true
        value = LauncherPrefs.get(context).get(XaulinXsSearchBarPrefs.SEARCH_BAR_OPACITY)
        setOnPreferenceChangeListener { _, newValue ->
            LauncherPrefs.get(context).put(XaulinXsSearchBarPrefs.SEARCH_BAR_OPACITY, newValue as Int)
            true
        }
    }
}
''',
    marker="SearchBarOpacityPreference",
)

write_if_absent(
    SETTINGS_PKG / "SearchBarColorEnabledPreference.kt",
    '''/*
 * XaulinXs Customizations — não faz parte do AOSP original.
 */
package com.xaulinxs.customizations.settings

import android.content.Context
import android.util.AttributeSet
import androidx.preference.SwitchPreference
import com.android.launcher3.LauncherPrefs
import com.xaulinxs.customizations.search.XaulinXsSearchBarPrefs

class SearchBarColorEnabledPreference @JvmOverloads constructor(
    context: Context,
    attrs: AttributeSet? = null,
) : SwitchPreference(context, attrs) {

    init {
        isPersistent = false
        isChecked = LauncherPrefs.get(context).get(XaulinXsSearchBarPrefs.SEARCH_BAR_CUSTOM_COLOR_ENABLED)
        setOnPreferenceChangeListener { _, newValue ->
            LauncherPrefs.get(context)
                .put(XaulinXsSearchBarPrefs.SEARCH_BAR_CUSTOM_COLOR_ENABLED, newValue as Boolean)
            true
        }
    }
}
''',
    marker="SearchBarColorEnabledPreference",
)

write_if_absent(
    SETTINGS_PKG / "SearchBarColorPickerPreference.kt",
    '''/*
 * XaulinXs Customizations — não faz parte do AOSP original.
 *
 * Seletor de cor em hex (#RRGGBB ou #AARRGGBB) com preview ao vivo, num
 * AlertDialog simples (androidx.appcompat, já é dependência do projeto).
 */
package com.xaulinxs.customizations.settings

import android.content.Context
import android.text.Editable
import android.text.InputType
import android.text.TextWatcher
import android.util.AttributeSet
import android.view.Gravity
import android.view.View
import android.widget.EditText
import android.widget.LinearLayout
import androidx.appcompat.app.AlertDialog
import androidx.preference.Preference
import com.android.launcher3.LauncherPrefs
import com.android.launcher3.R
import com.xaulinxs.customizations.search.XaulinXsSearchBarPrefs

class SearchBarColorPickerPreference @JvmOverloads constructor(
    context: Context,
    attrs: AttributeSet? = null,
) : Preference(context, attrs) {

    init {
        isPersistent = false
        updateSummary()
    }

    override fun onClick() {
        val prefs = LauncherPrefs.get(context)
        val currentColor = prefs.get(XaulinXsSearchBarPrefs.SEARCH_BAR_CUSTOM_COLOR_VALUE)
        val density = context.resources.displayMetrics.density
        val previewSizePx = (56 * density).toInt()
        val paddingPx = (24 * density).toInt()

        val preview = View(context).apply { setBackgroundColor(currentColor) }

        val hexInput = EditText(context).apply {
            inputType = InputType.TYPE_CLASS_TEXT
            setText(String.format("#%06X", 0xFFFFFF and currentColor))
            setSelection(text.length)
            addTextChangedListener(object : TextWatcher {
                override fun beforeTextChanged(s: CharSequence?, a: Int, b: Int, c: Int) {}
                override fun onTextChanged(s: CharSequence?, a: Int, b: Int, c: Int) {}
                override fun afterTextChanged(s: Editable?) {
                    parseHexOrNull(s?.toString())?.let { preview.setBackgroundColor(it) }
                }
            })
        }

        val container = LinearLayout(context).apply {
            orientation = LinearLayout.VERTICAL
            setPadding(paddingPx, paddingPx, paddingPx, paddingPx)
            addView(
                preview,
                LinearLayout.LayoutParams(previewSizePx, previewSizePx).apply {
                    gravity = Gravity.CENTER_HORIZONTAL
                    bottomMargin = paddingPx / 2
                },
            )
            addView(hexInput)
        }

        AlertDialog.Builder(context)
            .setTitle(R.string.xaulinxs_searchbar_color_picker_title)
            .setView(container)
            .setPositiveButton(android.R.string.ok) { _, _ ->
                val parsed = parseHexOrNull(hexInput.text?.toString()) ?: currentColor
                prefs.put(XaulinXsSearchBarPrefs.SEARCH_BAR_CUSTOM_COLOR_VALUE, parsed)
                updateSummary()
            }
            .setNegativeButton(android.R.string.cancel, null)
            .show()
    }

    private fun updateSummary() {
        val color = LauncherPrefs.get(context).get(XaulinXsSearchBarPrefs.SEARCH_BAR_CUSTOM_COLOR_VALUE)
        summary = String.format("#%06X", 0xFFFFFF and color)
    }

    private fun parseHexOrNull(input: String?): Int? {
        if (input.isNullOrBlank()) return null
        val clean = input.removePrefix("#").trim()
        if (clean.length != 6 && clean.length != 8) return null
        return try {
            val argb = if (clean.length == 6) "FF$clean" else clean
            (argb.toLong(16) and 0xFFFFFFFFL).toInt()
        } catch (e: NumberFormatException) {
            null
        }
    }
}
''',
    marker="SearchBarColorPickerPreference",
)

write_if_absent(
    SETTINGS_PKG / "SearchBarBlurEnabledPreference.kt",
    '''/*
 * XaulinXs Customizations — não faz parte do AOSP original.
 */
package com.xaulinxs.customizations.settings

import android.content.Context
import android.util.AttributeSet
import androidx.preference.SwitchPreference
import com.android.launcher3.LauncherPrefs
import com.xaulinxs.customizations.search.XaulinXsSearchBarPrefs

class SearchBarBlurEnabledPreference @JvmOverloads constructor(
    context: Context,
    attrs: AttributeSet? = null,
) : SwitchPreference(context, attrs) {

    init {
        isPersistent = false
        isChecked = LauncherPrefs.get(context).get(XaulinXsSearchBarPrefs.SEARCH_BAR_BLUR_ENABLED)
        setOnPreferenceChangeListener { _, newValue ->
            LauncherPrefs.get(context).put(XaulinXsSearchBarPrefs.SEARCH_BAR_BLUR_ENABLED, newValue as Boolean)
            true
        }
    }
}
''',
    marker="SearchBarBlurEnabledPreference",
)

# ---------------------------------------------------------------------
# 8) XML de preferences + strings — ancorado no fechamento do bloco
# ---------------------------------------------------------------------
apply_replace(
    PREFS_XML,
    old=(
        "    </PreferenceScreen>\n"
        "    <!-- ============ XaulinXs Customizations — fim ============ -->\n"
    ),
    new=(
        "        <com.xaulinxs.customizations.settings.SearchBarEnabledPreference\n"
        "            android:key=\"xaulinxs_searchbar_enabled\"\n"
        "            android:title=\"@string/xaulinxs_searchbar_enabled_title\"\n"
        "            android:summary=\"@string/xaulinxs_searchbar_enabled_summary\"\n"
        "            android:persistent=\"false\" />\n"
        "\n"
        "        <com.xaulinxs.customizations.settings.SearchBarWebModePreference\n"
        "            android:key=\"xaulinxs_searchbar_web_mode\"\n"
        "            android:title=\"@string/xaulinxs_searchbar_web_mode_title\"\n"
        "            android:summary=\"@string/xaulinxs_searchbar_web_mode_summary\"\n"
        "            android:persistent=\"false\" />\n"
        "\n"
        "        <com.xaulinxs.customizations.settings.SearchBarOpacityPreference\n"
        "            android:key=\"xaulinxs_searchbar_opacity\"\n"
        "            android:title=\"@string/xaulinxs_searchbar_opacity_title\"\n"
        "            android:persistent=\"false\" />\n"
        "\n"
        "        <com.xaulinxs.customizations.settings.SearchBarColorEnabledPreference\n"
        "            android:key=\"xaulinxs_searchbar_custom_color_enabled\"\n"
        "            android:title=\"@string/xaulinxs_searchbar_custom_color_enabled_title\"\n"
        "            android:summary=\"@string/xaulinxs_searchbar_custom_color_enabled_summary\"\n"
        "            android:persistent=\"false\" />\n"
        "\n"
        "        <com.xaulinxs.customizations.settings.SearchBarColorPickerPreference\n"
        "            android:key=\"xaulinxs_searchbar_custom_color_picker\"\n"
        "            android:title=\"@string/xaulinxs_searchbar_color_picker_title\"\n"
        "            android:persistent=\"false\" />\n"
        "\n"
        "        <com.xaulinxs.customizations.settings.SearchBarBlurEnabledPreference\n"
        "            android:key=\"xaulinxs_searchbar_blur_enabled\"\n"
        "            android:title=\"@string/xaulinxs_searchbar_blur_enabled_title\"\n"
        "            android:summary=\"@string/xaulinxs_searchbar_blur_enabled_summary\"\n"
        "            android:persistent=\"false\" />\n"
        "\n"
        "    </PreferenceScreen>\n"
        "    <!-- ============ XaulinXs Customizations — fim ============ -->\n"
    ),
    step_name="launcher_preferences.xml: itens da barra de busca",
)

apply_replace(
    STRINGS_XML,
    old="</resources>\n",
    new=(
        '    <string name="xaulinxs_searchbar_enabled_title">Barra de busca própria</string>\n'
        '    <string name="xaulinxs_searchbar_enabled_summary">Substitui a barra de busca padrão do hotseat por uma temática</string>\n'
        '    <string name="xaulinxs_searchbar_web_mode_title">Modo busca na web</string>\n'
        '    <string name="xaulinxs_searchbar_web_mode_summary">Ativado: a ação de busca do teclado pesquisa na web. Desativado: só campo de texto livre. Também pode ser trocado segurando o dedo na barra.</string>\n'
        '    <string name="xaulinxs_searchbar_opacity_title">Opacidade da barra</string>\n'
        '    <string name="xaulinxs_searchbar_custom_color_enabled_title">Cor própria da barra</string>\n'
        '    <string name="xaulinxs_searchbar_custom_color_enabled_summary">Usa uma cor fixa só para a barra, em vez da cor do papel de parede</string>\n'
        '    <string name="xaulinxs_searchbar_color_picker_title">Cor da barra (hex)</string>\n'
        '    <string name="xaulinxs_searchbar_blur_enabled_title">Desfoque (blur) na barra</string>\n'
        '    <string name="xaulinxs_searchbar_blur_enabled_summary">Borra o papel de parede atrás da barra (Android 12+; sem efeito em versões anteriores)</string>\n'
        '    <string name="xaulinxs_searchbar_hint_web">Pesquisar na web</string>\n'
        '    <string name="xaulinxs_searchbar_hint_text">Digite algo</string>\n'
        '    <string name="xaulinxs_searchbar_error">Não foi possível abrir a busca</string>\n'
        '    <string name="xaulinxs_searchbar_mode_web">Modo: busca na web</string>\n'
        '    <string name="xaulinxs_searchbar_mode_text">Modo: texto livre</string>\n'
        "</resources>\n"
    ),
    step_name="xaulinxs_strings.xml: strings da barra de busca",
)

print("\nFeature 7 (barra de busca) aplicada com sucesso.")
print("Recompile com:")
print("  ./gradlew assembleNoQuickstepDebug --stacktrace 2>&1 | tee build_nextNN.log")
