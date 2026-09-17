#ifndef PINS_H
#define PINS_H

// ================================
// L298N Motor Driver
// ================================
#define MOTOR_IN1 26
#define MOTOR_IN2 27
#define MOTOR_IN3 14
#define MOTOR_IN4 12

// PWM (future speed control)
#define MOTOR_ENA 25
#define MOTOR_ENB 13

// ================================
// Ultrasonic Sensors
// ================================

// Front
#define US_FRONT_TRIG 18
#define US_FRONT_ECHO 19

// Left
#define US_LEFT_TRIG 32
#define US_LEFT_ECHO 33

// Right
#define US_RIGHT_TRIG 16
#define US_RIGHT_ECHO 17

// ================================
// ToF Sensors (I2C)
// ================================

#define TOF_SDA 21
#define TOF_SCL 22

#define TOF1_XSHUT 4
#define TOF2_XSHUT 5

// ================================
// Battery Monitor (Future)
// ================================

#define BATTERY_PIN 34

#endif