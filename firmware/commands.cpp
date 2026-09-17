#include <Arduino.h>

#include "commands.h"
#include "motor.h"

void executeCommand(String command)
{
    command.toUpperCase();

    if (command == "FORWARD")
    {
        moveForward();
        Serial.println("OK FORWARD");
    }

    else if (command == "BACKWARD")
    {
        moveBackward();
        Serial.println("OK BACKWARD");
    }

    else if (command == "LEFT")
    {
        turnLeft();
        Serial.println("OK LEFT");
    }

    else if (command == "RIGHT")
    {
        turnRight();
        Serial.println("OK RIGHT");
    }

    else if (command == "STOP")
    {
        stopMotors();
        Serial.println("OK STOP");
    }

    else
    {
        Serial.println("UNKNOWN COMMAND");
    }
}