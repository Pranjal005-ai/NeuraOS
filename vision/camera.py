"""
=========================================================
camera.py

Central Camera Manager for Project Ved

Author: Pranjal

Design notes
------------
1. BACKENDS. Pi OS Bookworm drives the CSI Camera Module
   through libcamera, which OpenCV's V4L2 backend cannot
   see. So: Picamera2 on the Pi, OpenCV on the Mac.

2. LAZY. The camera is NOT opened at import.

3. ONE READER. A single background thread captures;
   consumers get a copy of the latest frame.

4. LOW LIGHT. Two separate levers, often confused:

   EXPOSURE (set_low_light) changes what the SENSOR
   captures -- longer shutter, higher gain, lower frame
   rate. This adds real information. It is the one that
   actually matters.

   ENHANCEMENT (enhance_low_light) redistributes what was
   already captured. It cannot invent detail that was
   never recorded, but it does recover faces from
   underexposed frames that the detector would otherwise
   walk straight past.

   Use both. Exposure first.
=========================================================
"""

import threading
import time

import cv2
import numpy as np


####################################################
# Backend detection
####################################################

def _picamera2_available():

    try:
        from picamera2 import Picamera2  # noqa: F401
        return True
    except Exception:
        return False


####################################################
# Low-light image processing
####################################################

def frame_brightness(frame):
    """
    Mean luminance, 0-255. Cheap enough to run per frame.
    """

    if frame is None:
        return 0.0

    if frame.ndim == 3:
        # Rough luma without a full colour convert.
        return float(frame[:, :, 1].mean())

    return float(frame.mean())


def _gamma_table(gamma):

    inv = 1.0 / max(0.01, gamma)

    return np.array(
        [((i / 255.0) ** inv) * 255 for i in range(256)]
    ).astype(np.uint8)


_GAMMA_CACHE = {}


def apply_gamma(frame, gamma=1.5):

    key = round(gamma, 2)

    if key not in _GAMMA_CACHE:
        _GAMMA_CACHE[key] = _gamma_table(key)

    return cv2.LUT(frame, _GAMMA_CACHE[key])


def enhance_low_light(frame, gamma=1.6, clip=2.5):
    """
    CLAHE on luminance + gamma lift.

    Works in LAB so only brightness is touched -- boosting
    RGB channels directly shifts colour, and skin tone
    shifts hurt the embedding.
    """

    if frame is None:
        return None

    lab = cv2.cvtColor(frame, cv2.COLOR_BGR2LAB)

    l, a, b = cv2.split(lab)

    clahe = cv2.createCLAHE(
        clipLimit=clip,
        tileGridSize=(8, 8)
    )

    l = clahe.apply(l)

    merged = cv2.merge((l, a, b))

    out = cv2.cvtColor(merged, cv2.COLOR_LAB2BGR)

    return apply_gamma(out, gamma)


def denoise(frame, strength=5):
    """
    Optional. High-gain frames are noisy, and the
    detector sometimes latches onto noise texture.

    SLOW -- roughly 100ms on a Pi 5. Use for enrollment
    stills, not for the live loop.
    """

    return cv2.fastNlMeansDenoisingColored(
        frame, None, strength, strength, 7, 21
    )


####################################################
# Backends
####################################################

class _OpenCVBackend:
    """USB / built-in webcam. Mac dev machine."""

    name = "opencv"

    def __init__(self, index=0, width=640, height=480):

        self.capture = cv2.VideoCapture(index)

        if not self.capture.isOpened():
            raise RuntimeError(
                f"OpenCV could not open camera index {index}"
            )

        self.capture.set(cv2.CAP_PROP_FRAME_WIDTH, width)
        self.capture.set(cv2.CAP_PROP_FRAME_HEIGHT, height)

        try:
            self.capture.set(cv2.CAP_PROP_BUFFERSIZE, 1)
        except Exception:
            pass

    def read(self):

        ok, frame = self.capture.read()

        return frame if ok else None

    def set_low_light(self, enabled=True, fps=15):
        """
        Ask the driver for a longer exposure.

        HONEST WARNING: on macOS the AVFoundation backend
        ignores most of these. Apple does not expose
        manual exposure through OpenCV. Expect this to be
        a no-op on your MacBook and to actually work on
        the Pi with a USB camera, or via Picamera2 on the
        CSI module.
        """

        try:
            if enabled:
                # 0.25 = manual on most V4L2 drivers,
                # 0.75 = auto. Magic numbers, sadly.
                self.capture.set(cv2.CAP_PROP_AUTO_EXPOSURE, 0.25)
                self.capture.set(cv2.CAP_PROP_EXPOSURE, -4)
                self.capture.set(cv2.CAP_PROP_GAIN, 255)
                self.capture.set(cv2.CAP_PROP_FPS, fps)
            else:
                self.capture.set(cv2.CAP_PROP_AUTO_EXPOSURE, 0.75)
                self.capture.set(cv2.CAP_PROP_FPS, 30)

            return True

        except Exception as exc:
            print(f"[CAMERA] Exposure control failed: {exc}")
            return False

    def release(self):

        self.capture.release()


class _Picamera2Backend:
    """CSI Camera Module 3 on the Pi 5."""

    name = "picamera2"

    def __init__(self, index=0, width=640, height=480):

        from picamera2 import Picamera2

        self.picam = Picamera2(camera_num=index)

        config = self.picam.create_video_configuration(
            main={
                "size": (width, height),
                "format": "RGB888"
            }
        )

        self.picam.configure(config)
        self.picam.start()

        time.sleep(0.4)

    def read(self):

        frame = self.picam.capture_array()

        if frame is None:
            return None

        return cv2.cvtColor(frame, cv2.COLOR_RGB2BGR)

    def set_low_light(self, enabled=True, fps=15):
        """
        This one genuinely works.

        Dropping to 15fps doubles the time available per
        frame, which is where the extra light comes from.
        AnalogueGain amplifies the sensor signal -- and
        the noise with it, but a noisy face beats no face.
        """

        try:
            if enabled:

                frame_us = int(1_000_000 / max(1, fps))

                self.picam.set_controls(
                    {
                        "AeEnable": True,
                        "AeExposureMode": 1,      # long
                        "FrameDurationLimits": (
                            frame_us, frame_us
                        ),
                        "AnalogueGain": 8.0,
                        "Brightness": 0.1,
                    }
                )
            else:
                self.picam.set_controls(
                    {
                        "AeEnable": True,
                        "AeExposureMode": 0,
                        "FrameDurationLimits": (33333, 33333),
                        "AnalogueGain": 1.0,
                        "Brightness": 0.0,
                    }
                )

            return True

        except Exception as exc:
            print(f"[CAMERA] Exposure control failed: {exc}")
            return False

    def release(self):

        try:
            self.picam.stop()
            self.picam.close()
        except Exception:
            pass


####################################################
# Camera
####################################################

class Camera:

    def __init__(
        self,
        index=0,
        width=640,
        height=480,
        backend=None
    ):

        self.width = width
        self.height = height

        if backend is None:
            backend = (
                "picamera2" if _picamera2_available() else "opencv"
            )

        if backend == "picamera2":
            self.backend = _Picamera2Backend(index, width, height)
        else:
            self.backend = _OpenCVBackend(index, width, height)

        self._frame = None
        self._frame_id = 0
        self._lock = threading.Lock()

        self._running = True
        self._fps = 0.0

        self.low_light = False

        self._thread = threading.Thread(
            target=self._capture_loop,
            daemon=True
        )

        self._thread.start()

    ################################################

    def _capture_loop(self):

        misses = 0
        last = time.time()

        while self._running:

            frame = self.backend.read()

            if frame is None:

                misses += 1

                time.sleep(0.5 if misses > 30 else 0.01)

                continue

            misses = 0

            with self._lock:
                self._frame = frame
                self._frame_id += 1

            now = time.time()
            dt = now - last
            last = now

            if dt > 0:
                self._fps = 0.9 * self._fps + 0.1 * (1.0 / dt)

    ################################################

    def set_low_light(self, enabled=True, fps=15):
        """
        Longer exposure, more gain, lower frame rate.
        """

        self.low_light = enabled

        ok = self.backend.set_low_light(enabled, fps)

        if ok:
            print(
                f"[CAMERA] Low-light mode "
                f"{'ON' if enabled else 'OFF'} "
                f"({self.backend.name})"
            )

        return ok

    ################################################

    def get_frame(self, copy=True, enhance=False):
        """
        Latest captured frame, or None.

        enhance=True applies low-light processing. Off by
        default -- the recognition path decides for itself
        based on measured brightness.
        """

        with self._lock:

            if self._frame is None:
                return None

            frame = self._frame.copy() if copy else self._frame

        if enhance:
            return enhance_low_light(frame)

        return frame

    ################################################

    def get_rgb_frame(self):

        frame = self.get_frame()

        if frame is None:
            return None

        return cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)

    ################################################

    def brightness(self):
        """Mean luminance of the current frame, 0-255."""

        return frame_brightness(self.get_frame(copy=False))

    ################################################

    def frame_id(self):

        with self._lock:
            return self._frame_id

    ################################################

    def wait_for_frame(self, timeout=5.0):

        deadline = time.time() + timeout

        while time.time() < deadline:

            frame = self.get_frame()

            if frame is not None:
                return frame

            time.sleep(0.02)

        return None

    ################################################

    def fps(self):

        return round(self._fps, 1)

    ################################################

    def is_open(self):

        return self._running and self._thread.is_alive()

    ################################################

    def release(self):

        self._running = False

        if self._thread.is_alive():
            self._thread.join(timeout=1.0)

        self.backend.release()


####################################################
# Lazy singleton
####################################################

_camera = None
_camera_lock = threading.Lock()


def get_camera(index=0, width=640, height=480, backend=None):

    global _camera

    with _camera_lock:

        if _camera is None or not _camera.is_open():

            _camera = Camera(
                index=index,
                width=width,
                height=height,
                backend=backend
            )

    return _camera


def get_frame():

    return get_camera().get_frame()


def get_rgb_frame():

    return get_camera().get_rgb_frame()


def release_camera():

    global _camera

    with _camera_lock:

        if _camera is not None:
            _camera.release()
            _camera = None


####################################################
# Utility
####################################################

def resize(frame, width=640, height=480):

    if frame is None:
        return None

    return cv2.resize(frame, (width, height))


####################################################

if __name__ == "__main__":

    cam = get_camera()

    print(f"Backend : {cam.backend.name}")

    frame = cam.wait_for_frame()

    if frame is None:
        print("No frame received.")
    else:
        # Let the FPS average settle before reporting.
        time.sleep(2.0)

        print(f"Frame      : {frame.shape}")
        print(f"FPS        : {cam.fps()}")
        print(f"Brightness : {cam.brightness():.1f} / 255")

        if cam.brightness() < 60:
            print("\n  Frame is dark. Trying low-light mode...")

            cam.set_low_light(True)
            time.sleep(2.0)

            print(f"  Brightness : {cam.brightness():.1f} / 255")
            print(f"  FPS        : {cam.fps()}")

    release_camera()