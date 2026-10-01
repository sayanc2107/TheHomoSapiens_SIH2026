package com.thehomosapiens.isl;

import android.content.Context;
import android.os.Build;
import android.os.VibrationEffect;
import android.os.Vibrator;
import android.speech.tts.TextToSpeech;
import android.webkit.JavascriptInterface;
import android.widget.Toast;
import java.util.Locale;

public class WebAppInterface {
    private final Context mContext;
    private TextToSpeech tts;

    public WebAppInterface(Context context) {
        this.mContext = context;
        tts = new TextToSpeech(context, status -> {
            if (status == TextToSpeech.SUCCESS) {
                tts.setLanguage(Locale.US);
            }
        });
    }

    @JavascriptInterface
    public void showToast(String toast) {
        Toast.makeText(mContext, toast, Toast.LENGTH_SHORT).show();
    }

    @JavascriptInterface
    public void speak(String text) {
        if (tts != null && text != null && !text.isEmpty()) {
            tts.speak(text, TextToSpeech.QUEUE_FLUSH, null, "ISL_TTS");
        }
    }

    @JavascriptInterface
    public void vibrate(long milliseconds) {
        Vibrator v = (Vibrator) mContext.getSystemService(Context.VIBRATOR_SERVICE);
        if (v != null && v.hasVibrator()) {
            if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O) {
                v.vibrate(VibrationEffect.createOneShot(milliseconds, VibrationEffect.DEFAULT_AMPLITUDE));
            } else {
                v.vibrate(milliseconds);
            }
        }
    }

    @JavascriptInterface
    public String getPlatform() {
        return "Android_Native";
    }
}
