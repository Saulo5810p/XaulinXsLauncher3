package com.android.launcher3;

import android.graphics.Path;

/**
 * Stub manual — classe própria do Launcher3 que está faltando nessa árvore
 * (não é do androidx.graphics.shapes). O algoritmo real estima o quão perto
 * um Path está de ser um retângulo arredondado; sempre retornando -1 aqui
 * desativa essa otimização e força o ShapeDelegate a usar sempre o path
 * genérico como fallback — funcionalmente seguro, só não é a forma
 * "perfeita" de ícone.
 */
public final class RoundRectEstimator {
    private RoundRectEstimator() {}

    public static float estimateRadius(Path path, float pathSize) {
        return -1f;
    }
}
