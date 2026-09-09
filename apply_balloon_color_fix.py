#!/usr/bin/env python3
"""
apply_balloon_color_fix.py
===========================

Script para o repositório LOCAL do XaulinXsLauncher3 (o que você já tem
clonado, por exemplo em ~/Launcher3 no Termux). Este script NÃO clona nada
da internet — ele procura a pasta do repositório que já existe no seu
dispositivo e edita o arquivo direto nela.

O QUE ESTE SCRIPT FAZ
----------------------
Aponta o fundo do retângulo popup de opções da workspace
(com.xaulinxs.customizations.popup.XaulinXsOptionsSheet — o popup que
aparece ao segurar o dedo em área vazia da tela inicial, com as opções
"Plano de fundo e estilo / Widgets / Lista de apps / Configurações")
para a MESMA customização de cor já usada pelos balões dos aplicativos
(com.xaulinxs.customizations.theme.XaulinXsBalloonColor):

  - Se a cor manual dos balões estiver DESLIGADA: usa a cor extraída do
    papel de parede atual (WallpaperColorHints), exatamente como os
    balões dos apps já fazem.
  - Se estiver LIGADA: usa a cor manual escolhida no editor hex/paleta
    (BALLOON_COLOR_ARGB).
  - Se nenhuma extração estiver disponível: cai no comportamento padrão
    do AOSP (fundo estático), sem quebrar nada.

Além disso, remove o "scrim" (véu de cor) que cobria de branco/cinza a
área da tela onde o retângulo do popup não aparece, deixando o papel de
parede visível ali (em vez de aplicar qualquer tingimento).

O retângulo (balão) dos atalhos de aplicativo (ArrowPopup / OptionsPopupView
clássico) NÃO é tocado por este script — ele já segue XaulinXsBalloonColor
corretamente e não foi reportado como quebrado.

COMO O SCRIPT ACHA O SEU REPOSITÓRIO
-------------------------------------
Por padrão (sem passar --repo-dir), o script procura, nesta ordem:
  1. O diretório atual (de onde você rodou o script) e seus pais, subindo
     até achar um que contenha o arquivo alvo.
  2. Uma busca recursiva (até 6 níveis de profundidade) a partir de
     $HOME (ex.: ~/Launcher3 no Termux) por uma pasta que contenha o
     arquivo alvo no caminho esperado.

Se achar mais de um candidato, o script lista todos e pede para você
rodar de novo com --repo-dir apontando para o certo. Se não achar
nenhum, também avisa e pede --repo-dir.

COMO USAR
---------
    # rodando de dentro da pasta do repo (ex.: cd ~/Launcher3):
    python3 apply_balloon_color_fix.py --dry-run   # só mostra o diff
    python3 apply_balloon_color_fix.py             # aplica de verdade

    # ou apontando o caminho manualmente:
    python3 apply_balloon_color_fix.py --repo-dir ~/Launcher3

    # depois de conferir que compila, se quiser versionar:
    python3 apply_balloon_color_fix.py --repo-dir ~/Launcher3 --commit
    python3 apply_balloon_color_fix.py --repo-dir ~/Launcher3 --commit --push

O script nunca clona, nunca baixa nada da internet, e só cria commit ou
faz push se você passar --commit / --push explicitamente.
"""

from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path

TARGET_RELATIVE_PATH = (
    "modules/customizations/src/com/xaulinxs/customizations/popup/"
    "XaulinXsOptionsSheet.kt"
)

MAX_SEARCH_DEPTH = 6

# ---------------------------------------------------------------------------
# Trechos originais (âncoras) que devem existir no arquivo antes da edição,
# e o texto novo que os substitui. Se uma âncora não for encontrada (porque
# o arquivo já foi editado, ou mudou de forma inesperada), o script para e
# avisa em vez de aplicar uma edição errada.
# ---------------------------------------------------------------------------

OLD_IMPORTS = """import android.content.Context
import android.util.AttributeSet
import android.view.LayoutInflater
import android.view.View
import android.widget.LinearLayout
import com.android.launcher3.R
import com.android.launcher3.model.data.ItemInfo
import com.android.launcher3.popup.PopupData
import com.android.launcher3.shortcuts.DeepShortcutView
import com.android.launcher3.util.Themes
import com.android.launcher3.Launcher
import com.android.launcher3.views.AbstractSlideInView
import com.android.launcher3.views.ActivityContext"""

NEW_IMPORTS = """import android.content.Context
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
import com.xaulinxs.customizations.theme.XaulinXsBalloonColor"""

OLD_ON_FINISH_INFLATE = """    override fun onFinishInflate() {
        super.onFinishInflate()
        mContent = findViewById(R.id.xaulinxs_sheet_content)
        rowsContainer = findViewById(R.id.xaulinxs_sheet_rows)
    }"""

NEW_ON_FINISH_INFLATE = """    override fun onFinishInflate() {
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
    }"""

OLD_GET_SCRIM_COLOR = """    override fun getScrimColor(context: Context): Int {
        return Themes.getAttrColor(context, R.attr.allAppsScrimColor)
    }"""

NEW_GET_SCRIM_COLOR = """    /*
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
    }"""


class PatchError(RuntimeError):
    pass


def run(cmd: list[str], cwd: Path | None = None) -> str:
    result = subprocess.run(cmd, cwd=cwd, capture_output=True, text=True)
    if result.returncode != 0:
        raise PatchError(
            f"Comando falhou: {' '.join(cmd)}\n"
            f"stdout: {result.stdout}\nstderr: {result.stderr}"
        )
    return result.stdout


# ---------------------------------------------------------------------------
# Busca do repositório local (sem clonar nada)
# ---------------------------------------------------------------------------

def candidate_has_target(candidate: Path) -> bool:
    return (candidate / TARGET_RELATIVE_PATH).is_file()


def search_upwards_from_cwd() -> Path | None:
    here = Path.cwd().resolve()
    for folder in [here, *here.parents]:
        if candidate_has_target(folder):
            return folder
    return None


def search_downwards_from_home(max_depth: int = MAX_SEARCH_DEPTH) -> list[Path]:
    home = Path.home()
    matches: list[Path] = []
    start_depth = len(home.parts)

    # Ignora pastas pesadas/irrelevantes para não deixar a busca lenta.
    skip_names = {
        ".git", "build", ".gradle", "node_modules", ".idea",
        ".cxx", "out", ".m2", ".cache",
    }

    stack = [home]
    while stack:
        current = stack.pop()
        try:
            depth = len(current.parts) - start_depth
        except ValueError:
            depth = 0
        if depth > max_depth:
            continue
        if candidate_has_target(current):
            matches.append(current)
            # não desce mais dentro de um repo já encontrado
            continue
        try:
            children = [c for c in current.iterdir() if c.is_dir()]
        except (PermissionError, OSError):
            continue
        for child in children:
            if child.name in skip_names or child.name.startswith("."):
                continue
            stack.append(child)
    return matches


def find_repo_dir(explicit: Path | None) -> Path:
    if explicit:
        explicit = explicit.expanduser().resolve()
        if not candidate_has_target(explicit):
            raise PatchError(
                f"O caminho informado em --repo-dir ({explicit}) não contém "
                f"o arquivo esperado ({TARGET_RELATIVE_PATH}). Confira o "
                "caminho da sua pasta do repositório (ex.: ~/Launcher3)."
            )
        return explicit

    found = search_upwards_from_cwd()
    if found:
        return found

    matches = search_downwards_from_home()
    if len(matches) == 1:
        return matches[0]
    if len(matches) > 1:
        listed = "\n".join(f"  - {m}" for m in matches)
        raise PatchError(
            "Achei mais de uma pasta de repositório com esse arquivo:\n"
            f"{listed}\n"
            "Rode de novo passando --repo-dir com o caminho certo."
        )

    raise PatchError(
        "Não encontrei automaticamente a pasta do seu repositório "
        f"(procurei a partir do diretório atual e em até {MAX_SEARCH_DEPTH} "
        f"níveis dentro de {Path.home()}). Rode o script de dentro da pasta "
        "do repositório (ex.: cd ~/Launcher3 && python3 apply_balloon_color_fix.py) "
        "ou passe --repo-dir ~/caminho/para/o/repo."
    )


# ---------------------------------------------------------------------------
# Aplicação do patch
# ---------------------------------------------------------------------------

def apply_single_replacement(text: str, old: str, new: str, description: str) -> str:
    count = text.count(old)
    if count == 0:
        raise PatchError(
            f"Âncora não encontrada para '{description}'. O arquivo pode já "
            "ter sido editado, ou o conteúdo mudou no repositório. Nenhuma "
            "alteração foi aplicada por segurança."
        )
    if count > 1:
        raise PatchError(
            f"Âncora de '{description}' apareceu {count} vezes (esperado "
            "1). Abortando por segurança para não aplicar a troca no lugar "
            "errado."
        )
    return text.replace(old, new, 1)


def validate_kotlin_braces(text: str, target: Path) -> None:
    """Checagem simples de sanidade: chaves e parênteses continuam
    equilibrados depois da edição (não garante que compila, mas pega erros
    grosseiros de substituição de texto)."""
    for open_ch, close_ch, name in [("{", "}", "chaves"), ("(", ")", "parênteses")]:
        balance = 0
        for ch in text:
            if ch == open_ch:
                balance += 1
            elif ch == close_ch:
                balance -= 1
            if balance < 0:
                raise PatchError(
                    f"Validação falhou em {target.name}: {name} desbalanceados "
                    "após a edição (fechando antes de abrir). Nenhuma escrita "
                    "foi persistida."
                )
        if balance != 0:
            raise PatchError(
                f"Validação falhou em {target.name}: {name} desbalanceados "
                f"após a edição (saldo final {balance}). Nenhuma escrita foi "
                "persistida."
            )
    if "XaulinXsBalloonColor.getBalloonColorOverride" not in text:
        raise PatchError(
            "Validação falhou: chamada a getBalloonColorOverride não "
            "encontrada no resultado final."
        )
    if "override fun getScrimColor(context: Context): Int {\n        return -1\n    }" not in text:
        raise PatchError(
            "Validação falhou: getScrimColor não ficou retornando -1 no "
            "resultado final."
        )


def patch_options_sheet(repo_dir: Path) -> tuple[Path, str, str]:
    target = repo_dir / TARGET_RELATIVE_PATH
    if not target.is_file():
        raise PatchError(f"Arquivo alvo não encontrado: {target}")

    original_text = target.read_text(encoding="utf-8")
    text = original_text

    text = apply_single_replacement(text, OLD_IMPORTS, NEW_IMPORTS, "bloco de imports")
    text = apply_single_replacement(
        text,
        OLD_ON_FINISH_INFLATE,
        NEW_ON_FINISH_INFLATE,
        "onFinishInflate() / applyBalloonColorBackground()",
    )
    text = apply_single_replacement(
        text, OLD_GET_SCRIM_COLOR, NEW_GET_SCRIM_COLOR, "getScrimColor()"
    )

    validate_kotlin_braces(text, target)

    return target, original_text, text


def print_diff(original_text: str, patched_text: str) -> None:
    import difflib

    diff = "".join(
        difflib.unified_diff(
            original_text.splitlines(keepends=True),
            patched_text.splitlines(keepends=True),
            fromfile=f"a/{TARGET_RELATIVE_PATH}",
            tofile=f"b/{TARGET_RELATIVE_PATH}",
        )
    )
    print("\n===== DIFF =====")
    print(diff if diff.strip() else "(sem diferenças)")
    print("===== FIM DO DIFF =====\n")


def main() -> int:
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument(
        "--repo-dir",
        type=Path,
        default=None,
        help="Caminho da pasta do SEU repositório já existente (ex.: ~/Launcher3). "
        "Se omitido, o script procura automaticamente.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Só mostra o diff das mudanças, não grava nada em disco.",
    )
    parser.add_argument(
        "--commit",
        action="store_true",
        help="Depois de gravar, cria um commit local com a alteração (não faz push sozinho).",
    )
    parser.add_argument(
        "--push",
        action="store_true",
        help="Depois de --commit, envia (git push) para o remoto 'origin'. "
        "Requer que você já tenha autenticação git configurada no repo.",
    )
    args = parser.parse_args()

    try:
        repo_dir = find_repo_dir(args.repo_dir)
        print(f"Repositório encontrado em: {repo_dir}")

        target, original_text, patched_text = patch_options_sheet(repo_dir)
        print(f"Arquivo alvo: {target}")

        if original_text == patched_text:
            print("Nada mudou (arquivo já estava igual ao esperado?). Abortando.")
            return 1

        print_diff(original_text, patched_text)

        if args.dry_run:
            print("(--dry-run: nada foi gravado em disco)")
            return 0

        target.write_text(patched_text, encoding="utf-8")
        print(f"Arquivo gravado com sucesso: {target}")

        if args.commit:
            run(["git", "add", TARGET_RELATIVE_PATH], cwd=repo_dir)
            commit_message = (
                "XaulinXs Customizations: retângulo de opções da workspace "
                "segue a cor de XaulinXsBalloonColor e remove o scrim "
                "estático para mostrar o papel de parede"
            )
            run(["git", "commit", "-m", commit_message], cwd=repo_dir)
            print("Commit criado localmente.")

            if args.push:
                run(["git", "push", "origin", "HEAD"], cwd=repo_dir)
                print("Push enviado para o remoto 'origin'.")
        else:
            print(
                "Nenhum commit foi criado (rode com --commit para commitar, "
                "e --commit --push para também enviar ao GitHub)."
            )

        return 0

    except PatchError as exc:
        print(f"\nERRO: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
