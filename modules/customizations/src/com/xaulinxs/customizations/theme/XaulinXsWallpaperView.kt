/*
 * XaulinXs Customizations — não faz parte do AOSP original.
 *
 * Desenha o wallpaper PRÓPRIO do R's Home3 (ver XaulinXsInAppWallpaper)
 * como plano de fundo da tela inicial. É colocada como o primeiro filho
 * do DragLayer em res/layout/launcher.xml — ou seja, o mais no fundo
 * possível, atrás até do Workspace — então ela ocupa visualmente o lugar
 * onde o wallpaper real do sistema apareceria, mesmo sem mudar nenhuma
 * flag de transparência de janela.
 *
 * Escala em center-crop (preenche a View inteira, cortando o excesso,
 * sem distorcer) — o mesmo comportamento visual de um wallpaper normal.
 *
 * FIX (borda faltando mostrando o wallpaper real do sistema): antes,
 * quando getCurrentWallpaper() retornava null (ex.: no 1º frame, antes
 * do arquivo default terminar de ser copiado em background, ou se o
 * decode falhasse), onDraw simplesmente não desenhava nada — a View
 * ficava com um retângulo/borda transparente vazando o wallpaper real
 * do sistema por trás. Agora, sempre que não há bitmap pronto, a View
 * pinta uma cor de fallback sólida e opaca (nunca fica transparente por
 * acidente).
 *
 * NOVO: interruptor "usar wallpaper do app" (XaulinXsInAppWallpaperSetting).
 * Quando desligado, esse é um caso DELIBERADO de não desenhar nada — a
 * View deixa o wallpaper real do sistema aparecer por trás de propósito,
 * ao contrário do bug acima (que era um null não intencional).
 */
package com.xaulinxs.customizations.theme

import android.content.Context
import android.graphics.Canvas
import android.graphics.Color
import android.graphics.Matrix
import android.graphics.Paint
import android.graphics.RenderEffect
import android.graphics.Shader
import android.os.Build
import android.util.AttributeSet
import android.view.View
import com.android.launcher3.LauncherPrefs
import com.xaulinxs.customizations.blur.XaulinXsPopupBlur
import com.xaulinxs.customizations.settings.ThemedScrimPreference.Companion.THEMED_SCRIM_ENABLED

class XaulinXsWallpaperView @JvmOverloads constructor(
    context: Context,
    attrs: AttributeSet? = null,
) : View(context, attrs) {

    private val paint = Paint(Paint.ANTI_ALIAS_FLAG or Paint.FILTER_BITMAP_FLAG)
    private val matrix = Matrix()
    private val onWallpaperChanged: () -> Unit = { post { invalidate() } }
    private val onBlurPrefChanged: () -> Unit =
        { post { applyBlurEffect(); preloadSystemWallpaperIfNeeded(); invalidate() } }
    private val onEnabledPrefChanged: () -> Unit =
        { post { applyBlurEffect(); preloadSystemWallpaperIfNeeded(); invalidate() } }

    // XAULINXS_BLUR_V3: pincel da cópia do wallpaper do sistema (alpha varia no fade-in).
    private val systemPaint = Paint(Paint.ANTI_ALIAS_FLAG or Paint.FILTER_BITMAP_FLAG)

    // XAULINXS_BLUR_V2: raio vindo do arrasto do app drawer (XaulinXsDepthController).
    // O raio final é o MAIOR entre o desfoque fixo da tela inicial e este.
    private var depthBlurRadiusPx = 0f

    override fun onAttachedToWindow() {
        super.onAttachedToWindow()
        XaulinXsInAppWallpaper.addOnChangedListener(onWallpaperChanged)
        XaulinXsWorkspaceBlur.addOnChangedListener(onBlurPrefChanged)
        XaulinXsInAppWallpaperSetting.addOnChangedListener(onEnabledPrefChanged)
        applyBlurEffect()
        preloadSystemWallpaperIfNeeded()
    }

    override fun onDetachedFromWindow() {
        super.onDetachedFromWindow()
        XaulinXsInAppWallpaper.removeOnChangedListener(onWallpaperChanged)
        XaulinXsWorkspaceBlur.removeOnChangedListener(onBlurPrefChanged)
        XaulinXsInAppWallpaperSetting.removeOnChangedListener(onEnabledPrefChanged)
    }

    /**
     * XaulinXs feature (info.txt/etapa 3: "Área de trabalho [...] -
     * desfoque"): usa View.setRenderEffect (RenderNode blur, API 31+),
     * que roda inteiramente dentro da NOSSA janela — diferente do blur
     * "de vidro fosco" das outras telas (balões/menu de apps/widgets),
     * que depende de cross-window blur do sistema e já está documentado
     * como bloqueado pelo ROM deste aparelho (ver XaulinXsDepthController).
     * Por desenharmos o próprio wallpaper agora (XaulinXsInAppWallpaper),
     * dá pra aplicar esse blur sem depender de nenhuma permissão ou
     * capability do sistema. Quando o interruptor do wallpaper do app
     * está desligado, não há nada nosso pra borrar — pula o blur.
     */
    private fun applyBlurEffect() {
        if (Build.VERSION.SDK_INT < Build.VERSION_CODES.S) return
        // XAULINXS_HOME_BLUR_SYSTEM_WALLPAPER: com o wallpaper do app desligado, tanto o desfoque
        // do drawer quanto o desfoque FIXO da tela inicial passam a valer — ambos aplicados à
        // cópia do wallpaper do sistema (ver drawSystemWallpaperSnapshot). Antes o desfoque da
        // tela inicial só valia para o wallpaper do app.
        val radiusPx = maxOf(XaulinXsWorkspaceBlur.getBlurRadiusPx(context), depthBlurRadiusPx)
        setRenderEffect(
            if (radiusPx > 0f)
                RenderEffect.createBlurEffect(radiusPx, radiusPx, Shader.TileMode.CLAMP)
            else null
        )
    }

    /** Chamado pelo XaulinXsDepthController a cada frame do arrasto do app drawer. */
    fun setDepthBlurRadiusPx(radiusPx: Float) {
        if (radiusPx == depthBlurRadiusPx) return
        depthBlurRadiusPx = radiusPx
        applyBlurEffect()
        if (!isInAppWallpaperEnabled()) {
            if (radiusPx > 0f) preloadSystemWallpaperIfNeeded()
            invalidate() // o fade-in da cópia depende do raio, então redesenha
        }
    }

    /** XAULINXS_BLUR_V3: carrega (em background) a cópia do wallpaper do sistema, se for preciso. */
    private fun preloadSystemWallpaperIfNeeded() {
        if (Build.VERSION.SDK_INT < Build.VERSION_CODES.S) return
        if (isInAppWallpaperEnabled()) return
        // XAULINXS_POPUPS_V4: a cópia também serve ao desfoque dos popups (balões), não só ao do drawer.
        val prefs = LauncherPrefs.get(context)
        // XAULINXS_HOME_BLUR_SYSTEM_WALLPAPER: o desfoque da tela inicial também precisa da cópia.
        if (!prefs.get(THEMED_SCRIM_ENABLED) &&
            !XaulinXsPopupBlur.isEnabled(context) &&
            XaulinXsWorkspaceBlur.getBlurRadiusPx(context) <= 0f
        ) return
        XaulinXsSystemWallpaperSnapshot.ensureLoaded(context) { invalidate() }
    }

    /**
     * XAULINXS_BLUR_V3: só enquanto o drawer está sendo aberto/arrastado desenha a cópia do wallpaper
     * do sistema (center-crop) por cima do wallpaper real, que passa a ser borrada pelo
     * RenderEffect desta view. Com o drawer fechado (raio 0) não desenha nada.
     */
    private fun drawSystemWallpaperSnapshot(canvas: Canvas) {
        // XAULINXS_HOME_BLUR_SYSTEM_WALLPAPER: raio efetivo = maior entre o desfoque fixo da tela
        // inicial e o do arrasto do drawer (mesma regra de applyBlurEffect).
        val workspaceRadius = XaulinXsWorkspaceBlur.getBlurRadiusPx(context)
        val radius = maxOf(workspaceRadius, depthBlurRadiusPx)
        if (radius < 1f) return
        val bitmap = XaulinXsSystemWallpaperSnapshot.peek() ?: return
        val viewW = width.toFloat()
        val viewH = height.toFloat()
        if (viewW <= 0f || viewH <= 0f) return
        val bmpW = bitmap.width.toFloat()
        val bmpH = bitmap.height.toFloat()
        val scale = maxOf(viewW / bmpW, viewH / bmpH)
        matrix.reset()
        matrix.setScale(scale, scale)
        matrix.postTranslate((viewW - bmpW * scale) / 2f, (viewH - bmpH * scale) / 2f)
        // Fade-in nos primeiros pixels de raio: esconde qualquer diferença de enquadramento
        // entre a cópia e o wallpaper real no instante em que a cópia aparece.
        // Desfoque fixo da tela inicial: cópia sempre opaca (não há transição a esconder). Só o
        // arrasto do drawer usa o fade-in por raio.
        systemPaint.alpha = if (workspaceRadius >= 1f) {
            255
        } else {
            (255f * (radius / SNAPSHOT_FADE_IN_PX).coerceIn(0f, 1f)).toInt()
        }
        canvas.drawBitmap(bitmap, matrix, systemPaint)
    }

    private fun isInAppWallpaperEnabled(): Boolean =
        LauncherPrefs.get(context).get(XaulinXsInAppWallpaperSetting.IN_APP_WALLPAPER_ENABLED)

    override fun onDraw(canvas: Canvas) {
        super.onDraw(canvas)

        if (!isInAppWallpaperEnabled()) {
            // Interruptor desligado: não pintar nada, de propósito — o wallpaper real do
            // sistema (por trás desta janela) aparece. Única exceção: durante o desfoque do
            // drawer, desenha a cópia borrada do wallpaper do sistema (XAULINXS_BLUR_V3).
            drawSystemWallpaperSnapshot(canvas)
            return
        }

        val viewW = width.toFloat()
        val viewH = height.toFloat()
        if (viewW <= 0f || viewH <= 0f) return

        val bitmap = XaulinXsInAppWallpaper.getCurrentWallpaper(context)
        if (bitmap == null) {
            // FIX: sem bitmap pronto ainda (1º frame / decode falhou) —
            // pinta um fundo sólido opaco em vez de deixar a View
            // transparente, pra nunca vazar o wallpaper real do sistema
            // atrás por acidente enquanto o interruptor estiver ligado.
            canvas.drawColor(FALLBACK_COLOR)
            return
        }

        val bmpW = bitmap.width.toFloat()
        val bmpH = bitmap.height.toFloat()
        // center-crop: escala pelo maior fator entre largura/altura, pra
        // preencher a View inteira, e centraliza o excesso cortado.
        val scale = maxOf(viewW / bmpW, viewH / bmpH)
        val scaledW = bmpW * scale
        val scaledH = bmpH * scale
        matrix.reset()
        matrix.setScale(scale, scale)
        matrix.postTranslate((viewW - scaledW) / 2f, (viewH - scaledH) / 2f)
        canvas.drawBitmap(bitmap, matrix, paint)
    }

    private companion object {
        const val FALLBACK_COLOR = Color.BLACK
        const val SNAPSHOT_FADE_IN_PX = 48f
    }
}
