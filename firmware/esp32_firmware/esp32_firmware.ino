/*
  esp32_firmware.ino

  Receives movement commands from Raspberry Pi
  over USB Serial and drives the L298N motor driver.
*/

// -----------------------------
// L298N Pin Connections
// -----------------------------
const int LEFT_IN1 = 26;
const int LEFT_IN2 = 27;

const int RIGHT_IN1 = 14;
const int RIGHT_IN2 = 12;

// -----------------------------
void setup() {

  Serial.begin(115200);

  pinMode(LEFT_IN1, OUTPUT);
  pinMode(LEFT_IN2, OUTPUT);

  pinMode(RIGHT_IN1, OUTPUT);
  pinMode(RIGHT_IN2, OUTPUT);

  stopMotors();

  Serial.println("VED ESP32 READY");
}

// -----------------------------
void loop() {

  if (!Serial.available())
    return;

  String command = Serial.readStringUntil('\n');

  command.trim();

  Serial.println(command);

  if (command == "MOVE_FORWARD")
    forward();

  else if (command == "MOVE_BACKWARD")
    backward();

  else if (command == "TURN_LEFT")
    left();

  else if (command == "TURN_RIGHT")
    right();

  else if (command == "STOP")
    stopMotors();
}

// -----------------------------
void forward() {

  digitalWrite(LEFT_IN1, LOW);
  digitalWrite(LEFT_IN2, HIGH);

  digitalWrite(RIGHT_IN1, LOW);
  digitalWrite(RIGHT_IN2, HIGH);
}

// -----------------------------
void backward() {

  digitalWrite(LEFT_IN1, HIGH);
  digitalWrite(LEFT_IN2, LOW);

  digitalWrite(RIGHT_IN1, HIGH);
  digitalWrite(RIGHT_IN2, LOW);
}

// -----------------------------
void left() {

  digitalWrite(LEFT_IN1, LOW);
  digitalWrite(LEFT_IN2, HIGH);

  digitalWrite(RIGHT_IN1, HIGH);
  digitalWrite(RIGHT_IN2, LOW);
}

// -----------------------------
void right() {

  digitalWrite(LEFT_IN1, HIGH);
  digitalWrite(LEFT_IN2, LOW);

  digitalWrite(RIGHT_IN1, LOW);
  digitalWrite(RIGHT_IN2, HIGH);
}

// -----------------------------
void stopMotors() {

  digitalWrite(LEFT_IN1, LOW);
  digitalWrite(LEFT_IN2, LOW);

  digitalWrite(RIGHT_IN1, LOW);
  digitalWrite(RIGHT_IN2, LOW);
}