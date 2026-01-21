import time
import sys
import serial
import serial.tools.list_ports
import json

class ArduinoTracker:
    """Handles connection and communication with Arduino hardware."""
    
    # Command bytes for efficient serial communication (single-byte)
    CMD_START_TEST = b'\x01'      # Start test (0x01)
    CMD_END_TEST = b'\x02'        # End test (0x02)
    CMD_PING = b'\x03'            # Ping signal to check connection (0x03)
    CMD_WITHIN_THRESHOLD = b'\x04'  # Within threshold signal (0x04)
    CMD_OUT_OF_THRESHOLD = b'\x05'  # Out of threshold signal (0x05)
    CMD_TEST_RESULTS = b'\x06'  # Check test status: Ready, Running, Ended (0x06)
    
    # Response codes from Arduino
    RESP_ACK = 'O'           # Command acknowledged
    RESP_TEST_START = "Test starting..."
    RESP_TEST_END = "TEST_END"
    RESP_SYSTEM_ONLINE = "Online"
    RESP_SYSTEM_READY = "Ready"
    RESP_SYSTEM_NOT_READY = "Running"
    
    def __init__(self, auto_connect=True, baud_rate=115200, timeout=2, on_detect_callback=None, port_identifiers=None):
        """Initialize the Arduino tracker.
        
        Args:
            auto_connect: If True, try to auto-connect to Arduino
            baud_rate: Baud rate for serial communication
            timeout: Serial connection timeout in seconds
            on_detect_callback: Callback function called when multiple ports are detected
                                Function signature: callback(ports) -> selected_port
            port_identifiers: List of strings to identify Arduino ports
        """
        self.arduino = None
        self.baud_rate = baud_rate
        self.timeout = timeout
        self.port_identifiers = port_identifiers or ['arduino', 'uno', 'usbserial'] # NOTE: no longer used, we're looking at VID to ident arduinos instead of description
        self.is_test_running = False
        self.test_results = None
        self.prev_command = None
        
        # If auto_connect is enabled, try to connect automatically
        if auto_connect:
            success, message = self.try_connect(on_detect_callback)
            if success:
                print(f"Auto-connected: {message}")
            else:
                print(f"Auto-connect failed: {message}")
    
    def try_connect(self, on_detect_callback=None):
        """Try to connect to Arduino, handling port detection and selection.
        
        Args:
            on_detect_callback: Callback function for port selection
            
        Returns:
            tuple: (success, message)
        """
        ports = self.detect_arduino_ports()
        
        if not ports:
            return False, "No Arduino devices detected"
        
        if len(ports) == 1:
            # Only one port found, connect automatically
            port = ports[0]['port']
            success = self.connect_to_port(port)
            
            if success:
                return True, f"Connected to Arduino at {port}"
            else:
                return False, f"Failed to connect to Arduino at {port}"
        else:
            # Multiple ports found, let user select
            if on_detect_callback:
                selected_port = on_detect_callback(ports)
                if selected_port:
                    success = self.connect_to_port(selected_port)
                    if success:
                        return True, f"Connected to Arduino at {selected_port}"
                    else:
                        return False, f"Failed to connect to Arduino at {selected_port}"
                else:
                    return False, "No port selected"
            else:
                # Default to first port if no callback
                port = ports[0]['port']
                success = self.connect_to_port(port)
                
                if success:
                    return True, f"Connected to Arduino at {port} (default selection)"
                else:
                    return False, f"Failed to connect to Arduino at {port} (default selection)"

    def detect_arduino_ports(self):
        """Detect available Arduino serial ports.
        
        Returns:
            list: List of potential Arduino serial ports
        """
        arduino_ports = []
        
        port_info_list = list(serial.tools.list_ports.comports())
        print(f"Available ports: {len(port_info_list)}")

        for port_info in port_info_list:
            port_device = port_info.device
            port_description = port_info.description.lower()
            
            # Debug output
            print(f"Port: {port_device}, Description: {port_description}, HWID: {port_info.hwid}, Product: {port_info.product}, manu: {port_info.manufacturer}, vid: {port_info.vid}")
            
            # Check if any identifier matches the port description
            # if any(identifier in port_description for identifier in self.port_identifiers):
            #     arduino_ports.append({
            #         'port': port_device,
            #         'description': port_info.description
            #     })
            if port_info.vid==6790:
                arduino_ports.append({
                    'port': port_device,
                    'description': port_info.description
                })
        
        return arduino_ports

    def connect_to_port(self, port):
        """Connect to Arduino at specified port.
        
        Args:
            port: Serial port to connect to
            
        Returns:
            bool: True if connection successful, False otherwise
        """
        try:
            self.arduino = serial.Serial(port, self.baud_rate, timeout=self.timeout)
            time.sleep(2)  # Allow time for Arduino reset
            
            # Test connection by pinging
            if not self.ping():
                print("Failed to verify connection with ping")
                self.disconnect()
                return False
        
            else:
                print("Connection verified with ping")
                return True
                
        except serial.SerialException as e:
            print(f"Connection error: {e}")
            self.arduino = None
            return False

    def ping(self):
        """Ping Arduino to verify connection.
        
        Returns:
            bool: True if ping successful, False otherwise
        """
        if not self.is_connected():
            return False
            
        try:
            # Clear buffers
            self.arduino.reset_input_buffer()
            self.arduino.reset_output_buffer()
            
            # Send ping command
            self.arduino.write(self.CMD_PING)
            self.arduino.flush()
            
            # Wait for response
            start_time = time.time()
            while time.time() - start_time < 2:
                if self.arduino.in_waiting > 0:
                    response = self.arduino.readline().decode('utf-8', errors='ignore').strip()
                    return response
                time.sleep(0.1)
                
            return False
            
        except serial.SerialException as e:
            print(f"Ping error: {e}")
            return False

    def is_connected(self):
        """Check if Arduino is connected.
        
        Returns:
            bool: True if connected, False otherwise
        """
        return self.arduino is not None and self.arduino.is_open
    
    def disconnect(self):
        """Disconnect from Arduino."""
        try:
            if self.arduino and self.arduino.is_open:
                self.arduino.close()
        except serial.SerialException as e:
            print(f"Error during disconnect: {e}")
        finally:
            self.arduino = None
            self.is_test_running = False

    def send_command(self, command):
        """Send command to Arduino and verify acknowledgment.
        
        Args:
            command: Command to send
            
        Returns:
            int: 1 if successful, 0 if failed, 2 if special response received
        """
        if not self.is_connected():
            print("Cannot send command: Not connected to Arduino")
            return 0
            
        # Convert command to bytes if it's a string
        if isinstance(command, str):
            if command == 'H':
                command = self.CMD_OUT_OF_THRESHOLD
            elif command == 'L':
                command = self.CMD_WITHIN_THRESHOLD
            else:
                print(f"Unknown command sent: {command}")
                return 0
            
        try:
            self.arduino.write(command)
            self.arduino.flush()
            self.prev_command = command
            return 1
        except serial.SerialException as e:
            print(f"Error sending command: {e}")
            return 0
        
    
    def check_ack(self):
        """Non-blocking check for Arduino acknowledgment."""
        if not self.is_connected():
            return 0
            
        try:
            if self.arduino.in_waiting > 0:
                response = self.arduino.read(1)
                if response == self.RESP_ACK:
                    return 1
                else:
                    return 2
            return 0
        except serial.SerialException as e:
            print(f"Error checking acknowledgment: {e}")
            return 0

    def start_test(self):
        """Start the test sequence on Arduino.
        
        Returns:
            bool: True if command acknowledged, False otherwise
        """
        if not self.is_connected():
            print("Cannot start test: Not connected to Arduino")
            return False
            
        try:
            # Ping to check test status and system state
            status = self.ping()
            print("ping status ", status)
            if self.RESP_SYSTEM_NOT_READY in status:
                self.stop_test()
        
            # Clear input buffer
            self.arduino.reset_input_buffer()
            self.arduino.reset_output_buffer()
            
            # Send start test command
            self.arduino.write(self.CMD_START_TEST)
            self.arduino.flush()
            
            # Wait for confirmation
            start_time = time.time()
            while time.time() - start_time < 2:
                if self.arduino.in_waiting > 0:
                    response = self.arduino.readline().decode('utf-8', errors='ignore').strip()
                    print(f"Start test response: {response}")
                    if self.RESP_TEST_START in response:
                        self.is_test_running = True
                        self.test_results = None
                        return True
                else:
                    print("no inwaiting ")

                time.sleep(0.1)
                
            print("No or wrong response received for start test command")
            return False
            
        except serial.SerialException as e:
            print(f"Error starting test: {e}")
            return False

    def stop_test(self):
        """Stop the current test.
        
        Returns:
            bool: True if command acknowledged, False otherwise
        """
        if not self.is_connected():
            print("Cannot stop test: Not connected")
            return False
            
        try:
            # Send end test command
            self.arduino.write(self.CMD_END_TEST)
            self.arduino.flush()
            
            # Wait for confirmation
            start_time = time.time()
            test_ended = False
            
            while time.time() - start_time < 3:
                if self.arduino.in_waiting > 0:
                    response = self.arduino.readline().decode('utf-8', errors='ignore').strip()
                    print(f"Stop test response: {response}")
                    if self.RESP_TEST_END in response:
                        test_ended = True
                        break
                time.sleep(0.1)
            
            # Mark test as not running
            self.is_test_running = False
            
            return test_ended
            
        except serial.SerialException as e:
            print(f"Error stopping test: {e}")
            return False

    def get_test_results(self, timeout=5):
        """Get results from the completed test.
        
        Args:
            timeout: Maximum time to wait for results in seconds
            
        Returns:
            dict: Test results including reason, click_counter, and click_tracker
                  or None if no results available
        """
        if not self.is_connected():
            print("Cannot get test results: Not connected to Arduino")
            return None
        
        # If we already have results, return them
        if self.test_results:
            return self.test_results
        
        try:
            # Ping to check test status and system state
            status = self.ping()
            print("status ", status)
            if self.RESP_SYSTEM_NOT_READY in status:
                print("System not ready!")
                return None
            elif self.RESP_SYSTEM_ONLINE in status: 
                print("No test initiated!")
                return None              
        
            # Clear input buffer
            self.arduino.reset_input_buffer()
            
            # Send start test command
            self.arduino.write(self.CMD_TEST_RESULTS)
            self.arduino.flush()
        
            # Wait for results up to timeout
            start_time = time.time()
            while time.time() - start_time < timeout:
                if self.arduino.in_waiting > 0:
                    line = self.arduino.readline().decode('utf-8', errors='ignore').strip()
                    print(f"Results line: {line}")

                    if line.startswith("{") and line.endswith("}"):
                        try:
                            data = json.loads(line)
                            return data
                        except json.JSONDecodeError:
                            print(f"JSON decode error: {line}")
                            return None
                            
                time.sleep(0.1)

        except serial.SerialException as e:
            print(f"Error stopping test: {e}")
            return None

        print(f"Timed out waiting for test results after {timeout} seconds")
        return None

    def read_available_data(self):
        """Read and return any available data from Arduino.
        
        Returns:
            list: List of lines received from Arduino, or empty list if none
        """
        if not self.is_connected():
            return []
            
        lines = []
        try:
            while self.arduino.in_waiting > 0:
                line = self.arduino.readline().decode('utf-8', errors='ignore').strip()
                if line.startswith("{") and line.endswith("}"):
                    json_data = json.loads(line)
                    lines.append(json_data)
                else:
                    lines.append(line)
        except serial.SerialException as e:
            print(f"Error reading data: {e}")
            
        return lines

    def check_connection(self):
        """Check if Arduino is still responding.
        
        Returns:
            bool: True if responding, False otherwise
        """
        if not self.ping():
            return False
        else:
            return True
        
    def get_test_status(self):
        """Check if test is still ongoing, and retrieve current test info."""
        if not self.is_connected():
            return {'test_status': 'Not connected'}

        try:
            # Read all available lines first
            lines = []
            while self.arduino.in_waiting > 0:
                line = self.arduino.readline().decode('utf-8', errors='ignore').strip()
                if line:  # Only add non-empty lines
                    lines.append(line)
            
            # NOW clear the buffers after reading everything
            self.arduino.reset_input_buffer()
            self.arduino.reset_output_buffer()
            
            if not lines:
                return {'test_status': "No response"}
            
            # print("lines:", lines)
                
            # Process lines - prioritize TEST_END messages
            test_end_found = False
            latest_status = None
            
            for line in lines:
                if self.RESP_TEST_END in line:
                    test_end_found = True
                elif self.RESP_SYSTEM_READY in line:
                    latest_status = {'test_status': 'Ready'}
                elif line.startswith("{") and line.endswith("}"):
                    try:
                        data = json.loads(line)
                        latest_status = data
                        # print("data from get test status ", data)
                    except json.JSONDecodeError:
                        print(f"JSON decode error: {line}")
            
            # Return TEST_END status if found, otherwise return latest status
            if test_end_found:
                self.is_test_running = False
                return {'test_status': 'Finished'}
            
            # print('latest_status', latest_status)
            return latest_status or {'test_status': "No valid response"}

        except serial.SerialException as e:
            print(f"Ping error: {e}")
            return {'test_status': "Serial error"}


def select_port_menu(ports):
    """Display a menu for selecting a port.
    
    Args:
        ports: List of port dictionaries with 'port' and 'description' keys
        
    Returns:
        str: Selected port or None if cancelled
    """
    if not ports:
        print("No Arduino ports detected")
        return None
        
    print("\nAvailable Arduino ports:")
    for i, port_info in enumerate(ports):
        print(f"{i+1}. {port_info['port']} - {port_info['description']}")
    
    try:
        choice = int(input(f"Select port (1-{len(ports)}, or 0 to cancel): "))
        if 1 <= choice <= len(ports):
            return ports[choice-1]['port']
        else:
            return None
    except ValueError:
        print("Invalid input")
        return None


if __name__ == "__main__":
    # Create Arduino tracker with manual port selection
    tracker = ArduinoTracker(auto_connect=False)
    
    # Try to connect with port selection menu
    success, message = tracker.try_connect(select_port_menu)
    
    if not success:
        print(f"Failed to connect: {message}")
        sys.exit(1)
        
    print(message)
    
    # Basic interactive command menu
    print("\nCommand Menu:")
    print("S - Start test")
    print("E - End test")
    print("H - Send HIGH signal (LED ON)")
    print("L - Send LOW signal (LED OFF)")
    print("R - Read data")
    print("0 - Send within threshold")
    print("1 - Send out of threshold")
    print("Q - Quit")
    
    prev_command = None
    
    while True:
        command = input("\nEnter command: ").strip().upper()
        
        if command == 'Q':
            break
        elif command == 'S':
            if tracker.start_test():
                print("Test started successfully")
            else:
                print("Failed to start test")
        elif command == 'E':
            if tracker.stop_test():
                results = tracker.get_test_results()
                if results:
                    print(f"Test results: {results}")
                else:
                    print("No test results available")
            else:
                print("Failed to stop test")
        elif command == 'R':
            lines = tracker.read_available_data()
            if lines:
                print(f"Received data: {lines}")
            else:
                print("No data available")
        elif command in ['H', 'L', '0', '1']:
            cmd_map = {
                '0': tracker.CMD_WITHIN_THRESHOLD,
                '1': tracker.CMD_OUT_OF_THRESHOLD
            }
            
            result = tracker.send_command(cmd_map[command])
            
            if result == 1:
                print(f"Command {command} sent and acknowledged")
                prev_command = cmd_map[command]
            elif result == 2:
                print("Program ended by Arduino")
                break
            else:
                print(f"Failed to send command {command}")
        else:
            print("Invalid command")
    
    # Clean up on exit
    tracker.disconnect()
    print("Disconnected from Arduino")