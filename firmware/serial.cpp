#include <Arduino.h>

#include "serial.h"
#include "commands.h"

String incomingCommand = "";

void serialSetup()
{
    Serial.begin(115200);

    while (!Serial)
    {
        delay(10);
    }

    Serial.println("VED ESP32 READY");
}

void serialLoop()
{
    while (Serial.available())
    {
        char c = Serial.read();

        if (c == '\n')
        {
            incomingCommand.trim();

            if (incomingCommand.length() > 0)
            {
                executeCommand(incomingCommand);
            }

            incomingCommand = "";
        }
        else
        {
            incomingCommand += c;
        }
    }
}