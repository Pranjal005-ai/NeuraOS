"""
=========================================================
face/face_controller.py

Bridge between Ved's logic and Ved's animated face.

Author: Pranjal

THE PROBLEM
-----------
The face renderer owns a pygame window, and pygame wants
the main thread. The greeter owns a camera loop. Neither
can host the other, so they have to be separate processes
-- which means they need a way to talk.

THE SOLUTION
------------
A UDP datagram to localhost. Chosen deliberately:

  - Fire and forget. If the face isn't running, send()
    does nothing and nobody blocks. The greeter must
    never stall because the display crashed.
  - No connection state to manage or reconnect.
  - Sub-millisecond on loopback.
  - Packet loss on loopback is effectively nil, and an
    occasional dropped expression is harmless anyway --
    the next one arrives 200ms later.

interfaces.py already looks for face.face_controller with
a set_expression() function, so wiring is automatic.

USAGE
-----
Logic side (greeter, behaviour engine):

    from face.face_controller import set_expression
    set_expression("happy")

Display side (face/main.py):

    from face.face_controller import ExpressionReceiver
    receiver = ExpressionReceiver()
    receiver.start()
    ...
    expression = receiver.poll()   # None if unchanged
=========================================================
"""

import json
import socket
import threading


HOST = "127.0.0.1"
PORT = 9911

VALID_EXPRESSIONS = {
    "idle", "happy", "listening", "thinking",
    "speaking", "surprised", "sad", "sleeping", "wink",
}


####################################################
# Sender
####################################################

class FaceLink:

    def __init__(self, host=HOST, port=PORT):

        self.address = (host, port)

        self.socket = socket.socket(
            socket.AF_INET,
            socket.SOCK_DGRAM
        )

        # Never block the caller, even if the OS buffer
        # is full. A stalled greeter is worse than a
        # missed expression.
        self.socket.setblocking(False)

        self.last_sent = None

    ####################################################

    def send(self, expression, **extra):

        if expression not in VALID_EXPRESSIONS:
            return False

        message = {"expression": expression}

        message.update(extra)

        try:
            self.socket.sendto(
                json.dumps(message).encode("utf-8"),
                self.address
            )

            self.last_sent = expression

            return True

        except Exception:
            # Face not running. Entirely fine.
            return False

    ####################################################

    def close(self):

        try:
            self.socket.close()
        except Exception:
            pass


####################################################
# Receiver -- used inside the face renderer
####################################################

class ExpressionReceiver:

    def __init__(self, host=HOST, port=PORT):

        self.address = (host, port)

        self.socket = None
        self.thread = None
        self.running = False

        self._lock = threading.Lock()

        self._pending = None
        self._extra = {}

    ####################################################

    def start(self):

        try:
            self.socket = socket.socket(
                socket.AF_INET,
                socket.SOCK_DGRAM
            )

            self.socket.bind(self.address)
            self.socket.settimeout(0.2)

        except Exception as exc:
            print(f"[FACE LINK] Could not bind {self.address}: {exc}")
            return False

        self.running = True

        self.thread = threading.Thread(
            target=self._loop,
            daemon=True
        )

        self.thread.start()

        print(f"[FACE LINK] Listening on {self.address[0]}:{self.address[1]}")

        return True

    ####################################################

    def _loop(self):

        while self.running:

            try:
                data, _ = self.socket.recvfrom(1024)

            except socket.timeout:
                continue

            except Exception:
                continue

            try:
                message = json.loads(data.decode("utf-8"))

            except Exception:
                continue

            expression = message.pop("expression", None)

            if expression not in VALID_EXPRESSIONS:
                continue

            with self._lock:
                self._pending = expression
                self._extra = message

    ####################################################

    def poll(self):
        """
        Latest expression, or None if nothing new.

        Returning None on no-change lets the render loop
        skip work rather than re-setting the same
        expression sixty times a second.
        """

        with self._lock:

            expression = self._pending
            self._pending = None

            return expression

    ####################################################

    def stop(self):

        self.running = False

        if self.thread and self.thread.is_alive():
            self.thread.join(timeout=0.5)

        if self.socket:
            try:
                self.socket.close()
            except Exception:
                pass


####################################################
# Module-level API
#
# interfaces.py finds set_expression() here, so the
# greeter needs no changes at all.
####################################################

_link = None


def get_link():

    global _link

    if _link is None:
        _link = FaceLink()

    return _link


def set_expression(name, **extra):

    return get_link().send(name, **extra)


####################################################
# Convenience wrappers
####################################################

def idle():
    return set_expression("idle")


def happy():
    return set_expression("happy")


def listening():
    return set_expression("listening")


def thinking():
    return set_expression("thinking")


def speaking():
    return set_expression("speaking")


def surprised():
    return set_expression("surprised")


def sad():
    return set_expression("sad")


def sleeping():
    return set_expression("sleeping")


def wink():
    return set_expression("wink")


####################################################

if __name__ == "__main__":

    import sys
    import time

    if len(sys.argv) > 1:

        # Send one expression and exit.
        name = sys.argv[1]

        if set_expression(name):
            print(f"Sent '{name}'")
        else:
            print(f"'{name}' is not a valid expression")
            print(f"Valid: {', '.join(sorted(VALID_EXPRESSIONS))}")

        sys.exit(0)

    # Cycle through everything, so you can watch the face
    # while this runs in another terminal.
    print("Cycling expressions. Run face/main.py to watch.\n")

    for name in [
        "idle", "happy", "surprised", "thinking",
        "listening", "speaking", "wink", "sad", "sleeping",
        "idle",
    ]:
        print(f"  {name}")
        set_expression(name)
        time.sleep(1.5)