#include <Servo.h>
#include <ArduinoJson.h>
#include <Adafruit_NeoPixel.h>

// Pin definitions

const int led_pin = 4;
const int button_pin = 5;   // Active high, connect other end into ground


const byte ledPin0 =  10;  // led data pubs
const byte ledPin1 =  11;    
const byte ledPin2 =  12;
const byte ledPin3 =  13;

// Command byte constants (single-byte for efficiency)
const byte CMD_START_TEST = 0x01;      // Start test
const byte CMD_END_TEST = 0x02;        // End test
const byte CMD_PING = 0x03;            // Ping signal
const byte CMD_WITHIN_THRESHOLD = 0x04;  // Within threshold signal
const byte CMD_OUT_OF_THRESHOLD = 0x05;  // Out of threshold signal
const byte CMD_TEST_RESULTS = 0x06;  // Get test results

// Response byte constants
const char RESP_ACK = 'O';             // Command acknowledged

// Timing constants
const int point_duration = 5000; // wait time before shifting to next point
//const int laser_duration = 2000; // duration for laser to be turned on
const int PRE_FIRE_DELAY = 500;    // 0.5 second delay before firing
//const int buzzer_duration = 1000; // Buzzer duration in milliseconds
const unsigned long DEBOUNCE_DELAY = 50; 
const int PROGRESS_INTERVAL = 300; // Send progress report every 100ms 

// State tracking variables
int button_state = HIGH; // Active LOW, take note
int last_button_state = HIGH;
int buzzer_state = LOW;
// int laser_state = LOW;
// int laser_flag = LOW;
int led_state = LOW;
int LED_strip_state = LOW;
int point_tracker = -1;

// Timing variables
unsigned long timestamp = 0;
unsigned long last_debounce_time = 0;
unsigned long last_progress_send_time = 0;

// Test state variables
bool test_running = false;
bool test_finished = false;
unsigned long test_start_time = 0;
const unsigned long TEST_TIMEOUT = 300000; // 5 minutes timeout
int out_of_thres_counter = 0;

// Init LED strips
#define R  255 // RGB configurations
#define G  255
#define B  31

const uint16_t nbPixels = 256 ; // number of led pixels per strip (32x8)

Adafruit_NeoPixel strip0 = Adafruit_NeoPixel(nbPixels, ledPin0, NEO_GRB + NEO_KHZ800);
Adafruit_NeoPixel strip1 = Adafruit_NeoPixel(nbPixels, ledPin1, NEO_GRB + NEO_KHZ800);
Adafruit_NeoPixel strip2 = Adafruit_NeoPixel(nbPixels, ledPin2, NEO_GRB + NEO_KHZ800);
Adafruit_NeoPixel strip3 = Adafruit_NeoPixel(nbPixels, ledPin3, NEO_GRB + NEO_KHZ800);

const uint32_t tempo = 100; // duration led is turned on

// Point tracker
const int numPoints = 40;
char click_tracker[numPoints];
int click_counter = 0;

void setup() {
  // Setup serial with higher baud rate for efficiency
  Serial.begin(115200);

  // Configure pins
  pinMode(button_pin, INPUT_PULLUP);
  // pinMode(laser_pin, OUTPUT);
  pinMode(led_pin, OUTPUT);

  // Init up LED strips
  strip0.begin();
  strip1.begin();
  strip2.begin();
  strip3.begin();

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

void lightUpLED(){
  int strip_idx = random(4);
  int i = random(256);

  if (strip_idx == 0){

    strip0.setPixelColor(i, strip0.Color(R, G, B));
    strip0.show(); // This sends the updated pixel color to the hardware.

    LED_strip_state = HIGH; 
    delay(tempo);
    strip0.clear();

    LED_strip_state = LOW;
  }

  else if (strip_idx == 1) {

    strip1.setPixelColor(i, strip1.Color(R, G, B));
    strip1.show(); // This sends the updated pixel color to the hardware.

    LED_strip_state = HIGH; 
    delay(tempo);
    strip1.clear();

    LED_strip_state = LOW;
  }

  else if (strip_idx == 2) {

    strip2.setPixelColor(i, strip2.Color(R, G, B));
    strip2.show(); // This sends the updated pixel color to the hardware.

    LED_strip_state = HIGH; 
    delay(tempo);
    strip2.clear();

    LED_strip_state = LOW;
  }

  else if (strip_idx == 3) {

    strip3.setPixelColor(i, strip3.Color(R, G, B));
    strip3.show(); // This sends the updated pixel color to the hardware.

    LED_strip_state = HIGH; 
    delay(tempo);
    strip3.clear();

    LED_strip_state = LOW;
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
  
  // Remove jittering
  delay(50);
}

void endTest(String reason) {
  // Turn off all outputs

  
  // laser_state = LOW;
  // laser_flag = LOW;

  LED_strip_state = LOW;

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

    // Select and light up LED
    lightUpLED();

    // Update timestamp
    timestamp = current_time;
  }

  // Button debounce and handling
  if ((current_time - last_debounce_time) > DEBOUNCE_DELAY) {
    if (reading != button_state) {
      button_state = reading;
    
      if (button_state == LOW) {
        // Serial.println("Pressed!");
        if (LED_strip_state == LOW) {
          // Wrong press, turn on buzzer
          // Serial.println("Wrong press!");
          //digitalWrite(buzzer_pin, HIGH);
          buzzer_state = HIGH;
          //buzzer_start_time = current_time;
        } 
        else {
          
          // Add click to click tracker
          click_tracker[point_tracker] = '1';
        }

        click_counter++;
      } 
    }
  }
  
}