#!/usr/bin/env python3
"""
Fix de build: XaulinXsOptionsSheet.kt (bound genérico errado) +
PopupContainerWithArrow.kt (import faltando de XaulinXsAppOverrides).

Rode este script na raiz do repo (pasta Launcher3/), com o Termux:
    python3 fix_options_sheet_build_errors.py

Idempotente: pode rodar mais de uma vez sem duplicar nada.
"""
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent

SHEET_FILE = REPO_ROOT / "modules/customizations/src/com/xaulinxs/customizations/popup/XaulinXsOptionsSheet.kt"
POPUP_FILE = REPO_ROOT / "src/com/android/launcher3/popup/PopupContainerWithArrow.kt"

errors = []


def fix_options_sheet():
    if not SHEET_FILE.exists():
        errors.append(f"Não encontrei: {SHEET_FILE}")
        return

    text = SHEET_FILE.read_text(encoding="utf-8")

    already_fixed = "AbstractSlideInView<Launcher>" in text
    old_signature = "AbstractSlideInView<ActivityContext>(context, attrs, defStyleAttr)" in text

    if already_fixed:
        print(f"[skip] {SHEET_FILE.name} já está corrigido.")
        return

    if not old_signature:
        errors.append(
            f"{SHEET_FILE.name}: não encontrei a assinatura antiga esperada "
            "(arquivo pode já ter sido editado manualmente de outra forma). "
            "Abortando este arquivo para não sobrescrever edição existente."
        )
        return

    # 1) Adiciona o import de Launcher, se ainda não existir.
    if "import com.android.launcher3.Launcher\n" not in text:
        text = text.replace(
            "import com.android.launcher3.views.AbstractSlideInView\n"
            "import com.android.launcher3.views.ActivityContext\n",
            "import com.android.launcher3.Launcher\n"
            "import com.android.launcher3.views.AbstractSlideInView\n"
            "import com.android.launcher3.views.ActivityContext\n",
            1,
        )

    # 2) Troca o parâmetro genérico ActivityContext -> Launcher e documenta o porquê.
    old_class_block = (
        "/**\n"
        " * Bottom sheet com barrinha de arrastar para as opções da área vazia da tela inicial.\n"
        " */\n"
        "class XaulinXsOptionsSheet\n"
        "@JvmOverloads\n"
        "constructor(context: Context, attrs: AttributeSet? = null, defStyleAttr: Int = 0) :\n"
        "    AbstractSlideInView<ActivityContext>(context, attrs, defStyleAttr) {"
    )
    new_class_block = (
        "/**\n"
        " * Bottom sheet com barrinha de arrastar para as opções da área vazia da tela inicial.\n"
        " *\n"
        " * O parâmetro genérico de [AbstractSlideInView] exige um tipo que seja Context E\n"
        " * ActivityContext ao mesmo tempo (`T extends Context & ActivityContext`). A interface\n"
        " * ActivityContext sozinha não satisfaz esse bound - é preciso a classe concreta real\n"
        " * usada em runtime, que no launcher-phone é sempre [Launcher].\n"
        " */\n"
        "class XaulinXsOptionsSheet\n"
        "@JvmOverloads\n"
        "constructor(context: Context, attrs: AttributeSet? = null, defStyleAttr: Int = 0) :\n"
        "    AbstractSlideInView<Launcher>(context, attrs, defStyleAttr) {"
    )

    if old_class_block not in text:
        errors.append(
            f"{SHEET_FILE.name}: bloco da classe não bateu exatamente com o esperado. "
            "Abortando este arquivo para não sobrescrever edição existente."
        )
        return

    text = text.replace(old_class_block, new_class_block, 1)

    SHEET_FILE.write_text(text, encoding="utf-8")
    print(f"[ok] {SHEET_FILE.name} corrigido (AbstractSlideInView<Launcher>).")


def fix_popup_container():
    if not POPUP_FILE.exists():
        errors.append(f"Não encontrei: {POPUP_FILE}")
        return

    text = POPUP_FILE.read_text(encoding="utf-8")
    import_line = "import com.xaulinxs.customizations.apps.XaulinXsAppOverrides\n"

    if import_line in text:
        print(f"[skip] {POPUP_FILE.name} já tem o import.")
        return

    anchor = "import com.android.launcher3.views.ActivityContext\n"
    if anchor not in text:
        errors.append(
            f"{POPUP_FILE.name}: não encontrei o ponto de ancoragem do import esperado. "
            "Abortando este arquivo para não sobrescrever edição existente."
        )
        return

    text = text.replace(anchor, anchor + import_line, 1)
    POPUP_FILE.write_text(text, encoding="utf-8")
    print(f"[ok] {POPUP_FILE.name} corrigido (import de XaulinXsAppOverrides adicionado).")


def main():
    fix_options_sheet()
    fix_popup_container()

    if errors:
        print("\nERROS:")
        for e in errors:
            print(f"  - {e}")
        sys.exit(1)

    print("\nTudo aplicado. Rode: ./gradlew assembleNoQuickstepDebug")


if __name__ == "__main__":
    main()
