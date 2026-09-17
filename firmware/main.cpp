/*
 * ==========================================================
 * main.cpp
 *
 * Ved ESP32 Firmware
 *
 * Responsibilities:
 *  - Initialize all hardware modules
 *  - Receive commands from Raspberry Pi
 *  - Run safety monitoring
 *  - Periodically send sensor data
 *
 * Author: Pranjal
 * ==========================================================
 */

#include <Arduino.h>

#include "battery.h"
#include "commands.h"
#include "motor.h"
#include "protocol.h"
#include "safety.h"
#include "serial.h"
#include "tof.h"
#include "ultrasonic.h"

// ==========================================================
// Configuration
// ==========================================================

// Send sensor data every second
const unsigned long SENSOR_INTERVAL = 1000;

// Stores previous sensor transmission time
unsigned long lastSensorRead = 0;

// ==========================================================
// Setup
// ==========================================================

void setup()
{
    // ------------------------------------------
    // Start serial communication
    // ------------------------------------------

    serialInit();

    serialWrite("VED Firmware Booting...");

    // ------------------------------------------
    // Initialize hardware modules
    // ------------------------------------------

    motorInit();

    ultrasonicInit();

    tofInit();

    batteryInit();

    safetyInit();

    protocolInit();

    serialWrite("VED Firmware Ready");
}

// ==========================================================
// Main Loop
// ==========================================================

void loop()
{
    // ------------------------------------------
    // Check for commands from Raspberry Pi
    // ------------------------------------------

    if (serialAvailable())
    {
        String message = serialRead();

        processCommand(message);
    }

    // ------------------------------------------
    // Run safety checks continuously
    // ------------------------------------------

    safetyLoop();

    // ------------------------------------------
    // Send sensor data every second
    // ------------------------------------------

    if (millis() - lastSensorRead >= SENSOR_INTERVAL)
    {
        lastSensorRead = millis();

        sendSensorData();
    }
}