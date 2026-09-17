/*
 * tof.h
 *
 * Handles the two VL53L0X Time-of-Flight sensors.
 *
 * Left ToF  -> Front underside
 * Right ToF -> Rear underside
 */

#ifndef TOF_H
#define TOF_H

// Initialize both ToF sensors
void tofInit();

// Returns distance in millimeters
int getLeftToF();

int getRightToF();

#endif