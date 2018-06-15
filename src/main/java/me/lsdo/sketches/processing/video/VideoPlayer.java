package me.lsdo.sketches.processing.video;

import processing.core.*;
import processing.video.*;
import me.lsdo.Driver;
import me.lsdo.processing.*;
import me.lsdo.processing.interactivity.*;
import me.lsdo.processing.util.*;
import java.util.Arrays;

// Play video from a file.

// Keyboard controls:
// p: play/plause
// .: ff 5 sec
// ,: rewind 5 sec
// Also controllable from web UI.

// TODO support contrast stretch?

public class VideoPlayer extends VideoBase {

    //final String DEMO_VIDEO = "res/mov/bm2014_mushroom_cloud.mp4";
    final String DEMO_VIDEO = "res/mov/trexes_thunderdome.mp4";
    
    static final double[] skips = {5, 60};

    Movie mov;
    boolean repeat;
    BooleanParameter playing;
    BooleanParameter[] skipActions;
    NumericParameter timeline;
    BooleanParameter mute;
    boolean updateFreezeFrame = false;
    
    public void loadMedia() {
	String path = Config.getSketchProperty("path", DEMO_VIDEO);
	if (path.isEmpty()) {
	    throw new RuntimeException("must specify video path in sketch.properties!");
	}
	repeat = Config.getSketchProperty("repeat", true);
	double startAt = Config.getSketchProperty("skip", 0.);
	
        mov = new Movie(this, path);
	// begin playback so we have access to duration
	mov.play();

	mute = new BooleanParameter("mute", "hidden") {
		@Override
		public void onTrue() {
		    mov.volume(0);
		}

		@Override
		public void onFalse() {
		    mov.volume(1);
		}
	    };
	mute.init(Config.getSketchProperty("mute", false));
	
	playing = new BooleanParameter("playing", "animation") {
		@Override
		public void onTrue() {
		    mov.play();
		    updateFreezeFrame = false;
		    updateRemainingTime();
		}

		@Override
		public void onFalse() {
		    mov.pause();
		    updateRemainingTime();
		}
	    };
	playing.trueCaption = "play";
	playing.falseCaption = "pause";

	skipActions = new BooleanParameter[2*skips.length];
	int i = 0;
	for (final double skip : skips) {
	    for (final boolean forward : new boolean[] {true, false}) {
		BooleanParameter skipAction = new BooleanParameter((forward ? "forward" : "back") + " " + skip + "s", "animation") {
			@Override
			public void onTrue() {
			    relJump((forward ? 1 : -1) * skip);
			}
		    };
		skipAction.affinity = BooleanParameter.Affinity.ACTION;
		skipAction.init(false);
		skipActions[i] = skipAction;
		i++;
	    }
	}

	timeline = new NumericParameter("timeline", "animation") {
		@Override
		public void onSet() {
		    jump(get());
		}
	    };
	timeline.min = 0;
	timeline.max = mov.duration();
	
	if (repeat) {
	    mov.loop();
	}
	playing.init(true);
	timeline.init(startAt);

        System.out.println("duration: " + mov.duration());
    }

    public PImage nextFrame() {
	if (mov.available()) {
	    mov.read();

	    if (updateFreezeFrame) {
		mov.pause();
		updateFreezeFrame = false;
	    }
	}
	return mov;
    }

    public void relJump(double t) {
	t += mov.time();
	if (repeat) {
	    t = MathUtil.fmod(t, mov.duration());
	} else {
            t = Math.max(0, Math.min(mov.duration(), t));
	}
	timeline.set(t);
    }
    
    public void jump(double t) {
	mov.jump((float)t);
	updateRemainingTime();
	
	if (!playing.get()) {
	    updateFreezeFrame = true;
	    mov.play();
	}
	
	System.out.println(String.format("%.2f / %.2f", t, mov.duration()));
    }

    public void updateRemainingTime() {
	if (!repeat) {
	    InputControl.DurationControlJson msg = new InputControl.DurationControlJson();
	    msg.duration = (playing.get() ? mov.duration() - mov.time() : -1);
	    canvas.ctrl.broadcast(msg);
	}
    }
    
    public void keyPressed() {
        if (this.key == '.') {
	    skipActions[0].trigger();
        } else if (this.key == ',') {
	    skipActions[1].trigger();
        } else if (this.key == 'p') {
	    playing.toggle();
        }
    }

}

/*
  class ContrastStretch implements OPC.FramePostprocessor {
        final double BENCHMARK_PCTILE = .95;

        // FIXME pixels outside the video projection area should be excluded
        public void postProcessFrame(int[] pixelBuffer) {
            int numPixels = pixelBuffer.length;
            float[] lums = new float[numPixels];
            for (int i = 0; i < numPixels; i++) {
                int pixel = pixelBuffer[i];
                lums[i] = app.brightness(pixel);
            }
            Arrays.sort(lums);

            float lowlum = lums[(int)((1-BENCHMARK_PCTILE) * numPixels)];
            float highlum = lums[(int)(BENCHMARK_PCTILE * numPixels)];

            for (int i = 0; i < numPixels; i++) {
                int pixel = pixelBuffer[i];
                float h = app.hue(pixel);
                float s = app.saturation(pixel);
                float l = app.brightness(pixel);
                l = 100f * (l - lowlum) / (highlum - lowlum);
                pixelBuffer[i] = app.color(h, s, l);
            }
        }
    }
    OPC.FramePostprocessor _contrastStretch = new ContrastStretch();

    public void postProcessFrame(int[] pixelBuffer) {
        OPC.FramePostprocessor proc = null;
        if (contrastStretch) {
            proc = _contrastStretch;
        }
        if (proc != null) {
            proc.postProcessFrame(pixelBuffer);
        }
    }
*/
