/*
 * tof.cpp
 *
 * Handles the two VL53L0X Time-of-Flight sensors.
 *
 * Both sensors share the same I2C bus.
 * Since they have the same default I2C address (0x29),
 * we use the XSHUT pins to power them up one at a time
 * and assign each sensor a unique address.
 */

#include <Wire.h>
#include <Adafruit_VL53L0X.h>

#include "pins.h"
#include "tof.h"

// ==========================================================
// ToF Sensor Objects
// ==========================================================

// Front/Left ToF sensor
Adafruit_VL53L0X tofLeft;

// Rear/Right ToF sensor
Adafruit_VL53L0X tofRight;

// ==========================================================
// Initialization
// ==========================================================

void tofInit()
{
    // ------------------------------------------
    // Initialize the I2C bus
    // ------------------------------------------

    Wire.begin(SDA_PIN, SCL_PIN);

    // ------------------------------------------
    // Configure XSHUT pins as outputs
    //
    // XSHUT allows us to individually enable
    // each sensor so that we can change its
    // I2C address.
    // ------------------------------------------

    pinMode(TOF1_XSHUT, OUTPUT);
    pinMode(TOF2_XSHUT, OUTPUT);

    // ------------------------------------------
    // Disable both sensors
    // ------------------------------------------

    digitalWrite(TOF1_XSHUT, LOW);
    digitalWrite(TOF2_XSHUT, LOW);

    delay(10);

    // ======================================================
    // Initialize Left ToF Sensor
    // ======================================================

    // Enable only the left sensor

    digitalWrite(TOF1_XSHUT, HIGH);

    delay(10);

    // Assign a new I2C address

    if (!tofLeft.begin(0x30))
    {
        Serial.println("ERROR: Left ToF sensor not detected.");
    }
    else
    {
        Serial.println("Left ToF initialized.");
    }

    // ======================================================
    // Initialize Right ToF Sensor
    // ======================================================

    // Enable the right sensor

    digitalWrite(TOF2_XSHUT, HIGH);

    delay(10);

    // Assign another I2C address

    if (!tofRight.begin(0x31))
    {
        Serial.println("ERROR: Right ToF sensor not detected.");
    }
    else
    {
        Serial.println("Right ToF initialized.");
    }
}

// ==========================================================
// Left ToF Reading
// ==========================================================

int getLeftToF()
{
    VL53L0X_RangingMeasurementData_t measurement;

    // Read distance measurement

    tofLeft.rangingTest(&measurement, false);

    // RangeStatus == 4 means measurement failed

    if (measurement.RangeStatus == 4)
    {
        return -1;
    }

    return measurement.RangeMilliMeter;
}

// ==========================================================
// Right ToF Reading
// ==========================================================

int getRightToF()
{
    VL53L0X_RangingMeasurementData_t measurement;

    // Read distance measurement

    tofRight.rangingTest(&measurement, false);

    // RangeStatus == 4 means measurement failed

    if (measurement.RangeStatus == 4)
    {
        return -1;
    }

    return measurement.RangeMilliMeter;
}