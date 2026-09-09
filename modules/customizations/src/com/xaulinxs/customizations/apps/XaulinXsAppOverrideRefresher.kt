/*
 * XaulinXs Customizations — não faz parte do AOSP original.
 *
 * Ponte entre XaulinXsAppOverrides (persistência) e a UI ao vivo do launcher.
 * Registrado uma vez em Launcher.onCreate, escuta toda mudança de override
 * (nome, ícone, esconder) e:
 *  - re-resolve título/ícone via IconCache.getTitleAndIcon (que já aplica o
 *    override por cima, ver IconCache.applyXaulinXsOverride) pro AppInfo real
 *    que está na AllAppsStore, e reaplica em toda BubbleTextView visível;
 *  - força a lista de apps a recalcular o filtro de "escondido".
 *
 * Existe como classe separada (em vez de lambda inline em Launcher.java) pra
 * manter a lógica de busca/refresh testável e num só lugar, já que o mesmo
 * fluxo serve tanto pro nome quanto pro ícone quanto pro esconder.
 */
package com.xaulinxs.customizations.apps

import com.android.launcher3.Launcher
import com.android.launcher3.LauncherAppState
import com.android.launcher3.icons.cache.CacheLookupFlag
import com.android.launcher3.model.data.AppInfo

object XaulinXsAppOverrideRefresher {

    @JvmStatic
    fun register(launcher: Launcher) {
        XaulinXsAppOverrides.addOnChangedListener { componentName ->
            val appsStore = launcher.appsView.appsStore
            val app = appsStore.apps.firstOrNull { it.componentName == componentName }
            if (app != null) {
                LauncherAppState.getInstance(launcher).iconCache.getTitleAndIcon(
                    app,
                    CacheLookupFlag.DEFAULT_LOOKUP_FLAG,
                )
                appsStore.xaulinXsReapplyIcon(app)
            }
            // Independente de o app estar na lista de apps carregada (pode ainda não
            // estar, se isso rodar muito cedo), sempre reavalia o filtro de escondidos -
            // é barato (não recarrega dados) e garante que o interruptor "esconder do
            // menu de aplicativos" reflita na hora.
            appsStore.xaulinXsRefreshFilters()
        }
    }
}
