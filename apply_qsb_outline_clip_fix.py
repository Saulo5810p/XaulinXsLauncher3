#!/usr/bin/env python3
"""
apply_qsb_outline_clip_fix.py

XaulinXsLauncher3 — corrige o bug real do slider "Tamanho"/"Largura"
da QSB não ter efeito visual acima de 100% (abaixo de 100% já
funcionava desde o fix anterior).

Causa raiz REAL (diferente do fix já aplicado antes):
BaseLauncherAppWidgetHostView (classe-base de OseWidgetView) chama
setClipToOutline(true) no construtor e nunca desliga. O
ViewOutlineProvider padrão usado por esse host define o outline como
outline.setRect(0, 0, view.getWidth(), view.getHeight()) — um
retângulo travado nos bounds MEDIDOS do host (Hotseat.onMeasure faz
mQsb.measure(EXACTLY, EXACTLY)). setClipToOutline corta pelo outline
de forma INDEPENDENTE de clipChildren/clipToPadding (já desligados
num fix anterior) — são dois mecanismos de recorte diferentes no
Android. O BubbleTextView filho, escalado via scaleX/scaleY conforme
o slider, continua desenhando normalmente além dos bounds (nada muda
no measure/layout, só a transformação visual), mas era cortado por
esse outline sempre que a escala passava de 100%. Abaixo de 100% o
conteúdo encolhe PARA DENTRO do outline, por isso "funcionava" só
nesse sentido.

Fix: clipToOutline = false no init{} do OseWidgetView, ao lado dos
outros dois clips já desligados. Escopado só a este host (a QSB não
usa cantos arredondados via esse mecanismo), sem afetar outros
widgets do launcher.

Uso:
    python3 apply_qsb_outline_clip_fix.py [caminho_do_repo]

Se caminho_do_repo não for passado, usa o diretório atual.
Idempotente: pode rodar quantas vezes quiser, sem duplicar nada.
"""

import sys
from pathlib import Path

TARGET_FILE = "src/com/android/launcher3/qsb/OseWidgetView.kt"

MARK_APPLIED = "clipToOutline = false"

OLD_BLOCK = (
    '        clipChildren = false\n'
    '        clipToPadding = false\n'
    '        activityContext.appWidgetHolder?.onViewCreationCallback?.accept(this)\n'
)
NEW_BLOCK = (
    '        clipChildren = false\n'
    '        clipToPadding = false\n'
    '        // XaulinXs fix — XAULINXS_QSB_SIZE_SLIDER_OUTLINE_CLIP_FIX: o fix\n'
    '        // acima (clipChildren/clipToPadding) não era suficiente sozinho.\n'
    '        // BaseLauncherAppWidgetHostView (classe-base deste host) chama\n'
    '        // setClipToOutline(true) no construtor e nunca desliga — o\n'
    '        // ViewOutlineProvider padrão (VIEW_OUTLINE_PROVIDER, usado\n'
    '        // sempre que o launcher não está aplicando cantos arredondados\n'
    '        // neste widget) define o outline como exatamente\n'
    '        // outline.setRect(0, 0, view.getWidth(), view.getHeight()), ou\n'
    '        // seja: um retângulo travado nos bounds MEDIDOS deste host\n'
    '        // (Hotseat.onMeasure faz mQsb.measure(EXACTLY, EXACTLY)).\n'
    '        // setClipToOutline corta pelo outline INDEPENDENTE de\n'
    '        // clipChildren/clipToPadding — são dois mecanismos de recorte\n'
    '        // diferentes no Android. O BubbleTextView filho escalado via\n'
    '        // scaleX/scaleY continua desenhando normalmente por cima/além\n'
    '        // dos bounds (nada muda no measure/layout, só na transformação\n'
    '        // visual), mas era cortado por este outline sempre que a escala\n'
    '        // passava de 100% — abaixo de 100% o conteúdo encolhe PARA\n'
    '        // DENTRO do outline, por isso "funcionava". Fix: desliga o\n'
    '        // clip-por-outline neste host específico (a QSB não usa cantos\n'
    '        // arredondados via este mecanismo, então não há regressão\n'
    '        // visual esperada).\n'
    '        clipToOutline = false\n'
    '        activityContext.appWidgetHolder?.onViewCreationCallback?.accept(this)\n'
)


def fail(msg: str) -> None:
    print(f"[ERRO] {msg}")
    sys.exit(1)


def main() -> None:
    repo_root = Path(sys.argv[1]) if len(sys.argv) > 1 else Path.cwd()
    target = repo_root / TARGET_FILE

    if not target.is_file():
        fail(f"Não encontrei {TARGET_FILE} em {repo_root}. "
             f"Rode este script dentro da raiz do repo, ou passe o caminho como argumento.")

    text = target.read_text(encoding="utf-8")

    if MARK_APPLIED in text:
        print("Nada para aplicar — o fix já estava presente neste arquivo.")
        return

    if OLD_BLOCK not in text:
        fail(
            f"Não encontrei o bloco esperado (clipChildren/clipToPadding seguido de "
            f"activityContext.appWidgetHolder...) em {TARGET_FILE}. O arquivo pode já "
            "ter sido editado manualmente de forma diferente — abortando sem tocar em "
            "nada, pra não sobrescrever edição sua."
        )

    text = text.replace(OLD_BLOCK, NEW_BLOCK, 1)
    target.write_text(text, encoding="utf-8")

    print(f"Arquivo atualizado: {TARGET_FILE}")
    print(
        "\nPronto. Compile com:\n"
        "  ./gradlew assembleNoQuickstepDebug\n"
        "\nTeste sugerido:\n"
        "  1) Abrir Configurações da QSB (long-press na barra ou Settings).\n"
        "  2) Subir o slider 'Tamanho' e/ou 'Largura' para acima de 100%\n"
        "     (ex.: 150%) e confirmar visualmente que a barra CRESCE de\n"
        "     verdade, sem cortar/travar.\n"
        "  3) Testar também abaixo de 100%, pra garantir que continua\n"
        "     funcionando como antes (sem regressão)."
    )


if __name__ == "__main__":
    main()
