#include <BluetoothSerial.h>
#include <ESP32Servo.h>

#if !defined(CONFIG_BT_ENABLED) || !defined(CONFIG_BLUEDROID_ENABLED)
#error Bluetooth is not enabled! Please run `make menuconfig` to and enable it
#endif

Servo myServo;
const int SERVO_PIN = 32;

const int NUM_SENSORS = 4;
const int fsrPins[NUM_SENSORS] = {A0, A1, A2, A3};  // FSR inputs

BluetoothSerial SerialBT;

// Threshold Settings
// These are analog values
const int TARGET_LOW  = 300;   // lower bound of desired force range
const int TARGET_HIGH = 700;   // upper bound of desired force range
const int DEADBAND    = 20;    // small band to avoid jitter around thresholds


// Servo Settings
const int MIN_ANGLE   = 0;     // hard limit for servo
const int MAX_ANGLE   = 180;   // hard limit for servo
const int START_ANGLE = 90;    // starting at 90 degrees
const int STEP_ANGLE  = 2;     // how many degrees to move per correction step


void setup() {
  Serial.begin(115200);
  SerialBT.begin("ESP32test"); //Bluetooth device name
  Serial.println("The device started, now you can pair it with bluetooth!");
  myServo.attach(SERVO_PIN, 500, 2500);
  myServo.write(START_ANGLE);  // start at 90°
  delay(500);
}

int readAverageFSR() {
  long sum = 0;
  for (int i = 0; i < NUM_SENSORS; i++) {
    int reading = analogRead(fsrPins[i]);
    sum += reading;
  }
  int avg = sum / NUM_SENSORS;
  return avg;
}

void loop() {
  int avgFSR = readAverageFSR();
  int currentAngle = myServo.read();  // current servo angle

  // Print for debugging
  Serial.print("Avg FSR: ");
  Serial.print(avgFSR);
  Serial.print(" | Angle: ");
  Serial.println(currentAngle);

  // Control logic:
  // If pressure is too low -> move one direction
  // If pressure is too high -> move opposite direction
  // If inside range -> do nothing (or very small changes if you want)
  if (SerialBT.available()) {
      //Serial.print(SerialBT.readString());
      String msg = SerialBT.readString();
      Serial.print(msg);

      if (msg == "On"){
        if (avgFSR < (TARGET_LOW - DEADBAND)) {
        // Too little force -> move servo to try to increase it
        currentAngle -= STEP_ANGLE;
        } 
        else if (avgFSR > (TARGET_HIGH + DEADBAND)) {
        // Too much force -> move servo to try to decrease it
        currentAngle += STEP_ANGLE;
        }
        // Clamp angle to safe servo range
        currentAngle = constrain(currentAngle, MIN_ANGLE, MAX_ANGLE);
        myServo.write(currentAngle);
      }
      else if (msg == "Off"){
        myServo.write(180);
      }   
   }
   delay(20);
}
