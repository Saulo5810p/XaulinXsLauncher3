#!/usr/bin/env python3
"""
Aplica o fix da QSB "invisível" na Hotseat em densidade real de telas
de telefone (caso do Samsung Galaxy A35 em dpi normal, ~384).

CAUSA RAIZ (confirmada lendo o código, não suposição):

Hotseat.onMeasure() mede a view da QSB com:
    mQsb.measure(
        makeMeasureSpec(dp.getHotseatProfile().getQsbWidth(), EXACTLY),
        ...
    )

getQsbWidth() vem de HotseatProfile.qsbWidth, calculado em
HotseatProfile.kt -> recalculateHotseatWidthAndBorderSpace(). Esse
método tinha um branch:

    if (!isScalableGrid)
        return HotseatWithBorderAndSpace(..., qsbWidth = 0, ...)

isScalableGrid vem do GridOption escolhido em res/xml/device_profiles.xml
a partir do "closest display option" pra tela do aparelho. Nos grids de
TELEFONE comuns (3_by_3, 4_by_4, 5_by_5 — o "Large Phone" do A35 é
5_by_5), o atributo launcher:isScalable não é declarado, então usa o
default "false". Só grids de TABLET/desktop/paisagem fixa
(6_by_5, desktop_6_by_5, fixed_landscape_mode) têm isScalable="true".

Resultado: em densidade real, o A35 cai no grid 5_by_5
(isScalable=false) -> qsbWidth SEMPRE 0 -> QSB medida com largura exata
zero -> nunca aparece, mesmo estando corretamente adicionada à view
hierarchy (Hotseat.addView(mQsb) roda incondicionalmente). Ao forçar
densidade 774, o algoritmo de "closest match" de tela passa a escolher
por acidente um grid de TABLET (isScalable=true), que por sua vez
calcula a largura de verdade — por isso a QSB "aparece" lá. Não é a
densidade em si que resolve; é o grid errado sendo selecionado.

O próprio comentário do código original em calculateQsbWidth() já
documentava a intenção: "QSB width is always calculated because when
in 3 button nav the width doesn't follow the width of the hotseat" —
ou seja, não deveria depender de isScalableGrid.

FIX (cirúrgico, sem tocar em mais nada do algoritmo de grid escalável):
dentro do branch !isScalableGrid, calcula qsbWidth de verdade
reaproveitando a função calculateQsbWidth() já existente, com
columnSpan = inv.numColumns (mesmo valor já usado nesse branch pros
outros campos). widthPx, borderSpace e numShownIcons continuam
exatamente como antes — só qsbWidth passa a refletir a largura real.
Isso NÃO ativa o algoritmo de scaling de grid escalável (que redimensiona
ícones/padding pra manter aspect ratio — comportamento pensado pra
tablet, não queremos isso no telefone). Alternativa descartada:
adicionar isScalable="true" no grid 5_by_5 em device_profiles.xml —
rejeitada porque isso ligaria esse algoritmo de scaling completo,
mudando tamanho de ícones e padding do workspace inteiro, um efeito
colateral muito maior que o necessário.

Não requer clonar: assume que o repo já existe localmente (padrão
~/Launcher3) e aplica em cima do checkout, para não perder mudanças
não commitadas.
"""
import argparse
import subprocess
import sys
from pathlib import Path

PATCH_FILENAME = "fix_qsb_visibility.patch"

PATCH_CONTENT = '''diff --git a/src/com/android/launcher3/deviceprofile/HotseatProfile.kt b/src/com/android/launcher3/deviceprofile/HotseatProfile.kt
index 78bc475..2bc4302 100644
--- a/src/com/android/launcher3/deviceprofile/HotseatProfile.kt
+++ b/src/com/android/launcher3/deviceprofile/HotseatProfile.kt
@@ -145,14 +145,58 @@ data class HotseatProfile(
             isVerticalBarLayout: Boolean,
             numShownHotseatIconsParam: Int,
         ): HotseatWithBorderAndSpace {
-            if (!isScalableGrid)
+            if (!isScalableGrid) {
+                // XaulinXs fix: no grid não-escalável (grid padrão de
+                // telefone, ex. "5_by_5"/Large Phone — o caso do
+                // Samsung Galaxy A35 em densidade real), este branch
+                // sempre zerava qsbWidth incondicionalmente. Hotseat
+                // mede a QSB com makeMeasureSpec(qsbWidth, EXACTLY), e
+                // largura exata 0 faz a QSB nunca aparecer — mesmo ela
+                // estando corretamente adicionada à hierarquia de views
+                // (addView(mQsb) sempre roda). Isso só não acontecia em
+                // densidades altas o bastante para o algoritmo de
+                // "closest display option" cair, por acidente, num
+                // GridOption com isScalable=true (ex. "6_by_5", grid de
+                // tablet) — não é um comportamento pretendido, é uma
+                // seleção de grid errada mascarando o bug.
+                // O próprio comentário de calculateQsbWidth() acima já
+                // documenta a intenção original: "QSB width is always
+                // calculated" — não deveria depender de isScalableGrid.
+                // Fix: calcula qsbWidth de verdade aqui também,
+                // reaproveitando calculateQsbWidth() com columnSpan =
+                // inv.numColumns (mesmo valor já usado para widthPx e
+                // columnSpan neste branch), sem alterar nada mais do
+                // comportamento do grid fixo de telefone (widthPx,
+                // borderSpace, numShownIcons continuam 0/inalterados —
+                // só qsbWidth passa a refletir a largura real).
+                val nonScalableQsbWidth =
+                    calculateQsbWidth(
+                        borderAndSpace =
+                            HotseatBorderAndSpace(
+                                widthPx = 0,
+                                columnSpan = inv.numColumns,
+                                borderSpace = 0,
+                            ),
+                        workspaceProfile = workspaceProfile,
+                        inv = inv,
+                        panelCount = panelCount,
+                        numShownHotseatIcons = numShownHotseatIconsParam,
+                        isQsbInline = hotseatProfileInitialValues.isQsbInline,
+                        // coerceAtLeast(0): MeasureSpec.EXACTLY com
+                        // largura negativa é comportamento indefinido —
+                        // salvaguarda defensiva, não deveria ocorrer em
+                        // grids de telefone normais, mas garante que
+                        // nunca voltamos a pior do que "QSB invisível"
+                        // (0px) em vez de crashar.
+                    ).coerceAtLeast(0)
                 return HotseatWithBorderAndSpace(
                     widthPx = 0,
                     numShownIcons = numShownHotseatIconsParam,
                     columnSpan = inv.numColumns,
-                    qsbWidth = 0,
+                    qsbWidth = nonScalableQsbWidth,
                     borderSpace = 0,
                 )
+            }
 
             var numShownHotseatIcons = numShownHotseatIconsParam
             var borderAndSpace =
'''


def run(cmd, cwd, check=True):
    print(f"$ {' '.join(cmd)}")
    result = subprocess.run(cmd, cwd=cwd, text=True)
    if check and result.returncode != 0:
        sys.exit(f"Comando falhou: {' '.join(cmd)}")
    return result.returncode


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--repo",
        default=str(Path.home() / "Launcher3"),
        help="Caminho do checkout local (padrão: ~/Launcher3)",
    )
    parser.add_argument(
        "--skip-build",
        action="store_true",
        help="Não rodar ./gradlew assembleDebug ao final",
    )
    args = parser.parse_args()

    repo = Path(args.repo).expanduser().resolve()
    if not repo.is_dir():
        sys.exit(f"Repo não encontrado em {repo}. Use --repo <caminho>.")

    target_file = (
        repo / "src/com/android/launcher3/deviceprofile/HotseatProfile.kt"
    )
    if not target_file.is_file():
        sys.exit(f"{target_file} não existe neste checkout.")

    if "nonScalableQsbWidth" in target_file.read_text(encoding="utf-8"):
        print("Fix já aplicado neste checkout (idempotente) — nada a fazer.")
    else:
        patch_path = repo / PATCH_FILENAME
        patch_path.write_text(PATCH_CONTENT, encoding="utf-8")

        print("Conferindo se o patch aplica limpo (git apply --check)...")
        run(["git", "apply", "--check", PATCH_FILENAME], cwd=repo)

        print("Aplicando patch...")
        run(["git", "apply", PATCH_FILENAME], cwd=repo)

        patch_path.unlink()

        print("\nDiff aplicado:")
        run(
            [
                "git",
                "diff",
                "src/com/android/launcher3/deviceprofile/HotseatProfile.kt",
            ],
            cwd=repo,
            check=False,
        )

    if not args.skip_build:
        print("\nCompilando (./gradlew assembleDebug)...")
        gradlew = repo / "gradlew"
        if not gradlew.is_file():
            sys.exit("gradlew não encontrado no repo — pulei o build.")
        run(["chmod", "+x", "gradlew"], cwd=repo)
        run(["./gradlew", "assembleDebug"], cwd=repo)
        print("\nBuild OK.")
    else:
        print("\n--skip-build: pulei a compilação.")

    print(
        "\nPróximo passo: instalar o APK debug em DENSIDADE REAL (384, "
        "sem forçar dpi) e confirmar que a QSB aparece na dock. Também "
        "checar visualmente se ela não se sobrepõe aos ícones — o "
        "design clássico de telefone usa uma faixa própria acima da "
        "linha de ícones (dp.getQsbOffsetY()), mas vale confirmar no "
        "aparelho real."
    )


if __name__ == "__main__":
    main()
