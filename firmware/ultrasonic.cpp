#include <Arduino.h>
#include <NewPing.h>

#include "pins.h"
#include "ultrasonic.h"

constexpr uint16_t MAX_DISTANCE = 400;

NewPing frontSensor(FRONT_TRIG, FRONT_ECHO, MAX_DISTANCE);
NewPing leftSensor(FRONT_TRIG, FRONT_ECHO, MAX_DISTANCE);
NewPing rightSensor(RIGHT_TRIG, RIGHT_ECHO, MAX_DISTANCE);

static long readSensor(NewPing& sensor)
{
    unsigned int distance = sensor.ping_cm();

    // No echo received
    if (distance == 0)
    {
        return MAX_DISTANCE;
    }

    return distance;
}

void ultrasonicInit()
{
}

long getFrontDistance()
{
    return readSensor(frontSensor);
}

long getLeftDistance()
{
    return readSensor(leftSensor);
}

long getRightDistance()
{
    return readSensor(rightSensor);
}