/*
 * ultrasonic.h
 *
 * Handles the three HC-SR04 ultrasonic sensors.
 */

#ifndef ULTRASONIC_H
#define ULTRASONIC_H

// Initialize ultrasonic sensors
void ultrasonicInit();

// Returns distance in centimeters
long getFrontDistance();

long getLeftDistance();

long getRightDistance();

#endif