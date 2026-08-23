#!/usr/bin/env python3
"""
Fix: build falhou com "Expecting a top level declaration" e "imports are
only allowed in the beginning of file" em XaulinXsColorPalette.kt.

Causa raiz: no bloco de comentário do topo do arquivo, o comentário
continha literalmente o texto "Surface*/Outline*" -- e "*/" é o
terminador de comentário de bloco em Kotlin (mesma regra do Java/C).
O comentário fechava ali, no meio da linha 15, em vez de na linha 29
onde eu pretendia. Tudo entre a linha 15 e o "package"/imports reais
passou a ser lido como código Kotlin solto (daí "Expecting a top level
declaration" repetido), e quando o parser finalmente chegava no
"import androidx.core.graphics.ColorUtils" real, ele já não considerava
mais esse import como estando "no início do arquivo".

Fix: troca "Surface*/Outline*" por "Surface e Outline" no comentário --
sem mudança de comportamento, só de texto explicativo.

Rode este script na RAIZ do checkout local do repo (mesmo diretório do
gradlew), dentro do Termux. Idempotente.
"""
import sys
from pathlib import Path

TARGET = Path(
    "modules/customizations/src/com/xaulinxs/customizations/theme/XaulinXsColorPalette.kt"
)

OLD = " * Surface*/Outline*) são derivadas automaticamente a partir do matiz da"
NEW = " * Surface e Outline) são derivadas automaticamente a partir do matiz da"


def main() -> int:
    if not Path("gradlew").exists():
        print("ERRO: rode este script na raiz do checkout (onde está o gradlew).")
        return 1

    if not TARGET.exists():
        print(f"ERRO: não encontrei {TARGET}. Você já rodou apply_custom_colors.py?")
        return 1

    content = TARGET.read_text(encoding="utf-8")

    if NEW in content:
        print("Já corrigido — nada a fazer.")
        return 0

    if OLD not in content:
        print(
            f"ERRO: não encontrei o texto esperado em {TARGET}.\n"
            "O arquivo pode ter sido editado manualmente. Abortando sem mexer "
            "em nada — me manda o conteúdo atual do arquivo (linhas 1-30) que "
            "eu ajusto o patch."
        )
        return 1

    content = content.replace(OLD, NEW)
    TARGET.write_text(content, encoding="utf-8")

    print(f"OK: corrigido {TARGET}.")
    print("Agora: git add -A && git commit -m 'fix: comentário Kotlin fechando cedo demais' && git push")
    print("Depois: ./gradlew assembleNoQuickstepDebug")
    return 0


if __name__ == "__main__":
    sys.exit(main())
