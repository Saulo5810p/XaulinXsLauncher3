#!/usr/bin/env python3
"""
Fix: ClassCastException (android.widget.Switch -> androidx.appcompat.widget.SwitchCompat)
ao dar long-press num ícone de app (crash no PopupContainerWithArrow$Companion.bindXaulinXsAppPopupHeader).

Causa raiz:
  O layout xaulinxs_app_popup_header.xml declara o interruptor "esconder app" como
  <Switch> (android.widget.Switch, widget nativo), mas o Kotlin tentava ler essa
  view com findViewById<androidx.appcompat.widget.SwitchCompat>(...), forçando
  um cast pra um tipo incompatível com o que foi de fato inflado.

  SwitchStyle (res/values/styles.xml) estende android:style/Widget.Material.
  CompoundButton.Switch, que é exclusivo do Switch nativo -- não pode ser
  aplicado a um SwitchCompat. Por isso o fix é no lado Kotlin (ler como
  android.widget.Switch), não no XML.

Uso:
    python3 fix_switch_classcast_crash.py [caminho_do_repo]

Se caminho_do_repo não for passado, usa o diretório atual.
Idempotente: pode rodar várias vezes sem duplicar nem quebrar nada.
"""
import sys
from pathlib import Path

OLD_BLOCK = """            val hideSwitch =
                header.findViewById<androidx.appcompat.widget.SwitchCompat>(
                    R.id.xaulinxs_app_popup_hide_switch
                )"""

NEW_BLOCK = """            val hideSwitch =
                header.findViewById<android.widget.Switch>(
                    R.id.xaulinxs_app_popup_hide_switch
                )"""


def main():
    repo_root = Path(sys.argv[1]) if len(sys.argv) > 1 else Path(".")
    target = repo_root / "src" / "com" / "android" / "launcher3" / "popup" / "PopupContainerWithArrow.kt"

    if not target.exists():
        print(f"ERRO: arquivo não encontrado em {target}")
        print("Rode este script a partir da raiz do repo, ou passe o caminho como argumento.")
        sys.exit(1)

    content = target.read_text(encoding="utf-8")

    if NEW_BLOCK in content:
        print(f"OK (já aplicado, nada a fazer): {target}")
        sys.exit(0)

    if OLD_BLOCK not in content:
        print(f"ERRO: não encontrei o trecho esperado em {target}.")
        print("O arquivo pode já ter sido editado de outra forma. Nada foi alterado.")
        sys.exit(1)

    content = content.replace(OLD_BLOCK, NEW_BLOCK)
    target.write_text(content, encoding="utf-8")
    print(f"Aplicado com sucesso: {target}")
    print("Fix: hideSwitch agora é lido como android.widget.Switch (bate com o <Switch> do XML).")
    sys.exit(0)


if __name__ == "__main__":
    main()
