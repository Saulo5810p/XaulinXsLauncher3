package com.android.systemui.plugins.annotations;

import java.lang.annotation.Retention;
import java.lang.annotation.RetentionPolicy;

/** Stub manual — anotação marcadora, sem uso em runtime aqui. */
@Retention(RetentionPolicy.SOURCE)
public @interface ProvidesInterface {
    String action() default "";
    int version() default 1;
}
