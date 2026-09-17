/*
 * battery.h
 *
 * Monitors the robot battery.
 *
 * Future features:
 * - Battery voltage
 * - Battery percentage
 * - Low battery warning
 * - Auto docking
 */

#ifndef BATTERY_H
#define BATTERY_H

// Initialize battery monitoring
void batteryInit();

// Read battery voltage
float getBatteryVoltage();

// Battery percentage (0–100)
int getBatteryPercentage();

// Returns true if battery is low
bool batteryLow();

#endif