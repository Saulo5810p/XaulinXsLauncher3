#!/usr/bin/env python3
"""
fix_build_errors_strings.py

Corrige os 2 erros de build reportados em mergeNoQuickstepDebugResources:

1) strings.xml:59 (app_name) — "Invalid unicode escape sequence in string"
   Causa real: apóstrofo não escapado dentro de "R's Home3". Em recursos
   Android, um apóstrofo dentro de uma string entre aspas duplas ainda
   precisa ser escapado (\') ou o aapt2 falha ao interpretar a sequência
   de escape ao redor dele. Corrige TODOS os arquivos do projeto que têm
   "R's Home3" (strings.xml em ~14 idiomas + launcher_preferences.xml +
   launcher.xml), não só o valores/strings.xml original do erro.

2) xaulinxs_strings.xml — "Multiple substitutions specified in
   non-positional format" em 3 strings (xaulinxs_allapps_transparency_
   percent_summary, xaulinxs_folder_size_summary,
   xaulinxs_folder_transparency_summary). Causa real: essas strings têm
   múltiplos "%" literais (ex.: "0% ... 100%") que o aapt2 interpreta
   como possíveis format specifiers. Como não são de fato %1$s/%2$s
   (são só sinal de porcentagem em texto), a correção é adicionar
   formatted="false" na tag <string>, exatamente como a própria mensagem
   de erro do Gradle sugere.

Idempotente: pode rodar várias vezes sem duplicar nem quebrar nada já
corrigido. Roda no Termux, na raiz do projeto (Launcher3/).
"""
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent

# ---------------------------------------------------------------------
# FIX 1: apóstrofo não escapado em "R's Home3"
# ---------------------------------------------------------------------
# Só troca a ocorrência exata "R's Home3" -> "R\'s Home3", em qualquer
# arquivo .xml do projeto. Não mexe em nenhuma outra ocorrência de "'s"
# no projeto (bem restrito ao literal do nome do app), pra não arriscar
# escapar duas vezes nem tocar em outra string por engano.
BROKEN = "R's Home3"
FIXED = "R\\'s Home3"

def fix_apostrophe(path: Path) -> bool:
    text = path.read_text(encoding="utf-8")
    if FIXED in text:
        # já corrigido nesse arquivo — nada a fazer (idempotência)
        if BROKEN not in text:
            return False
    if BROKEN not in text:
        return False
    new_text = text.replace(BROKEN, FIXED)
    path.write_text(new_text, encoding="utf-8")
    return True

# ---------------------------------------------------------------------
# FIX 2: formatted="false" nas 3 strings com múltiplos "%" literais
# ---------------------------------------------------------------------
TARGET_STRING_NAMES = [
    "xaulinxs_allapps_transparency_percent_summary",
    "xaulinxs_folder_size_summary",
    "xaulinxs_folder_transparency_summary",
]

# Casa <string name="NOME" ...atributos-existentes...>conteudo</string>
# sem exigir que "name" seja o primeiro atributo, e sem duplicar
# formatted="false" se já estiver presente (idempotência).
STRING_TAG_RE_TEMPLATE = r'<string([^>]*\bname="{name}"[^>]*)>'

def fix_formatted_false(path: Path) -> int:
    text = path.read_text(encoding="utf-8")
    changed = 0

    def make_repl():
        def repl(match: "re.Match[str]") -> str:
            nonlocal changed
            attrs = match.group(1)
            if "formatted=" in attrs:
                # já tem o atributo (true ou false) — não mexe, evita duplicar
                return match.group(0)
            changed += 1
            return f"<string{attrs} formatted=\"false\">"
        return repl

    for name in TARGET_STRING_NAMES:
        pattern = STRING_TAG_RE_TEMPLATE.format(name=re.escape(name))
        text, n = re.subn(pattern, make_repl(), text)
        changed += 0  # contagem real já feita dentro de repl via nonlocal

    if changed:
        path.write_text(text, encoding="utf-8")
    return changed

def main():
    xml_files = list(ROOT.rglob("*.xml"))
    # ignora diretórios de build/saída, se existirem soltos por aí
    xml_files = [
        p for p in xml_files
        if "/build/" not in str(p) and "/.git/" not in str(p)
    ]

    apostrophe_fixed = []
    for p in xml_files:
        try:
            if fix_apostrophe(p):
                apostrophe_fixed.append(p)
        except UnicodeDecodeError:
            continue

    formatted_fixed = []
    strings_file = ROOT / "res" / "values" / "xaulinxs_strings.xml"
    if strings_file.exists():
        n = fix_formatted_false(strings_file)
        if n:
            formatted_fixed.append((strings_file, n))
    else:
        print(f"AVISO: não encontrei {strings_file} — pulei o fix 2. "
              f"Rode este script na raiz do projeto (onde fica a pasta res/).")

    print("=== Fix 1: apóstrofo não escapado em 'R's Home3' ===")
    if apostrophe_fixed:
        for p in apostrophe_fixed:
            print(f"  corrigido: {p.relative_to(ROOT)}")
    else:
        print("  nada a corrigir (já estava OK ou não encontrado)")

    print()
    print("=== Fix 2: formatted=\"false\" em xaulinxs_strings.xml ===")
    if formatted_fixed:
        for p, n in formatted_fixed:
            print(f"  corrigido: {p.relative_to(ROOT)} ({n} string(s))")
    else:
        print("  nada a corrigir (já estava OK ou arquivo não encontrado)")

    print()
    print("Pronto. Rode de novo o build:")
    print("  ./gradlew assembleNoQuickstepDebug")

if __name__ == "__main__":
    main()
