#!/usr/bin/env python3
"""
Corrige o erro de build:
  Unresolved reference 'XaulinXsQsbPermissionCallback'
  Unresolved reference 'XaulinXsQsbPermissionActivity'
em OseWidgetView.kt.

Causa: as classes existem em com.xaulinxs.customizations.qsb, mas não
estão importadas no arquivo (mesmo padrão dos bugs anteriores do
LauncherAppModule.kt com o widget picker).

Uso (no Termux, dentro de ~/Launcher3):
    python fix_osewidgetview_imports.py
"""
import sys
from pathlib import Path

# Ajuste este caminho se o seu projeto não estiver em ~/Launcher3
DEFAULT_PATH = Path.home() / "Launcher3" / "src" / "com" / "android" / "launcher3" / "qsb" / "OseWidgetView.kt"

ANCHOR_IMPORT = "import com.xaulinxs.customizations.qsb.QsbTextModeResult"
NEW_IMPORTS = (
    "import com.xaulinxs.customizations.qsb.QsbTextModeResult\n"
    "import com.xaulinxs.customizations.qsb.XaulinXsQsbPermissionActivity\n"
    "import com.xaulinxs.customizations.qsb.XaulinXsQsbPermissionCallback"
)


def main():
    target = Path(sys.argv[1]) if len(sys.argv) > 1 else DEFAULT_PATH

    if not target.exists():
        print(f"Erro: arquivo não encontrado: {target}")
        print("Passe o caminho manualmente: python fix_osewidgetview_imports.py /caminho/OseWidgetView.kt")
        sys.exit(1)

    text = target.read_text(encoding="utf-8")

    if "import com.xaulinxs.customizations.qsb.XaulinXsQsbPermissionCallback" in text:
        print("Já corrigido: os imports já existem em", target)
        return

    if ANCHOR_IMPORT not in text:
        print("Erro: não encontrei o import âncora esperado no arquivo.")
        print("O arquivo pode ter mudado de estrutura — corrija manualmente adicionando:")
        print(NEW_IMPORTS.splitlines()[1])
        print(NEW_IMPORTS.splitlines()[2])
        sys.exit(1)

    text = text.replace(ANCHOR_IMPORT, NEW_IMPORTS, 1)
    target.write_text(text, encoding="utf-8")
    print(f"Corrigido: imports adicionados em {target}")


if __name__ == "__main__":
    main()
