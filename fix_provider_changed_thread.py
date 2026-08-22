#!/usr/bin/env python3
"""
Fix: crash "CalledFromWrongThreadException" em UiThreadHelper
     (LauncherWidgetHolder.lambda$startListening$1 -> AppWidgetHost.startListening
      -> onProviderChanged -> AppWidgetHostView.updateAppWidget)

Causa raiz: ListenableAppWidgetHost.onProviderChanged() é chamado pelo
framework Android de dentro de AppWidgetHost.startListening(), que o
Launcher3 roda deliberadamente fora da main thread (widgetHolderExecutor /
UI_HELPER_EXECUTOR, a HandlerThread "UiThreadHelper"). super.onProviderChanged()
pode atualizar sincronamente uma AppWidgetHostView já existente na tela
(applyContent -> ViewGroup.addView -> PagedView.requestLayout), e View exige
que só a thread que criou a hierarquia a toque -> crash.

Fix: a parte que chama super.onProviderChanged() (e o initSpans() que
depende dela) passa a rodar via MAIN_EXECUTOR.execute{}. dispatchUpdate()
continua rodando na thread original, pois só empurra um evento pra um
stream reativo (MutableListenableStream) e não toca View.

Rode este script na RAIZ do checkout local do repo (mesmo diretório do
gradlew), dentro do Termux.

Idempotente: se o fix já estiver aplicado, o script não faz nada e avisa.
"""
import sys
from pathlib import Path

TARGET = Path("src/com/android/launcher3/widget/ListenableAppWidgetHost.kt")

OLD_BLOCK = '''    override fun onProviderChanged(appWidgetId: Int, appWidget: AppWidgetProviderInfo) {
        val info = LauncherAppWidgetProviderInfo.fromProviderInfo(ctx, appWidget)
        updateDispatcher.forEach { it.dispatchUpdate(appWidgetId, info) }
        super.onProviderChanged(appWidgetId, info)
        // The super method updates the dimensions of the providerInfo. Update the
        // launcher spans accordingly.
        info.initSpans(ctx, InvariantDeviceProfile.INSTANCE.get(ctx))
    }'''

NEW_BLOCK = '''    override fun onProviderChanged(appWidgetId: Int, appWidget: AppWidgetProviderInfo) {
        val info = LauncherAppWidgetProviderInfo.fromProviderInfo(ctx, appWidget)
        updateDispatcher.forEach { it.dispatchUpdate(appWidgetId, info) }
        // XaulinXs fix (crash real confirmado via logcat do Galaxy A35,
        // CalledFromWrongThreadException em UiThreadHelper):
        // onProviderChanged() é chamado pelo framework de dentro de
        // AppWidgetHost.startListening(), que o Launcher3 propositalmente
        // roda fora da main thread (via widgetHolderExecutor /
        // UI_HELPER_EXECUTOR, a "UiThreadHelper" HandlerThread), para não
        // travar a UI. Mas super.onProviderChanged() aqui embaixo pode
        // atualizar sincronamente uma AppWidgetHostView já existente
        // (applyContent -> ViewGroup.addView -> PagedView.requestLayout),
        // e View exige que só a thread que criou a hierarquia a toque.
        // Fix: garante que a parte que mexe em view rode na main thread,
        // mesmo padrão já usado em XaulinXsWidgetFontForcer.applyTo().
        val runOnMain = Runnable {
            callSuperOnProviderChanged(appWidgetId, info)
            // The super method updates the dimensions of the providerInfo. Update the
            // launcher spans accordingly.
            info.initSpans(ctx, InvariantDeviceProfile.INSTANCE.get(ctx))
        }
        MAIN_EXECUTOR.execute(runOnMain)
    }

    // Kotlin não permite `super.foo()` dentro de uma lambda/Runnable (o `this`
    // implícito lá dentro não é mais a instância externa) — isolando a chamada
    // a super numa função membro normal contorna isso.
    private fun callSuperOnProviderChanged(
        appWidgetId: Int,
        appWidget: AppWidgetProviderInfo,
    ) {
        super.onProviderChanged(appWidgetId, appWidget)
    }'''

MARKER = "callSuperOnProviderChanged"


def main() -> int:
    if not Path("gradlew").exists():
        print("ERRO: rode este script na raiz do checkout (onde está o gradlew).")
        return 1

    if not TARGET.exists():
        print(f"ERRO: não encontrei {TARGET}. O repo mudou de estrutura?")
        return 1

    content = TARGET.read_text(encoding="utf-8")

    if MARKER in content:
        print(f"Já aplicado — {TARGET} já tem o fix (marcador '{MARKER}' presente). Nada a fazer.")
        return 0

    if OLD_BLOCK not in content:
        print(
            f"ERRO: não encontrei o bloco esperado de onProviderChanged() em {TARGET}.\n"
            "O arquivo pode já ter sido editado manualmente de outro jeito. "
            "Abortando sem mexer em nada — me manda o conteúdo atual do arquivo "
            "que eu ajusto o patch."
        )
        return 1

    content = content.replace(OLD_BLOCK, NEW_BLOCK)
    TARGET.write_text(content, encoding="utf-8")

    print(f"OK: fix aplicado em {TARGET}.")
    print("Agora: git add -A && git commit -m 'fix: crash UiThreadHelper em onProviderChanged' && git push")
    print("Depois: ./gradlew assembleNoQuickstepDebug")
    return 0


if __name__ == "__main__":
    sys.exit(main())
