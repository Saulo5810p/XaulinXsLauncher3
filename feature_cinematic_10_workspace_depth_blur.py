#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
XaulinXs Customizations — Feature 10/N (item 2 da PROXIMA_FASE_BLUR_DOCK_QSB.md):
scroll blur pesado no Workspace, reagindo à POSIÇÃO de scroll (quão no
meio do caminho entre páginas), somado visualmente ao blur de velocidade
já existente (feature 2).

Decisão confirmada com o usuário: os dois blurs ficam SEPARADOS, não
fundidos num raio único — CinematicScrollVelocityEffect (blur de
velocidade, raio máx. 60f, com aberração cromática/vinheta) continua
exatamente como está hoje, aplicado na PagedView inteira. Este é um
segundo blur, mais pesado (raio até 300f), aplicado direto em cada
CellLayout (página) — como é uma view FILHA dentro da PagedView, o
Android compõe as duas camadas de blur naturalmente, sem precisar de
nenhum código de composição manual. Efeito puro
(RenderEffect.createBlurEffect, TileMode.DECAL, sem AGSL/shader), sem
cap de otimização — reage a cada frame de scroll.

Fórmula: radius = abs(scrollProgress) * 300f, onde scrollProgress é o
retorno de getScrollProgress() nativo do PagedView (já usado por
Workspace.updatePageScrollValues() para o coverflow da feature 7).
Guarda isFinite() desde a primeira versão — mesma lição aprendida no
crash de NaN da feature 7 (fix_cinematic_7_nan_crash.py).

Arquivo novo:
  - src/com/xaulinxs/customizations/cinematic/WorkspaceDepthBlurEffect.kt

Hook: 1 linha em Workspace.updatePageScrollValues(), logo depois da
chamada já existente a CinematicCoverFlowEffect.applyToPage (mesmo
scrollProgress já calculado, sem recalcular nada). CinematicCoverFlowEffect
não usa setRenderEffect (só rotação/escala/alpha/cameraDistance) —
confirmado antes de escrever este script, sem conflito entre os dois
efeitos na mesma página.

Todas as edições são ADITIVAS: nenhuma lógica de scroll ou CellLayout é
alterada — só efeito visual observacional por cima. Script idempotente —
pode rodar várias vezes sem duplicar nada.

Uso:
    python3 feature_cinematic_10_workspace_depth_blur.py /caminho/do/repo
    (ou rode de dentro da raiz do repo sem argumento)
"""

import os
import sys

MARKER_HOOK = "// XAULINXS_CASCADE_HOOK_DEPTH_BLUR_WORKSPACE"
MARKER_NEW_FILE = "// XAULINXS_WORKSPACE_DEPTH_BLUR_FILE"

NEW_FILE_PATH = "src/com/xaulinxs/customizations/cinematic/WorkspaceDepthBlurEffect.kt"
WORKSPACE_REL_PATH = "src/com/android/launcher3/Workspace.java"

NEW_FILE_CONTENT = '''/*
 * XaulinXs Customizations — não faz parte do AOSP original.
 *
 * Blur pesado e progressivo por PÁGINA do Workspace, reagindo à posição
 * de scroll (quão no meio do caminho entre duas páginas ela está) — não
 * à velocidade do gesto. Diferente e mais pesado que
 * CinematicScrollVelocityEffect (feature 2, aplicado na PagedView inteira,
 * raio máximo 60f, reage a velocidade): este aplica direto em cada
 * CellLayout via RenderEffect.createBlurEffect puro, raio até 300f no
 * pico (meio do caminho entre páginas), TileMode.DECAL (borra e deixa
 * transparente fora dos limites da página, "vazando" a mancha de blur).
 *
 * Decisão confirmada com o usuário: os dois efeitos ficam SEPARADOS (não
 * fundidos num raio só) — o de velocidade continua exatamente como está
 * hoje na PagedView inteira (aberração cromática/vinheta incluídas,
 * perfeito reagindo ao arrasto). Este é um efeito adicional, empilhado
 * visualmente por estar numa view filha (CellLayout) dentro da PagedView
 * — native compositing do Android soma as duas camadas de blur sem
 * precisar de nenhum código de composição manual.
 *
 * setRenderEffect(null) quando a página está praticamente centralizada
 * (scrollProgress ~0), recuperando nitidez total — sem nenhuma trava de
 * "só atualiza se mudou", reage a cada frame de scroll conforme pedido.
 *
 * Guarda isFinite() desde a primeira versão (aprendizado da feature 7:
 * getScrollProgress() pode devolver NaN/Infinity antes do primeiro
 * layout medido — sem essa guarda o launcher crasha ao abrir).
 */
package com.xaulinxs.customizations.cinematic

import android.graphics.Shader
import android.os.Build
import android.view.View
import kotlin.math.abs

object WorkspaceDepthBlurEffect {

    // Raio máximo de blur no pico (scrollProgress = ±1, meio do caminho
    // entre duas páginas) — pedido explícito do usuário: "bruto", cobrindo
    // ícones e widgets por completo.
    private const val MAX_BLUR_RADIUS = 300f
    private const val MIN_BLUR_RADIUS = 0.5f // abaixo disso, remove o efeito (evita RenderEffect inútil)

    /**
     * Chamar para cada página (CellLayout) a cada recálculo de scroll —
     * mesmo ponto e mesmo scrollProgress já usados por
     * CinematicCoverFlowEffect.applyToPage em
     * Workspace.updatePageScrollValues().
     */
    @JvmStatic
    fun applyToPage(page: View, scrollProgress: Float) {
        if (Build.VERSION.SDK_INT < Build.VERSION_CODES.S) return

        // Mesma guarda que evitou o crash da feature 7: scrollProgress
        // pode vir NaN/Infinity antes do primeiro layout medido.
        if (!scrollProgress.isFinite()) {
            page.setRenderEffect(null)
            return
        }

        val absProgress = abs(scrollProgress).coerceIn(0f, 1.4f)
        val radius = absProgress * MAX_BLUR_RADIUS

        if (radius < MIN_BLUR_RADIUS) {
            page.setRenderEffect(null)
            return
        }

        val effect = android.graphics.RenderEffect.createBlurEffect(
            radius,
            radius,
            Shader.TileMode.DECAL
        )
        page.setRenderEffect(effect)
    }
}

''' + f"{MARKER_NEW_FILE}\n"


def find_repo_root(start):
    candidates = [start] + ([os.path.join(start, d) for d in os.listdir(start)] if os.path.isdir(start) else [])
    for c in candidates:
        if os.path.isfile(os.path.join(c, WORKSPACE_REL_PATH)):
            return c
    return None


def write_new_file(repo_root):
    path = os.path.join(repo_root, NEW_FILE_PATH)
    if os.path.exists(path):
        with open(path, "r", encoding="utf-8") as f:
            existing = f.read()
        if MARKER_NEW_FILE in existing:
            print(f"[=] {NEW_FILE_PATH} já existe e está atualizado — pulando.")
            return
        print(f"[~] {NEW_FILE_PATH} existe mas parece desatualizado — sobrescrevendo.")
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        f.write(NEW_FILE_CONTENT)
    print(f"[+] Criado {NEW_FILE_PATH}")


def patch_workspace(repo_root):
    path = os.path.join(repo_root, WORKSPACE_REL_PATH)
    if not os.path.isfile(path):
        print(f"[!] ERRO: {path} não encontrado. Estrutura do repo mudou? Abortando este hook.")
        return False
    with open(path, "r", encoding="utf-8") as f:
        content = f.read()

    if MARKER_HOOK in content:
        print("[=] Workspace.java já tem o hook do blur pesado por posição — pulando.")
        return True

    old_block = (
        "                float scrollProgress = getScrollProgress(screenCenter, child, i);\n"
        "                child.setScrollProgress(scrollProgress);\n"
        "                // XAULINXS_CASCADE_HOOK_COVERFLOW_WORKSPACE\n"
        "                CinematicCoverFlowEffect.applyToPage(child, scrollProgress);\n"
    )
    if old_block not in content:
        print("[!] ERRO: âncora do hook (bloco da feature 7, coverflow) não encontrada em "
              "Workspace.java — abortando. O arquivo pode ter mudado desde a última feature.")
        return False
    if content.count(old_block) > 1:
        print("[!] ERRO: âncora aparece mais de uma vez em Workspace.java — abortando por segurança.")
        return False

    new_block = old_block + (
        "                " + MARKER_HOOK + "\n"
        "                com.xaulinxs.customizations.cinematic.WorkspaceDepthBlurEffect\n"
        "                        .applyToPage(child, scrollProgress);\n"
    )
    content = content.replace(old_block, new_block, 1)

    with open(path, "w", encoding="utf-8") as f:
        f.write(content)
    print("[+] Hook do blur pesado por posição (Workspace) aplicado.")
    return True


def main():
    start = sys.argv[1] if len(sys.argv) > 1 else "."
    repo_root = find_repo_root(os.path.abspath(start))
    if repo_root is None:
        print(f"[!] ERRO: não encontrei {WORKSPACE_REL_PATH} a partir de '{start}'. "
              f"Rode este script de dentro da raiz do repo, ou passe o caminho como argumento.")
        sys.exit(1)

    print(f"Repo detectado em: {repo_root}\n")

    write_new_file(repo_root)
    ok = patch_workspace(repo_root)

    print()
    if ok:
        print("Concluído. Rode ./gradlew assembleDebug para compilar.")
    else:
        print("Concluído com erros — revise as mensagens [!] acima antes de compilar.")
        sys.exit(1)


if __name__ == "__main__":
    main()
