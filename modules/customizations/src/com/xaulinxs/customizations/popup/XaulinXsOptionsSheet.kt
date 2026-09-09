/*
 * XaulinXs Customizations - Fase 1.5 (popup de área vazia como bottom sheet real).
 *
 * Este arquivo é uma adição nova e isolada (não altera nenhum arquivo do AOSP).
 * Usa a classe já existente no AOSP com.android.launcher3.views.AbstractSlideInView,
 * que é a mesma família de componente usada pelo menu de aplicativos em modo de
 * bottom sheet (tablet) e pela folha de widgets: ela já implementa, prontos:
 *   - arrastar para baixo para fechar (SingleAxisSwipeDetector já embutido)
 *   - fechar tocando fora do conteúdo (scrim)
 *   - abrir/fechar animado
 *   - suporte ao gesto de "voltar" do sistema
 *
 * Isso é usado APENAS para o popup de "área vazia da tela inicial" (Plano de fundo
 * e estilo / Widgets / Lista de apps / Configurações da tela inicial), chamado por
 * Launcher.showDefaultOptions(). O popup de itens extras da tela inicial (pastas,
 * widgets, par de apps) continua usando o PopupContainer/ArrowPopup original -
 * ele lida com coisas mais delicadas (moldura de redimensionar widget, listener de
 * arrastar) que não valia a pena arriscar reescrever nesta etapa.
 */
package com.xaulinxs.customizations.popup

import android.content.Context
import android.graphics.drawable.GradientDrawable
import android.util.AttributeSet
import android.view.LayoutInflater
import android.view.View
import android.widget.LinearLayout
import com.android.launcher3.R
import com.android.launcher3.model.data.ItemInfo
import com.android.launcher3.popup.PopupData
import com.android.launcher3.shortcuts.DeepShortcutView
import com.android.launcher3.Launcher
import com.android.launcher3.views.AbstractSlideInView
import com.android.launcher3.views.ActivityContext
import com.xaulinxs.customizations.theme.XaulinXsBalloonColor

/**
 * Bottom sheet com barrinha de arrastar para as opções da área vazia da tela inicial.
 *
 * O parâmetro genérico de [AbstractSlideInView] exige um tipo que seja Context E
 * ActivityContext ao mesmo tempo (`T extends Context & ActivityContext`). A interface
 * ActivityContext sozinha não satisfaz esse bound - é preciso a classe concreta real
 * usada em runtime, que no launcher-phone é sempre [Launcher].
 */
class XaulinXsOptionsSheet
@JvmOverloads
constructor(context: Context, attrs: AttributeSet? = null, defStyleAttr: Int = 0) :
    AbstractSlideInView<Launcher>(context, attrs, defStyleAttr) {

    companion object {
        private const val OPEN_CLOSE_DURATION_MS = 250L

        /** Mostra o bottom sheet com as opções passadas em [items]. */
        @JvmStatic
        fun show(activityContext: ActivityContext, anchorView: View, items: List<PopupData>) {
            if (items.isEmpty()) return
            if (getOpenView<XaulinXsOptionsSheet>(activityContext, TYPE_OPTIONS_POPUP) != null) {
                // Já tem um popup deste tipo aberto, não abre outro por cima.
                return
            }

            val context = activityContext.asContext()
            val dragLayer = activityContext.dragLayer
            val sheet =
                LayoutInflater.from(context)
                    .inflate(R.layout.xaulinxs_workspace_options_sheet, dragLayer, false)
                    as XaulinXsOptionsSheet

            val itemInfo = anchorView.tag as? ItemInfo ?: ItemInfo()
            sheet.populate(activityContext, anchorView, itemInfo, items)
            sheet.openAnimated()
        }
    }

    private lateinit var rowsContainer: LinearLayout

    override fun onFinishInflate() {
        super.onFinishInflate()
        mContent = findViewById(R.id.xaulinxs_sheet_content)
        rowsContainer = findViewById(R.id.xaulinxs_sheet_rows)
        applyBalloonColorBackground()
    }

    /*
     * XaulinXs Customizations: este retângulo (popup de área vazia da
     * workspace: Plano de fundo / Widgets / Apps / Configurações) era um
     * balão (ArrowPopup) e por isso já seguia XaulinXsBalloonColor. Ao ser
     * redesenhado como bottom sheet moderno (XaulinXsOptionsSheet), o fundo
     * passou a vir de um drawable estático (xaulinxs_sheet_background com
     * @color/materialColorSurfaceContainer) e perdeu essa customização.
     *
     * Aqui reaplicamos a MESMA regra dos balões dos apps, sem duplicar
     * lógica: desligado -> cor extraída do papel de parede; ligado -> cor
     * manual do editor hex/paleta; sem nenhuma das duas -> mantém o
     * drawable original (fallback AOSP), sem quebrar nada.
     */
    private fun applyBalloonColorBackground() {
        val overrideColor =
            XaulinXsBalloonColor.getBalloonColorOverride(context) ?: return
        val background = mContent.background?.mutate()
        if (background is GradientDrawable) {
            background.setColor(overrideColor)
        }
    }

    /**
     * Mantido como método de instância (em vez de mexer direto nos membros protegidos herdados
     * de [AbstractSlideInView] lá do companion object) para evitar qualquer ambiguidade de
     * visibilidade em Kotlin - acesso a membro `protected` a partir do próprio corpo da classe é
     * sempre permitido.
     */
    private fun openAnimated() {
        mIsOpen = true
        attachToContainer()
        setUpOpenAnimation(OPEN_CLOSE_DURATION_MS).animationPlayer.start()
    }

    private fun populate(
        activityContext: ActivityContext,
        anchorView: View,
        itemInfo: ItemInfo,
        items: List<PopupData>,
    ) {
        val inflater = LayoutInflater.from(context)
        items.forEach { popupData ->
            val row =
                inflater.inflate(R.layout.xaulinxs_sheet_option_row, rowsContainer, false)
                    as DeepShortcutView
            row.iconView.setBackgroundResource(popupData.iconResId)
            row.bubbleText.setText(popupData.labelResId)
            row.setOnClickListener {
                close(true)
                popupData.popupAction.invoke(activityContext, itemInfo, anchorView)
            }
            rowsContainer.addView(row)
        }
    }

    override fun isOfType(type: Int): Boolean {
        return (type and TYPE_OPTIONS_POPUP) != 0
    }

    override fun handleClose(animate: Boolean) {
        handleClose(animate, OPEN_CLOSE_DURATION_MS)
    }

    /*
     * XaulinXs Customizations: este bottom sheet não cobre a tela inteira
     * (é ancorado embaixo), então a área acima dele usava um scrim estático
     * quase-branco (?attr/allAppsScrimColor -> materialColorSurfaceDim),
     * escondendo o papel de parede exatamente onde o retângulo do popup não
     * aparece. Sem scrim (-1 = comportamento padrão de AbstractSlideInView,
     * ver getScrimColor() lá), essa área fica transparente e mostra o papel
     * de parede normalmente, como pedido.
     */
    override fun getScrimColor(context: Context): Int {
        return -1
    }
}
