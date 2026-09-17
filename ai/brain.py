"""
brain.py

Decision Engine for Project Ved / NeuraOS

Responsibilities:
- Understand the user's command
- Decide which module should handle it
- Return an intent to assistant.py
"""


class Brain:

    def process_command(self, command):

        # Convert command to lowercase for easier matching
        command = command.lower()

        # =====================================================
        # MOVEMENT
        # =====================================================

        if any(word in command for word in [
            "forward",
            "go forward",
            "move forward",
            "ahead",
            "आगे"
        ]):
            return "MOVE_FORWARD"

        if any(word in command for word in [
            "back",
            "backward",
            "move back",
            "पीछे"
        ]):
            return "MOVE_BACKWARD"

        if any(word in command for word in [
            "left",
            "turn left",
            "बाएं"
        ]):
            return "TURN_LEFT"

        if any(word in command for word in [
            "right",
            "turn right",
            "दाएं"
        ]):
            return "TURN_RIGHT"

        if any(word in command for word in [
            "stop",
            "halt",
            "freeze",
            "रुको"
        ]):
            return "STOP"

        # =====================================================
        # OBJECT SEARCH
        # =====================================================

        if any(word in command for word in [
            "find bottle",
            "find cup",
            "find chair",
            "find bag",
            "find person",
            "find phone",
            "find laptop",
            "find my"
        ]):
            return "OBJECT_SEARCH"

        # =====================================================
        # PERSON FOLLOWING
        # =====================================================

        if any(word in command for word in [
            "follow me",
            "follow"
        ]):
            return "FOLLOW"

        if any(word in command for word in [
            "stop following",
            "don't follow",
            "leave me"
        ]):
            return "STOP_FOLLOW"

        # =====================================================
        # CAMERA / VISION
        # =====================================================

        if any(word in command for word in [
            "what do you see",
            "look around",
            "describe",
            "camera",
            "who is in front",
            "what can you see"
        ]):
            return "VISION"

        # =====================================================
        # QR SCANNER
        # =====================================================

        if any(word in command for word in [
            "scan qr",
            "scan qr code",
            "read qr",
            "read qr code",
            "scan code"
        ]):
            return "QR_SCAN"

        # =====================================================
        # OCR
        # =====================================================

        if any(word in command for word in [
            "read this",
            "read text",
            "read paper",
            "read document",
            "read label",
            "read medicine",
            "read sign",
            "ocr"
        ]):
            return "OCR"

        # =====================================================
        # FACE RECOGNITION
        # =====================================================

        if any(word in command for word in [
            "who is this",
            "who is he",
            "who is she",
            "recognize face",
            "identify person"
        ]):
            return "FACE_RECOGNITION"

        # =====================================================
        # MEMORY
        # =====================================================

        if "remember" in command:
            return "MEMORY_SAVE"

        if any(word in command for word in [
            "what do you remember",
            "tell me what you remember",
            "memory"
        ]):
            return "MEMORY_READ"

        # =====================================================
        # DEFAULT
        # =====================================================

        return "CHAT"


# ==========================================================
# Singleton
# ==========================================================

brain = Brain() 