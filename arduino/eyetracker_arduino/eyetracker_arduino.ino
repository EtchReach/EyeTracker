#include <Servo.h>
#include <ArduinoJson.h>
#include <Adafruit_NeoPixel.h>

// Pin definitions

const int led_pin = 3;
const int button_pin = 7;   // Active high, connect other end into ground


const byte ledPin0 =  10;  // led data pubs
const byte ledPin1 =  11;    
// const byte ledPin2 =  12;
// const byte ledPin3 =  13;

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
const unsigned long START_DELAY_MS = 2000;
const unsigned long RESPONSE_WINDOW_MS = 2000;
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
unsigned long stimulus_end_time = 0;
unsigned long response_window_end_time = 0;
unsigned long next_point_delay = point_duration;

// Test state variables
bool test_running = false;
bool test_finished = false;
bool response_window_active = false;
bool point_answered = false;
unsigned long test_start_time = 0;
const unsigned long TEST_TIMEOUT = 300000; // 5 minutes timeout
int out_of_thres_counter = 0;
int active_strip_idx = -1;

// Init LED strips
#define R  255 // RGB configurations
#define G  255
#define B  31

const uint16_t nbPixels = 512 ; // number of led pixels per strip (32x8)

Adafruit_NeoPixel strip0 = Adafruit_NeoPixel(nbPixels, ledPin0, NEO_GRB + NEO_KHZ800);
Adafruit_NeoPixel strip1 = Adafruit_NeoPixel(nbPixels, ledPin1, NEO_GRB + NEO_KHZ800);
// Adafruit_NeoPixel strip2 = Adafruit_NeoPixel(nbPixels, ledPin2, NEO_GRB + NEO_KHZ800);
// Adafruit_NeoPixel strip3 = Adafruit_NeoPixel(nbPixels, ledPin3, NEO_GRB + NEO_KHZ800);

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

void clearActiveLED() {
  if (active_strip_idx == 0) {
    strip0.clear();
    strip0.show();
  } else if (active_strip_idx == 1) {
    strip1.clear();
    strip1.show();
  }

  active_strip_idx = -1;
  LED_strip_state = LOW;
}

void lightUpLED(){
  clearActiveLED();

  int strip_idx = random(2);
  int i = random(nbPixels);

  if (strip_idx == 0){
    strip0.setPixelColor(i, strip0.Color(R, G, B));
    strip0.show(); // This sends the updated pixel color to the hardware.
  }
  else if (strip_idx == 1) {
    strip1.setPixelColor(i, strip1.Color(R, G, B));
    strip1.show(); // This sends the updated pixel color to the hardware.
  }

  active_strip_idx = strip_idx;
  LED_strip_state = HIGH;
}

void updateStimulusState(unsigned long current_time) {
  if (LED_strip_state == HIGH && current_time >= stimulus_end_time) {
    clearActiveLED();
  }

  if (response_window_active && current_time >= response_window_end_time) {
    response_window_active = false;
  }
}

void startTest() {
  Serial.println("Test starting...");
  test_running = true;
  test_finished = false;
  test_start_time = millis();
  timestamp = millis();
  next_point_delay = START_DELAY_MS;
  
  // Reset all counters and states
  point_tracker = -1;
  click_counter = 0;
  out_of_thres_counter = 0;
  response_window_active = false;
  point_answered = false;
  stimulus_end_time = 0;
  response_window_end_time = 0;
  clearActiveLED();
  
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

  response_window_active = false;
  point_answered = false;
  clearActiveLED();

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

  updateStimulusState(current_time);

  if (reading != last_button_state) {
    last_debounce_time = current_time;
    last_button_state = reading;
  }

  if (duration > next_point_delay) {
    // Update point_tracker to the next point
    point_tracker++;

    // Check if we've completed a full cycle and end the test
    if (point_tracker >= numPoints) {
      endTest("Test completed successfully");
      return;
    }

    // Select and light up LED
    lightUpLED();
    stimulus_end_time = current_time + tempo;
    response_window_active = true;
    response_window_end_time = current_time + RESPONSE_WINDOW_MS;
    point_answered = false;
    next_point_delay = point_duration;

    // Update timestamp
    timestamp = current_time;
  }

  // Button debounce and handling
  if ((current_time - last_debounce_time) > DEBOUNCE_DELAY) {
    if (reading != button_state) {
      button_state = reading;
    
      if (button_state == LOW) {
        click_counter++;

        if (response_window_active && !point_answered && point_tracker >= 0) {
          click_tracker[point_tracker] = '1';
          point_answered = true;
          Serial.println("PRESS_CORRECT");
        } 
        else {
          buzzer_state = HIGH;
          Serial.println("PRESS_WRONG");
        }
      } 
    }
  }
  
}
