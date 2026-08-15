#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
XaulinXs Customizations — Fix 8 (item 1 da PROXIMA_FASE_BLUR_DOCK_QSB.md):
suavizar a cascata giratória de entrada (AllApps e Widget Picker).

Problema relatado pelo usuário: a cascata de giro 720° estava rápida e
"seca" demais (comparável à animation scale 0.2x do Android). Pedido:
bem mais lenta e suave, no nível mais extremo testado nesta sessão.

Valores ANTIGOS -> NOVOS (idênticos nos dois arquivos, View System e
Compose, para manter a mesma sensação em ambas as superfícies):
  - stiffness:      SpringForce.STIFFNESS_LOW (200f) -> 15f (customizado,
                     não existe constante nomeada mais lenta que
                     STIFFNESS_LOW no androidx.dynamicanimation nem no
                     Spring do Compose — confirmado antes de editar)
  - dampingRatio:    0.55f -> 0.78f (overshoot bem mais contido, sem
                     oscilar feito elástico seco)
  - STAGGER_DELAY_MS: 18L -> 110L (a cascata varre o grid bem mais devagar,
                     não só cada ícone individual girando mais devagar)

Arquivos alterados:
  - src/com/xaulinxs/customizations/cinematic/AllAppsIconEnterEffect.kt
    (View System, SpringAnimation/SpringForce)
  - src/com/xaulinxs/customizations/cinematic/CinematicWidgetSheetEffects.kt
    (Compose, spring())

Nenhum hook novo, nenhum arquivo novo — só troca de constantes já
existentes. Idempotente: se os valores novos já estão presentes, o script
detecta e não faz nada; se os valores antigos não forem encontrados (por
já terem sido trocados por outro valor manualmente), avisa e não
sobrescreve às cegas.

Uso:
    python3 fix_cinematic_8_smoother_cascade.py /caminho/do/repo
    (ou rode de dentro da raiz do repo sem argumento)
"""

import os
import sys

VIEW_FILE = "src/com/xaulinxs/customizations/cinematic/AllAppsIconEnterEffect.kt"
COMPOSE_FILE = "src/com/xaulinxs/customizations/cinematic/CinematicWidgetSheetEffects.kt"

# (arquivo, texto_antigo, texto_novo, descricao)
EDITS = [
    (
        VIEW_FILE,
        "                    stiffness = SpringForce.STIFFNESS_LOW\n"
        "                    dampingRatio = 0.55f // <1 = permite overshoot visível",
        "                    stiffness = 15f // customizado — mais mole que STIFFNESS_LOW (200f)\n"
        "                    dampingRatio = 0.78f // overshoot bem mais contido/suave",
        "AllAppsIconEnterEffect: spring stiffness/dampingRatio",
    ),
    (
        VIEW_FILE,
        "    private const val STAGGER_DELAY_MS = 18L",
        "    private const val STAGGER_DELAY_MS = 110L // suavizado (era 18L) — cascata varre bem mais devagar",
        "AllAppsIconEnterEffect: STAGGER_DELAY_MS",
    ),
    (
        COMPOSE_FILE,
        "                        spring(\n"
        "                            dampingRatio = 0.55f,\n"
        "                            stiffness = Spring.StiffnessLow,\n"
        "                        ),",
        "                        spring(\n"
        "                            dampingRatio = 0.78f, // overshoot bem mais contido/suave (era 0.55f)\n"
        "                            stiffness = 15f, // mais mole que Spring.StiffnessLow (era 200f)\n"
        "                        ),",
        "CinematicWidgetSheetEffects: spring dampingRatio/stiffness",
    ),
    (
        COMPOSE_FILE,
        "private const val STAGGER_DELAY_MS = 18L",
        "private const val STAGGER_DELAY_MS = 110L // suavizado (era 18L) — cascata varre bem mais devagar",
        "CinematicWidgetSheetEffects: STAGGER_DELAY_MS",
    ),
]


def main():
    repo_root = sys.argv[1] if len(sys.argv) > 1 else "."
    repo_root = os.path.abspath(repo_root)

    applied = 0
    skipped_already_done = 0
    warnings = []

    for rel_path, old, new, desc in EDITS:
        full_path = os.path.join(repo_root, rel_path)
        if not os.path.isfile(full_path):
            warnings.append(f"[ERRO] Arquivo não encontrado: {rel_path}")
            continue

        with open(full_path, "r", encoding="utf-8") as f:
            content = f.read()

        if new in content:
            print(f"[SKIP] Já aplicado: {desc}")
            skipped_already_done += 1
            continue

        if old not in content:
            warnings.append(
                f"[AVISO] Padrão antigo não encontrado para '{desc}' em "
                f"{rel_path} — pode já ter sido alterado manualmente. "
                f"Nada foi sobrescrito às cegas."
            )
            continue

        if content.count(old) > 1:
            warnings.append(
                f"[AVISO] Padrão de '{desc}' aparece mais de uma vez em "
                f"{rel_path} — edição pulada por segurança (evitar ambiguidade)."
            )
            continue

        content = content.replace(old, new)
        with open(full_path, "w", encoding="utf-8") as f:
            f.write(content)
        print(f"[OK] Aplicado: {desc}")
        applied += 1

    print()
    print(f"Resumo: {applied} edição(ões) aplicada(s), "
          f"{skipped_already_done} já estava(m) aplicada(s).")
    if warnings:
        print("\nAvisos:")
        for w in warnings:
            print(f"  {w}")
        if applied == 0 and skipped_already_done == 0:
            sys.exit(1)


if __name__ == "__main__":
    main()
