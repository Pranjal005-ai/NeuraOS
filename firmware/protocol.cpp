/*
 * protocol.cpp
 *
 * JSON Communication
 */

#include <Arduino.h>
#include <ArduinoJson.h>

#include "protocol.h"
#include "battery.h"
#include "tof.h"
#include "ultrasonic.h"

void protocolInit()
{
}

void sendSensorData()
{
    StaticJsonDocument<256> json;

    json["front"] = getFrontDistance();
    json["left"] = getLeftDistance();
    json["right"] = getRightDistance();

    json["tof_left"] = getLeftToF();
    json["tof_right"] = getRightToF();

    json["battery"] = getBatteryPercentage();

    json["status"] = "READY";

    serializeJson(json, Serial);

    Serial.println();
}