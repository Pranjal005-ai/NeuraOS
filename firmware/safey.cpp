/*
 * safety.cpp
 *
 * Robot Safety Manager
 */

#include <Arduino.h>

#include "motor.h"
#include "tof.h"
#include "ultrasonic.h"
#include "battery.h"
#include "safety.h"

// ==========================================================
// Configuration
// ==========================================================

// Stop if an object is closer than this
const int FRONT_STOP_DISTANCE = 20;      // cm

// Stop if a stair/drop is detected
const int MIN_TOF_DISTANCE = 40;         // mm

// ==========================================================
// Initialization
// ==========================================================

void safetyInit()
{
    // Nothing required yet
}

// ==========================================================
// Can Robot Move?
// ==========================================================

bool canMove()
{
    // Front obstacle

    if (getFrontDistance() <= FRONT_STOP_DISTANCE)
    {
        return false;
    }

    // Left ToF invalid

    if (getLeftToF() == -1)
    {
        return false;
    }

    // Right ToF invalid

    if (getRightToF() == -1)
    {
        return false;
    }

    return true;
}

// ==========================================================
// Emergency Stop
// ==========================================================

void emergencyStop()
{
    stopMotors();

    Serial.println("SAFETY STOP");
}

// ==========================================================
// Main Safety Loop
// ==========================================================

void safetyLoop()
{
    if (!canMove())
    {
        emergencyStop();
    }
}