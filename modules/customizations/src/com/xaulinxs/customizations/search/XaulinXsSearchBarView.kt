/*
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
