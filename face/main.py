"""
=========================================================
File: face/main.py
Author: Pranjal

Purpose:
Runs Ved's animated face display.

Run from INSIDE the face folder:
    cd face && python3 main.py

WHY THIS IS A SEPARATE PROCESS
------------------------------
There are two main.py files in this project and they are
not duplicates:

    NeuraOS/main.py       the robot -- vision, brain,
                          missions, navigation
    NeuraOS/face/main.py  this file -- the pygame window

They must be separate processes. Pygame requires the main
thread for its window and event loop; the robot loop also
requires the main thread. Neither can host the other.

So they talk over UDP on localhost (face_controller.py).
The robot sends "happy"; this process renders it. If the
robot isn't running, this still works with the number
keys. If this isn't running, the robot carries on with a
blind face. Neither can take the other down.

RUN BOTH:
    terminal 1:  cd face && python3 main.py
    terminal 2:  python3 main.py
=========================================================
"""

import pygame

from face import VedFace
from renderer import FaceRenderer
from face_controller import ExpressionReceiver


# Manual keys, for testing without the robot running.
KEY_EXPRESSIONS = {
    pygame.K_1: "idle",
    pygame.K_2: "happy",
    pygame.K_3: "listening",
    pygame.K_4: "thinking",
    pygame.K_5: "speaking",
    pygame.K_6: "surprised",
    pygame.K_7: "sad",
    pygame.K_8: "sleeping",
    pygame.K_9: "wink",
}


def main():

    face = VedFace()

    renderer = FaceRenderer()

    clock = pygame.time.Clock()

    ################################################
    # Listen for expressions from the robot process
    #
    # Failing to bind is not fatal -- another copy of
    # this file may already be running, or the port may
    # be taken. The face still works from the keyboard.
    ################################################

    receiver = ExpressionReceiver()

    if receiver.start():
        print("Listening for expressions from the robot.")
    else:
        print("Running standalone -- use keys 1-9.")

    print("Keys 1-9 set an expression. ESC quits.")

    running = True

    face.idle()

    try:
        while running:

            ########################################
            # Window events
            ########################################

            for event in pygame.event.get():

                if event.type == pygame.QUIT:
                    running = False

                elif event.type == pygame.KEYDOWN:

                    if event.key == pygame.K_ESCAPE:
                        running = False

                    elif event.key in KEY_EXPRESSIONS:

                        name = KEY_EXPRESSIONS[event.key]

                        getattr(face, name, face.idle)()

            ########################################
            # Expressions from the robot
            #
            # poll() returns None when nothing new has
            # arrived, so this costs nothing per frame.
            ########################################

            incoming = receiver.poll()

            if incoming:
                getattr(face, incoming, face.idle)()

            ########################################
            # Draw
            ########################################

            renderer.render(face.current_expression())

            clock.tick(60)

    except KeyboardInterrupt:
        print("\nInterrupted.")

    finally:
        receiver.stop()
        pygame.quit()
        print("Face display stopped.")


if __name__ == "__main__":
    main()