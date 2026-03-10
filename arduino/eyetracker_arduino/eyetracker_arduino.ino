#include <Servo.h>
#include <ArduinoJson.h>

// Pin definitions
const int buzzer_pin = 3;
const int button_pin = 5;   // Active high, connect other end into ground
const int servo1 = 11;       // first servo, grey wire
const int servo2 = 10;      // second servo, blue wire
const int led_pin = 12;
const int laser_pin = 13;

// Command byte constants (single-byte for efficiency)
const byte CMD_START_TEST = 0x01;      // Start test
const byte CMD_END_TEST = 0x02;        // End test
const byte CMD_PING = 0x03;            // Ping signal
const byte CMD_WITHIN_THRESHOLD = 0x04;  // Within threshold signal
const byte CMD_OUT_OF_THRESHOLD = 0x05;  // Out of threshold signal
const byte CMD_TEST_RESULTS = 0x06;  // Get test results

// const char CMD_START_TEST = '1';      // Start test
// const char CMD_END_TEST = '2';        // End test
// const char CMD_PING = '3';            // Ping signal
// const char CMD_WITHIN_THRESHOLD = '4';  // Within threshold signal
// const char CMD_OUT_OF_THRESHOLD = '5';  // Out of threshold signal
// const char CMD_TEST_RESULTS = '6';  // Check test status: Ready, Running, Ended

// Response byte constants
const char RESP_ACK = 'O';             // Command acknowledged

// Timing constants
const int point_duration = 5000; // wait time before shifting to next point
const int laser_duration = 2000; // duration for laser to be turned on
const int PRE_FIRE_DELAY = 500;    // 0.5 second delay before firing
const int buzzer_duration = 1000; // Buzzer duration in milliseconds
const unsigned long DEBOUNCE_DELAY = 50; 
const int PROGRESS_INTERVAL = 300; // Send progress report every 100ms

// Servo movement parameters
const float SERVO_STEPS = 1;           
// const float TOTAL_MOVE_TIME = 2000;    

// State tracking variables
int button_state = HIGH; // Active LOW, take note
int last_button_state = HIGH;
int laser_state = LOW;
int laser_flag = LOW;
int buzzer_state = LOW;
int led_state = LOW;
int point_tracker = -1;

// Timing variables
unsigned long timestamp = 0;
unsigned long buzzer_start_time = 0;
unsigned long laser_start_time = 0;
unsigned long last_debounce_time = 0;
unsigned long last_progress_send_time = 0;

// Servo position tracking
float current_servo1_pos = 90;
float current_servo2_pos = 90;
bool is_moving = false;
unsigned long last_move_time = 0;

// Test state variables
bool test_running = false;
bool test_finished = false;
unsigned long test_start_time = 0;
const unsigned long TEST_TIMEOUT = 300000; // 5 minutes timeout
int out_of_thres_counter = 0;

// Servo objects
Servo myservo1;
Servo myservo2;

// Laser point coordinates (4 points): (Y-axis: 0 (top) - 180 (bottom), X-axis: 0 (right) - 180 (left)) 
// int myPoints[4][2] = {{75, 110}, {70, 60}, {20, 60}, {30, 110}}; 
int myPoints[][2] = {
    {74, 8},
    {29, 52},
    {61, 10},
    {43, 5},
    {83, 41},
    {20, 11},
    {52, 33},
    {67, 19},
    {88, 3},
    {35, 44},

    {57, 27},
    {24, 58},
    {31, 14},
    {90, 14},
    {55, 6},
    {22, 18},
    {79, 55},
    {46, 9},
    {62, 46},
    {50, 25},

    {41, 60},
    {82, 1},
    {28, 7},
    {58, 33},
    {54, 2},
    {69, 14},
    {18, 49},
    {76, 4},
    {17, 0},
    {55, 50},

    {33, 28},
    {90, 18},
    {23, 4},
    {64, 50},
    {55, 13},
    {71, 60},
    {57, 12},
    {39, 1},
    {86, 22},
    {63, 0}
  // {17,0},
  // //{0, 14},
  // {17,60},
  // {55,60},
  // //{55,14},
  // {55,0},
  // {90,0},
  // //{90,14},
  // {90,60}
};
const int numPoints = sizeof(myPoints) / sizeof(myPoints[0]); 
char click_tracker[numPoints];
int click_counter = 0;

void setup() {
  // Setup serial with higher baud rate for efficiency
  Serial.begin(115200);

  // Configure pins
  pinMode(button_pin, INPUT_PULLUP);
  pinMode(laser_pin, OUTPUT);
  pinMode(buzzer_pin, OUTPUT);
  pinMode(led_pin, OUTPUT);
  digitalWrite(buzzer_pin, buzzer_state);

  // Attach servos
  myservo1.attach(servo1, 600, 2000);
  myservo2.attach(servo2, 600, 2000);

  // Init click tracker array
  for (int i = 0; i < numPoints; i++) {
    click_tracker[i] = '0';
  }
  
  Serial.println("System ready");
}

void loop() {
  unsigned long current_time = millis();
  
  // Process any incoming serial commands (more efficient processing)
  if (Serial.available() > 0) {
    byte command = Serial.read();
    // char command = Serial.read();
    
    switch(command) {
      case CMD_START_TEST:
        if (!test_running) {
          startTest(); // This function already prints "Test starting..."
          Serial.println(point_tracker);
        } else {
          Serial.println("System busy: Test already running");
        }
        break;
        
      case CMD_END_TEST:
        if (test_running) {
          endTest("Test manually stopped");
        }
        break;
        
      case CMD_PING:
        if (test_running) {
          Serial.println("Test Running");
        } else if (test_finished) {
          Serial.println("Test Ended");
        } else {
          Serial.println("System Online");
        }
        break;
        
      
      case CMD_WITHIN_THRESHOLD:
        // Handle within threshold command
        digitalWrite(led_pin, LOW);
        led_state = LOW;
        // Serial.write(RESP_ACK);  // Send immediate acknowledgment
        break;
        
      case CMD_OUT_OF_THRESHOLD:
        // Handle out of threshold command
        out_of_thres_counter += 1;
        digitalWrite(led_pin, HIGH);
        led_state = HIGH;
        // Serial.write(RESP_ACK);  // Send immediate acknowledgment
        break;

      // This is extra, during test run, arduino automatically sends updates every 300ms without request
      case CMD_TEST_RESULTS:
        { // Scope for StaticJsonDocument
          JsonDocument doc; // Increased size slightly for safety
          if (test_running) {
            doc["test_status"] = "Test Running";
          } else if (test_finished) {
            doc["test_status"] = "Test Finished";
            // Optionally include last test results here too
            doc["points_shown"] = point_tracker; // Point tracker would have incremeted to total points + 1, before breaking when point_tracker >= numPoints condiiton is checked. Since, point trakcer is 0-indexed, need + 1 here.
            doc["total_points"] = numPoints;
            doc["clicks"] = click_counter;
            char tracker_str[numPoints + 1];
            memcpy(tracker_str, click_tracker, numPoints);
            tracker_str[numPoints] = '\0';
            doc["click_pattern"] = tracker_str;
            doc["out_of_thres_counter"] = out_of_thres_counter;
          } else {
            doc["test_status"] = "System Ready";
          }
          serializeJson(doc, Serial);
          Serial.println(); // Add a newline after JSON
        }
        break;

      default:
        // Unknown command, ignore
        break;
    }
    
    // Clear any remaining serial data
    while (Serial.available()) {
      Serial.read();
    }
  }

  // Only execute test logic if test is running
  if (test_running) {
    runTestLogic(current_time);

    if (millis() - last_progress_send_time >= PROGRESS_INTERVAL) {
      printTestStatus();; // Controlled interval
      last_progress_send_time = millis();
    }

    // Check if test should time out
    if ((test_start_time < current_time) && (current_time - test_start_time > TEST_TIMEOUT)) {
      endTest("Test timed out");
    }
  }
}

void startTest() {
  Serial.println("Test starting...");
  test_running = true;
  test_finished = false;
  test_start_time = millis();
  timestamp = millis();
  
  // Reset all counters and states
  point_tracker = -1;
  click_counter = 0;
  out_of_thres_counter = 0;
  
  for (int i = 0; i < numPoints; i++) {
    click_tracker[i] = '0';
  }
  
  // Set initial position
  int target_x = myPoints[point_tracker][0];
  int target_y = myPoints[point_tracker][1];
  
  // Store as current position without movement (first position)
  current_servo1_pos = target_y;
  current_servo2_pos = target_x;
  
  // Move servos directly to initial position (no need for smooth movement at start)
  myservo1.write(target_y);
  myservo2.write(target_x);
  
  // Remove jittering
  delay(50);
}

void endTest(String reason) {
  // Turn off all outputs
  digitalWrite(laser_pin, LOW);
  digitalWrite(buzzer_pin, LOW);
  
  laser_state = LOW;
  laser_flag = LOW;
  buzzer_state = LOW;
  
  test_running = false;
  test_finished = true;
  
  // Report test results
  Serial.println("TEST_END");
  Serial.print("Reason: ");
  Serial.println(reason);
  Serial.print("Click counter: ");
  Serial.println(click_counter);
  Serial.print("Click tracker: ");
  Serial.println(click_tracker);
  Serial.print("Out-of-thres tracker: ");
  Serial.println(out_of_thres_counter);
  
  Serial.println("System ready");
}

void smoothServoMove(int target_servo1, int target_servo2) {
  // Calculate the step sizes for each servo
  // float step_size1 = (target_servo1 - current_servo1_pos) / (float)SERVO_STEPS;
  // float step_size2 = (target_servo2 - current_servo2_pos) / (float)SERVO_STEPS;

  // Calculate delay between steps
  // int step_delay = TOTAL_MOVE_TIME / SERVO_STEPS;

  // // Variables to track intermediate positions
  // float pos1 = current_servo1_pos;
  // float pos2 = current_servo2_pos;

  // // Perform the gradual movement
  // for (int i = 1; i <= SERVO_STEPS; i++) {
  //   // Calculate intermediate positions
  //   pos1 = current_servo1_pos + (step_size1 * i);
  //   pos2 = current_servo2_pos + (step_size2 * i);

  //   // Move servos to the calculated positions
  //   int rounded_pos1 = round(pos1);
  //   int rounded_pos2 = round(pos2);

  //   // Write positions to servos
  //   myservo1.write(rounded_pos1);
  //   myservo2.write(rounded_pos2);

  //   // Allow time for servo to move
  //   delay(step_delay);
  // }

  // Make sure we're at the final position
  myservo1.write(target_servo1);
  myservo2.write(target_servo2);

  // Update current positions
  current_servo1_pos = target_servo1;
  current_servo2_pos = target_servo2;
}

void printTestStatus() {
  JsonDocument doc; // Increased size slightly for safety
  if (test_running) {
    doc["test_status"] = "Test Running";
    doc["points_shown"] = point_tracker + 1; // +1 because point_tracker is 0-indexed
    doc["total_points"] = numPoints;
    doc["clicks"] = click_counter;
    // Create a temporary string for click_tracker for ArduinoJson
    char tracker_str[numPoints + 1];
    memcpy(tracker_str, click_tracker, numPoints);
    tracker_str[numPoints] = '\0'; // Null-terminate
    doc["click_pattern"] = tracker_str;
  } else if (test_finished) {
    doc["test_status"] = "Test Finished";
    // Optionally include last test results here too
    doc["points_shown"] = point_tracker + 1;
    doc["total_points"] = numPoints;
    doc["clicks"] = click_counter;
    char tracker_str[numPoints + 1];
    memcpy(tracker_str, click_tracker, numPoints);
    tracker_str[numPoints] = '\0';
    doc["click_pattern"] = tracker_str;
  } else {
    doc["test_status"] = "System Ready";
  }
  serializeJson(doc, Serial);
  Serial.println(); // Add a newline after JSON
}

void runTestLogic(unsigned long current_time) {
  // Check current time and duration
  unsigned long duration = current_time - timestamp;

  // Inverse logic, if 1 means button not pressed, 0 means button pressed
  int reading = digitalRead(button_pin);

  if (reading != last_button_state) {
    last_debounce_time = current_time;
    last_button_state = reading;
  }

  if (duration > point_duration) {
    // Update point_tracker to the next point
    point_tracker++;

    // Check if we've completed a full cycle and end the test
    if (point_tracker >= numPoints) {
      endTest("Test completed successfully");
      return;
    }

    // If laser is still on turn it off before moving
    if (laser_state == HIGH) {
      digitalWrite(laser_pin, LOW);
      laser_state = LOW;
    }

    int target_x = myPoints[point_tracker][0];
    int target_y = myPoints[point_tracker][1];

    // Move the servos smoothly instead of abruptly
    smoothServoMove(target_y, target_x);  // Note: servo1=y, servo2=x

    // Set up laser firing
    laser_flag = HIGH;
    laser_start_time = current_time;  // Initialize the start time
    laser_state = LOW;  // Ensure laser starts from OFF state

    // Update timestamp
    timestamp = current_time;
  }

  // Button debounce and handling
  if ((current_time - last_debounce_time) > DEBOUNCE_DELAY) {
    if (reading != button_state) {
      button_state = reading;
    
      if (button_state == LOW) {
        // Serial.println("Pressed!");
        if (laser_state == LOW) {
          // Wrong press, turn on buzzer
          // Serial.println("Wrong press!");
          digitalWrite(buzzer_pin, HIGH);
          buzzer_state = HIGH;
          buzzer_start_time = current_time;
        } 
        else {
          // Turn off laser
          // Serial.println("Right press!");
          digitalWrite(laser_pin, LOW);
          laser_state = LOW;
          laser_flag = LOW;
          
          // Add click to click tracker
          click_tracker[point_tracker] = '1';
        }

        click_counter++;
      } 
    }
  }
  
  // Laser control logic
  if (laser_flag == HIGH) {
    if (laser_state == LOW) {
      if (current_time - laser_start_time >= PRE_FIRE_DELAY) {
        digitalWrite(laser_pin, HIGH);
        laser_state = HIGH;
        laser_start_time = current_time;  // Reset start time for duration tracking
      }
    }
    else if (current_time - laser_start_time >= laser_duration) {
      // Turn off laser after duration
      digitalWrite(laser_pin, LOW);
      laser_state = LOW;
      laser_flag = LOW;
    }
  }

  // Buzzer control logic
  if (buzzer_state == HIGH) {    
    if (current_time - buzzer_start_time >= buzzer_duration) {
      digitalWrite(buzzer_pin, LOW);  // Turn off the buzzer
      buzzer_state = LOW;
    }
  }
}