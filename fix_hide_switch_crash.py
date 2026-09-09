#!/usr/bin/env python3
"""
Fix de crash: NullPointerException no SwitchCompat (interruptor de "esconder
app") dentro do popup de long-press em ícones de app.

Causa raiz: androidx.appcompat.widget.SwitchCompat monta internamente um
StaticLayout com o texto "on"/"off" do trilho MESMO quando esse texto não é
exibido (showText=false, o padrão). Sem android:textOn/textOff definidos no
XML, getTextOn()/getTextOff() retornam null e o StaticLayout crasha ao medir
a View (SwitchCompat.makeLayout -> StaticLayout.<init>).

Rode este script na raiz do repo (pasta Launcher3/), com o Termux:
    python3 fix_hide_switch_crash.py

Idempotente: pode rodar mais de uma vez sem duplicar nada.
"""
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent

LAYOUT_FILE = REPO_ROOT / "res/layout/xaulinxs_app_popup_header.xml"

errors = []


def fix_switch_layout():
    if not LAYOUT_FILE.exists():
        errors.append(f"Não encontrei: {LAYOUT_FILE}")
        return

    text = LAYOUT_FILE.read_text(encoding="utf-8")

    if 'android:textOn=""' in text and 'android:textOff=""' in text:
        print(f"[skip] {LAYOUT_FILE.name} já está corrigido.")
        return

    old_block = (
        '        <androidx.appcompat.widget.SwitchCompat\n'
        '            android:id="@+id/xaulinxs_app_popup_hide_switch"\n'
        '            android:layout_width="wrap_content"\n'
        '            android:layout_height="wrap_content"\n'
        '            android:checked="false" />'
    )
    new_block = (
        '        <androidx.appcompat.widget.SwitchCompat\n'
        '            android:id="@+id/xaulinxs_app_popup_hide_switch"\n'
        '            android:layout_width="wrap_content"\n'
        '            android:layout_height="wrap_content"\n'
        '            android:checked="false"\n'
        '            android:textOn=""\n'
        '            android:textOff="" />'
    )

    if old_block not in text:
        errors.append(
            f"{LAYOUT_FILE.name}: não encontrei o bloco exato do SwitchCompat "
            "esperado (arquivo pode já ter sido editado manualmente de outra "
            "forma). Abortando para não sobrescrever edição existente."
        )
        return

    text = text.replace(old_block, new_block, 1)
    LAYOUT_FILE.write_text(text, encoding="utf-8")
    print(f"[ok] {LAYOUT_FILE.name} corrigido (textOn/textOff vazios no SwitchCompat).")


def main():
    fix_switch_layout()

    if errors:
        print("\nERROS:")
        for e in errors:
            print(f"  - {e}")
        sys.exit(1)

    print("\nTudo aplicado. Rode: ./gradlew assembleNoQuickstepDebug")


if __name__ == "__main__":
    main()
