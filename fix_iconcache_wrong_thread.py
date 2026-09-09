#!/usr/bin/env python3
"""
Fix de crash: IllegalStateException "Cache accessed on wrong thread" ao
fechar o popup de app ou trocar nome/icone/esconder.

Causa raiz: XaulinXsAppOverrideRefresher.register chamava
IconCache.getTitleAndIcon diretamente dentro do listener de
XaulinXsAppOverrides.notifyChanged, que roda em Executors.MAIN_EXECUTOR (de
proposito, pois o resto do listener toca Views). Mas IconCache.getTitleAndIcon
so pode ser chamado na worker thread propria do cache
(bgLooper = Executors.MODEL_EXECUTOR.looper) - chamar na main thread dispara
BaseIconCache.assertWorkerThread().

Fix: resolver o icone em Executors.MODEL_EXECUTOR e so entao voltar para
Executors.MAIN_EXECUTOR para tocar nas Views (xaulinXsReapplyIcon /
xaulinXsRefreshFilters).

Rode este script na raiz do repo (pasta Launcher3/), com o Termux:
    python3 fix_iconcache_wrong_thread.py

Idempotente: pode rodar mais de uma vez sem duplicar nada.
"""
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent

TARGET_FILE = (
    REPO_ROOT
    / "modules/customizations/src/com/xaulinxs/customizations/apps/XaulinXsAppOverrideRefresher.kt"
)

OLD_CONTENT = '/*\n * XaulinXs Customizations — não faz parte do AOSP original.\n *\n * Ponte entre XaulinXsAppOverrides (persistência) e a UI ao vivo do launcher.\n * Registrado uma vez em Launcher.onCreate, escuta toda mudança de override\n * (nome, ícone, esconder) e:\n *  - re-resolve título/ícone via IconCache.getTitleAndIcon (que já aplica o\n *    override por cima, ver IconCache.applyXaulinXsOverride) pro AppInfo real\n *    que está na AllAppsStore, e reaplica em toda BubbleTextView visível;\n *  - força a lista de apps a recalcular o filtro de "escondido".\n *\n * Existe como classe separada (em vez de lambda inline em Launcher.java) pra\n * manter a lógica de busca/refresh testável e num só lugar, já que o mesmo\n * fluxo serve tanto pro nome quanto pro ícone quanto pro esconder.\n */\npackage com.xaulinxs.customizations.apps\n\nimport com.android.launcher3.Launcher\nimport com.android.launcher3.LauncherAppState\nimport com.android.launcher3.icons.cache.CacheLookupFlag\nimport com.android.launcher3.model.data.AppInfo\n\nobject XaulinXsAppOverrideRefresher {\n\n    @JvmStatic\n    fun register(launcher: Launcher) {\n        XaulinXsAppOverrides.addOnChangedListener { componentName ->\n            val appsStore = launcher.appsView.appsStore\n            val app = appsStore.apps.firstOrNull { it.componentName == componentName }\n            if (app != null) {\n                LauncherAppState.getInstance(launcher).iconCache.getTitleAndIcon(\n                    app,\n                    CacheLookupFlag.DEFAULT_LOOKUP_FLAG,\n                )\n                appsStore.xaulinXsReapplyIcon(app)\n            }\n            // Independente de o app estar na lista de apps carregada (pode ainda não\n            // estar, se isso rodar muito cedo), sempre reavalia o filtro de escondidos -\n            // é barato (não recarrega dados) e garante que o interruptor "esconder do\n            // menu de aplicativos" reflita na hora.\n            appsStore.xaulinXsRefreshFilters()\n        }\n    }\n}\n'

NEW_CONTENT = '/*\n * XaulinXs Customizations — não faz parte do AOSP original.\n *\n * Ponte entre XaulinXsAppOverrides (persistência) e a UI ao vivo do launcher.\n * Registrado uma vez em Launcher.onCreate, escuta toda mudança de override\n * (nome, ícone, esconder) e:\n *  - re-resolve título/ícone via IconCache.getTitleAndIcon (que já aplica o\n *    override por cima, ver IconCache.applyXaulinXsOverride) pro AppInfo real\n *    que está na AllAppsStore, e reaplica em toda BubbleTextView visível;\n *  - força a lista de apps a recalcular o filtro de "escondido".\n *\n * Existe como classe separada (em vez de lambda inline em Launcher.java) pra\n * manter a lógica de busca/refresh testável e num só lugar, já que o mesmo\n * fluxo serve tanto pro nome quanto pro ícone quanto pro esconder.\n */\npackage com.xaulinxs.customizations.apps\n\nimport com.android.launcher3.Launcher\nimport com.android.launcher3.LauncherAppState\nimport com.android.launcher3.icons.cache.CacheLookupFlag\nimport com.android.launcher3.model.data.AppInfo\nimport com.android.launcher3.util.Executors\n\nobject XaulinXsAppOverrideRefresher {\n\n    @JvmStatic\n    fun register(launcher: Launcher) {\n        XaulinXsAppOverrides.addOnChangedListener { componentName ->\n            val appsStore = launcher.appsView.appsStore\n            val app = appsStore.apps.firstOrNull { it.componentName == componentName }\n            if (app != null) {\n                // IconCache.getTitleAndIcon só pode ser chamado na worker thread própria\n                // do cache (bgLooper = Executors.MODEL_EXECUTOR.looper, ver IconCache.kt) -\n                // chamar direto aqui (este listener já roda no MAIN_EXECUTOR, ver\n                // XaulinXsAppOverrides.notifyChanged) derruba o app com\n                // "Cache accessed on wrong thread". Resolve o título/ícone em\n                // background e só então volta pra main thread pra tocar nas Views.\n                Executors.MODEL_EXECUTOR.execute {\n                    LauncherAppState.getInstance(launcher).iconCache.getTitleAndIcon(\n                        app,\n                        CacheLookupFlag.DEFAULT_LOOKUP_FLAG,\n                    )\n                    Executors.MAIN_EXECUTOR.execute {\n                        appsStore.xaulinXsReapplyIcon(app)\n                        appsStore.xaulinXsRefreshFilters()\n                    }\n                }\n            } else {\n                // App não estava carregado na lista ainda - não há ícone pra\n                // re-resolver, mas o filtro de escondidos precisa ser reavaliado\n                // mesmo assim (é barato, não recarrega dados).\n                appsStore.xaulinXsRefreshFilters()\n            }\n        }\n    }\n}\n'

errors = []


def fix_refresher():
    if not TARGET_FILE.exists():
        errors.append(f"Nao encontrei: {TARGET_FILE}")
        return

    text = TARGET_FILE.read_text(encoding="utf-8")

    if text == NEW_CONTENT:
        print(f"[skip] {TARGET_FILE.name} ja esta corrigido.")
        return

    if text != OLD_CONTENT:
        errors.append(
            f"{TARGET_FILE.name}: conteudo atual nao bate nem com a versao "
            "original esperada nem com a corrigida (arquivo pode ja ter sido "
            "editado manualmente de outra forma). Abortando para nao "
            "sobrescrever edicao existente."
        )
        return

    TARGET_FILE.write_text(NEW_CONTENT, encoding="utf-8")
    print(f"[ok] {TARGET_FILE.name} corrigido (icone resolvido em MODEL_EXECUTOR).")


def main():
    fix_refresher()

    if errors:
        print("\nERROS:")
        for e in errors:
            print(f"  - {e}")
        sys.exit(1)

    print("\nTudo aplicado. Rode: ./gradlew assembleNoQuickstepDebug")


if __name__ == "__main__":
    main()
