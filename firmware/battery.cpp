/*
 * battery.cpp
 *
 * Battery monitoring module.
 *
 * NOTE:
 * Ved v1 does not yet have a voltage divider connected
 * to the ESP32, so these are placeholder functions.
 *
 * Once the hardware is added, this file will read the
 * battery voltage using the ESP32 ADC.
 */

#include <Arduino.h>

#include "battery.h"

// ==========================================================
// Initialization
// ==========================================================

void batteryInit()
{
    // Nothing to initialize yet
}

// ==========================================================
// Battery Voltage
// ==========================================================

float getBatteryVoltage()
{
    // Placeholder value

    return 7.4;
}

// ==========================================================
// Battery Percentage
// ==========================================================

int getBatteryPercentage()
{
    // Placeholder value

    return 100;
}

// ==========================================================
// Low Battery
// ==========================================================

bool batteryLow()
{
    return false;
}/*
 * battery.cpp
 *
 * Battery monitoring module.
 *
 * NOTE:
 * Ved v1 does not yet have a voltage divider connected
 * to the ESP32, so these are placeholder functions.
 *
 * Once the hardware is added, this file will read the
 * battery voltage using the ESP32 ADC.
 */

#include <Arduino.h>

#include "battery.h"

// ==========================================================
// Initialization
// ==========================================================

void batteryInit()
{
    // Nothing to initialize yet
}

// ==========================================================
// Battery Voltage
// ==========================================================

float getBatteryVoltage()
{
    // Placeholder value

    return 7.4;
}

// ==========================================================
// Battery Percentage
// ==========================================================

int getBatteryPercentage()
{
    // Placeholder value

    return 100;
}

// ==========================================================
// Low Battery
// ==========================================================

bool batteryLow()
{
    return false;
}