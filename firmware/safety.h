/*
 * safety.h
 *
 * Safety Manager
 *
 * Responsible for stopping the robot whenever
 * an unsafe condition is detected.
 */

#ifndef SAFETY_H
#define SAFETY_H

// Initialize safety module
void safetyInit();

// Called repeatedly from loop()
void safetyLoop();

// Returns true if robot can move
bool canMove();

// Emergency stop
void emergencyStop();

#endif