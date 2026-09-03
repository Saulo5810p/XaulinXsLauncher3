/*
 * Copyright (C) 2025 The Android Open Source Project
 *
 * Licensed under the Apache License, Version 2.0 (the "License");
 * you may not use this file except in compliance with the License.
 * You may obtain a copy of the License at
 *
 *      http://www.apache.org/licenses/LICENSE-2.0
 *
 * Unless required by applicable law or agreed to in writing, software
 * distributed under the License is distributed on an "AS IS" BASIS,
 * WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
 * See the License for the specific language governing permissions and
 * limitations under the License.
 */

package com.android.launcher3.qsb

import android.annotation.SuppressLint
import android.app.AlertDialog
import android.appwidget.AppWidgetManager.INVALID_APPWIDGET_ID
import android.appwidget.AppWidgetProviderInfo
import android.content.ComponentName
import android.content.Context
import android.content.Intent
import android.content.pm.PackageManager
import android.content.res.ColorStateList
import android.os.Process.myUserHandle
import android.text.Editable
import android.text.TextWatcher
import android.util.AttributeSet
import android.util.Log
import android.view.View
import android.widget.EditText
import android.widget.ImageView
import android.widget.LinearLayout
import android.widget.RemoteViews
import android.widget.TextView
import androidx.annotation.VisibleForTesting
import androidx.core.net.toUri
import com.android.launcher3.BubbleTextView
import com.android.launcher3.LauncherSettings.Favorites
import com.android.launcher3.R
import com.android.launcher3.allapps.AllAppsStore
import com.android.launcher3.dagger.LauncherComponentProvider.appComponent
import com.android.launcher3.model.data.AppInfo
import com.android.launcher3.model.data.ItemInfo
import com.android.launcher3.model.data.LauncherAppWidgetInfo
import com.android.launcher3.popup.PopupContainer
import com.android.launcher3.util.ComponentKey
import com.android.launcher3.util.RunnableList
import com.android.launcher3.util.SafeCloseable
import com.android.launcher3.util.ViewEx.registerLifecycleTask
import com.android.launcher3.views.ActivityContext
import com.android.launcher3.widget.LauncherAppWidgetHostView
import com.xaulinxs.customizations.qsb.QsbAction
import com.xaulinxs.customizations.qsb.QsbActionPreviewBuilder
import com.xaulinxs.customizations.qsb.QsbBadgeIcon
import com.xaulinxs.customizations.qsb.QsbConfig
import com.xaulinxs.customizations.qsb.QsbFailureReason
import com.xaulinxs.customizations.qsb.QsbTextModeCommand
import com.xaulinxs.customizations.qsb.QsbTextModeResult
import com.xaulinxs.customizations.qsb.XaulinXsQsbPermissionActivity
import com.xaulinxs.customizations.qsb.XaulinXsQsbPermissionCallback

/**
 * Renders the On-device search engine's widget [RemoteViews] based on [AppWidgetProviderInfo] by
 * listening to OSE changes through [OseWidgetManager]
 */
class OseWidgetView
@JvmOverloads
constructor(context: Context, attrs: AttributeSet? = null, defStyleAttr: Int = 0) :
    LauncherAppWidgetHostView(context) {

    private val oseWidgetManager = context.appComponent.oseWidgetManager
    @VisibleForTesting var closeActions = RunnableList()
    private val activityContext: ActivityContext = ActivityContext.lookupContext(context)

    internal var autoUpdateTag = true

    init {
        activityContext.appWidgetHolder?.onViewCreationCallback?.accept(this)
        setOnLongClickListener {
            PopupContainer.showForMenuItems(
                activityContext,
                this,
                activityContext.activityComponent.getOseWidgetOptionsProvider().getOptionItems(),
            ) != null
        }
    }

    override fun onAttachedToWindow() {
        super.onAttachedToWindow()
        attachedToWindow()
    }

    @VisibleForTesting
    fun attachedToWindow() {
        closeActions.executeAllAndClear()

        // XaulinXs Customizations: esta é a QSB nativa AOSP/Launcher3
        // "NoQuickstep" — OseWidgetManager nunca mais localiza/binda um
        // AppWidget de terceiro (ver comentário em
        // OseWidgetManager.handleOseInfoUpdate), então providerInfo e
        // views são sempre despachados como null. O fluxo original do
        // AOSP abaixo pressupõe que, depois de setAppWidget(id, info)
        // com um "info" real, um evento de "views" real chega logo em
        // seguida sobrescrevendo o RemoteViews(context.packageName, 0)
        // usado só como placeholder de reset — com info sempre null,
        // esse RemoteViews vazio (layoutId=0) nunca é sobrescrito e
        // fica permanentemente visível, o que o framework renderiza
        // como uma UI de erro nativa genérica (não a nossa
        // getErrorView() customizada — essa só dispara quando
        // updateAppWidget recebe null, não um RemoteViews vazio).
        // Fix: quando não há provider (it == null), pula esse reset
        // por completo e delega direto para getErrorView(), chamando
        // updateAppWidget(null) — o caminho que o framework já trata
        // corretamente.
        //
        // We use INVALID_APPWIDGET_ID because appWidgetId is not tracked in OseWidgetView. Instead
        // it is managed by OseWidgetManager and QsbAppWidgetHost.
        closeActions.add(
            oseWidgetManager.providerInfo.forEach(activityContext.uiExecutor) {
                setAppWidget(INVALID_APPWIDGET_ID, it)
                if (it == null) {
                    updateAppWidget(null)
                } else {
                    // We will get valid updateAppWidget remoteview call from
                    // OseWidgetManager again. This is only for resetting the
                    // remoteviews using a broken remote view.
                    updateAppWidget(RemoteViews(context.packageName, 0))
                }
                if (autoUpdateTag) tag = getTagInfo(it)
                Log.i(TAG, "setAppWidget providerInfo=$it")
            }::close
        )
        closeActions.add(
            oseWidgetManager.views.forEach(activityContext.uiExecutor) {
                updateAppWidget(it)
                Log.i(TAG, "updateAppWidget view=$it")
            }::close
        )
    }

    override fun onDetachedFromWindow() {
        super.onDetachedFromWindow()
        detachedFromWindow()
    }

    @VisibleForTesting
    fun detachedFromWindow() {
        closeActions.executeAllAndClear()
    }

    override fun shouldDelayChildPressedState(): Boolean {
        // Delay the ripple effect on the widget view when swiping up from home screen
        // to go to all apps.
        return true
    }

    @SuppressLint("UseCompatLoadingForDrawables")
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
        val oseInfo = context.appComponent.getOseManager().oseInfo.value
        val osePkg: String? =
            when {
                oseInfo.isOseConfigured -> oseInfo.pkg
                else -> null
            }

        val appsStore = activityContext.activityComponent.appsStore
        val title = context.getText(R.string.abandoned_search)
        val updateListener =
            AllAppsStore.OnUpdateListener {
                val appInfo =
                    osePkg
                        ?.let {
                            appsStore.getApp(
                                ComponentKey(ComponentName(osePkg, ""), myUserHandle()),
                                AppInfo.PACKAGE_KEY_COMPARATOR,
                            )
                        }
                        ?.clone()

                if (appInfo == null) {
                    view.tag = null
                    view.applyIconAndLabel(
                        context.getDrawable(R.drawable.ic_allapps_search)!!.mutate().apply {
                            setTint(context.getColor(R.color.materialColorOnSurface))
                        },
                        title,
                        null,
                    )
                    // Since we don't have a valid appInfo, just open the default browser
                    // Set the data to a blank page uri
                    view.setOnClickIntent(Intent(Intent.ACTION_VIEW).setData("http://".toUri()))
                } else {
                    appInfo.title = title
                    view.applyFromApplicationInfo(appInfo)
                    view.setOnClickIntent(
                        when {
                            // Launch search intent.
                            oseInfo.supportsSearchIntent ->
                                Intent(Intent.ACTION_SEARCH).setPackage(appInfo.targetPackage)
                            // Launch main activity
                            else -> appInfo.intent
                        }
                    )
                }
            }

        updateListener.onAppsUpdated()
        view.registerLifecycleTask {
            appsStore.addUpdateListener(updateListener)
            SafeCloseable { appsStore.removeUpdateListener(updateListener) }
        }
        return view
    }

    /**
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
    }

    fun View.setOnClickIntent(intent: Intent) = setOnClickListener {
        // XaulinXs Customizations: Modo Texto e Modo Web são exclusivos
        // (QsbConfig.MODE_TEXT_ENABLED). No Modo Texto, o toque abre um
        // campo de texto: se reconhecer um comando ("abrir <app>"),
        // executa direto; senão cai pro comportamento normal do Modo
        // Web (o mesmo intent que já seria disparado), nunca deixa o
        // toque sem efeito.
        if (QsbConfig.isTextModeEnabled(context)) {
            showXaulinXsTextModeDialog(intent)
            return@setOnClickListener
        }
        launchQsbIntent(intent)
    }

    /**
     * XaulinXs Customizations — "Predictive Action Badge": conforme o
     * usuário digita, o texto é reprocessado (QsbActionPreviewBuilder)
     * e uma etiqueta abaixo do campo mostra a ação que será executada
     * — antes de apertar Enter. Construído em código (não em um XML
     * do AOSP como search_container_all_apps.xml) para não editar um
     * layout grande do launcher e ficar 100% contido no pacote
     * XaulinXs Customizations.
     */
    private fun View.showXaulinXsTextModeDialog(fallbackIntent: Intent) {
        val appsStore = activityContext.activityComponent.appsStore

        val badgeIcon =
            ImageView(context).apply {
                layoutParams =
                    LinearLayout.LayoutParams(dp(16), dp(16)).apply { marginEnd = dp(8) }
            }
        val badgeText =
            TextView(context).apply {
                textSize = 12f
                setTextColor(context.getColor(R.color.materialColorPrimary))
                setTypeface(typeface, android.graphics.Typeface.BOLD)
            }
        val badgeContainer =
            LinearLayout(context).apply {
                orientation = LinearLayout.HORIZONTAL
                gravity = android.view.Gravity.CENTER_VERTICAL
                setPadding(dp(12), dp(6), dp(12), dp(6))
                setBackgroundResource(R.drawable.xaulinxs_qsb_action_badge_bg)
                visibility = View.GONE
                addView(badgeIcon)
                addView(badgeText)
            }

        val input =
            EditText(context).apply {
                hint = context.getString(R.string.xaulinxs_qsb_text_mode_hint)
                setPadding(48, 32, 48, 32)
            }

        val outerContainer =
            LinearLayout(context).apply {
                orientation = LinearLayout.VERTICAL
                addView(input)
                addView(
                    badgeContainer,
                    LinearLayout.LayoutParams(
                        LinearLayout.LayoutParams.MATCH_PARENT,
                        LinearLayout.LayoutParams.WRAP_CONTENT,
                    ).apply { topMargin = dp(4) },
                )
            }

        input.addTextChangedListener(
            object : TextWatcher {
                override fun beforeTextChanged(s: CharSequence?, start: Int, count: Int, after: Int) {}
                override fun afterTextChanged(s: Editable?) {}
                override fun onTextChanged(s: CharSequence?, start: Int, before: Int, count: Int) {
                    val preview = QsbActionPreviewBuilder.build(appsStore, s?.toString().orEmpty())
                    if (preview == null) {
                        badgeContainer.visibility = View.GONE
                        return
                    }
                    badgeText.text = preview.message
                    badgeIcon.setImageResource(iconResFor(preview.icon))
                    badgeContainer.visibility = View.VISIBLE
                }
            }
        )

        AlertDialog.Builder(context)
            .setTitle(R.string.xaulinxs_qsb_text_mode_dialog_title)
            .setView(outerContainer)
            .setPositiveButton(android.R.string.ok) { _, _ ->
                val raw = input.text?.toString().orEmpty()
                if (raw.isBlank()) {
                    launchQsbIntent(fallbackIntent)
                    return@setPositiveButton
                }
                handleXaulinXsTextModeResult(
                    QsbTextModeCommand.interpret(raw, appsStore, context),
                    fallbackIntent,
                )
            }
            .setNegativeButton(android.R.string.cancel, null)
            .show()
    }

    private fun View.dp(value: Int): Int =
        (value * context.resources.displayMetrics.density).toInt()

    private fun iconResFor(icon: QsbBadgeIcon): Int =
        when (icon) {
            QsbBadgeIcon.OPEN_APP -> android.R.drawable.ic_menu_manage
            QsbBadgeIcon.CALL -> android.R.drawable.ic_menu_call
            QsbBadgeIcon.WHATSAPP_CALL -> android.R.drawable.ic_menu_call
            QsbBadgeIcon.MESSAGE -> android.R.drawable.ic_menu_send
            QsbBadgeIcon.SEARCH -> android.R.drawable.ic_menu_search
            QsbBadgeIcon.NONE -> android.R.drawable.ic_menu_search
        }

    /**
     * Trata o resultado da QSB Inteligente. FreeText (nenhum comando
     * reconhecido) é o único caso que cai para o Modo Web
     * ([fallbackIntent]) — todo o resto é uma ação concreta reconhecida
     * (lançada, pendente de permissão, ou alvo não encontrado), nunca
     * um fallback genérico de busca/browser no lugar da ação pedida.
     */
    private fun View.handleXaulinXsTextModeResult(result: QsbTextModeResult, fallbackIntent: Intent) {
        when (result) {
            is QsbTextModeResult.Launch -> launchQsbIntent(result.intent)
            is QsbTextModeResult.FreeText -> launchQsbIntent(fallbackIntent)
            is QsbTextModeResult.NotFound -> showXaulinXsNotFoundToast(result.reason)
            is QsbTextModeResult.NeedsPermission ->
                requestXaulinXsPermission(result.permission, result.retryAction)
        }
    }

    private fun showXaulinXsNotFoundToast(reason: QsbFailureReason) {
        val messageRes =
            when (reason) {
                QsbFailureReason.APP_NOT_FOUND -> R.string.xaulinxs_qsb_smart_app_not_found
                QsbFailureReason.CONTACT_NOT_FOUND -> R.string.xaulinxs_qsb_smart_contact_not_found
            }
        android.widget.Toast.makeText(context, messageRes, android.widget.Toast.LENGTH_SHORT).show()
    }

    /**
     * Pede a permissão em falta via diálogo explicativo + Activity
     * transparente dedicada (XaulinXsQsbPermissionActivity), em vez de
     * pedir a permissão diretamente pelo Launcher: o Launcher não
     * implementa onRequestPermissionsResult, e adicionar esse override
     * nele mexeria num arquivo grande do AOSP com alto risco de
     * conflito em atualizações futuras. A Activity dedicada resolve o
     * pedido e devolve o resultado via callback estático de curta
     * duração (XaulinXsQsbPermissionCallback), reexecutando
     * [retryAction] automaticamente se concedida — usuário não precisa
     * digitar o comando de novo.
     */
    private fun requestXaulinXsPermission(permission: String, retryAction: QsbAction) {
        AlertDialog.Builder(context)
            .setTitle(R.string.xaulinxs_qsb_smart_permission_title)
            .setMessage(R.string.xaulinxs_qsb_smart_permission_message)
            .setPositiveButton(R.string.xaulinxs_storage_permission_grant) { _, _ ->
                val appsStore = activityContext.activityComponent.appsStore
                XaulinXsQsbPermissionCallback.onGranted = { grantedAction ->
                    // retry() só devolve FreeText no caso defensivo de a
                    // ação reconhecida virar Unrecognized (não deveria
                    // acontecer para uma action já validada pelo parser) —
                    // nesse cenário não há intent de fallback sensato, só
                    // ignora silenciosamente em vez de arriscar um crash
                    // com um Intent vazio.
                    when (val result = QsbTextModeCommand.retry(grantedAction, appsStore, context)) {
                        is QsbTextModeResult.FreeText -> Unit
                        else -> handleXaulinXsTextModeResult(result, Intent())
                    }
                }
                context.startActivity(
                    XaulinXsQsbPermissionActivity.newIntent(context, permission, retryAction)
                        .addFlags(Intent.FLAG_ACTIVITY_NEW_TASK)
                )
            }
            .setNegativeButton(R.string.xaulinxs_storage_permission_deny, null)
            .show()
    }

    private fun View.launchQsbIntent(intent: Intent) {
        intent.addFlags(Intent.FLAG_ACTIVITY_NEW_TASK or Intent.FLAG_ACTIVITY_RESET_TASK_IF_NEEDED)
        if (intent.action == Intent.ACTION_VIEW) {
            // Browser Intent and set the default browser package.
            val resolveInfo =
                runCatching {
                        context.packageManager.resolveActivity(
                            intent,
                            PackageManager.MATCH_DEFAULT_ONLY,
                        )
                    }
                    .getOrNull()
            resolveInfo?.activityInfo?.packageName.apply { intent.setPackage(this) }
        }
        activityContext.startActivitySafely(
            this@OseWidgetView,
            intent,
            this@OseWidgetView.tag as? ItemInfo,
        )
    }

    private class QsbItemInfo : ItemInfo() {

        override fun getStableId() = STABLE_ID
    }

    companion object {
        private const val TAG = "OseWidgetView"

        private val STABLE_ID = Object()

        private fun getTagInfo(provider: AppWidgetProviderInfo?): ItemInfo {
            val info =
                provider?.let { LauncherAppWidgetInfo(INVALID_APPWIDGET_ID, it.provider) }
                    ?: QsbItemInfo()
            info.id = R.id.search_container_hotseat
            info.container = Favorites.CONTAINER_HOTSEAT
            return info
        }
    }
}
