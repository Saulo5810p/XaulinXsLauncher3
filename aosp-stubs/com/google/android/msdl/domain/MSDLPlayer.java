package com.google.android.msdl.domain;

import android.os.Vibrator;

import com.google.android.msdl.data.model.MSDLToken;
import com.google.android.msdl.logging.MSDLEvent;

import java.util.Collections;
import java.util.List;
import java.util.concurrent.Executor;

/**
 * Stub manual — MSDLPlayer real ainda não existe fora da árvore interna do
 * Google. playToken() é no-op; getHistory() sempre volta vazio.
 */
public abstract class MSDLPlayer {
    public abstract void playToken(MSDLToken token, InteractionProperties properties);
    public abstract List<MSDLEvent> getHistory();

    public static final Companion Companion = new Companion();

    public static final class Companion {
        public MSDLPlayer createPlayer(
                Vibrator vibrator, Executor executor, Object useHapticFeedbackForToken) {
            return new MSDLPlayer() {
                @Override
                public void playToken(MSDLToken token, InteractionProperties properties) {}

                @Override
                public List<MSDLEvent> getHistory() {
                    return Collections.emptyList();
                }
            };
        }
    }
}
