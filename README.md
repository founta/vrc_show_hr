# VRC heartrate sender
This project retrieves your heart rate from Pulsoid and sends it to VR chat's text box. It is controlled by a web UI and also allows sending other text via the web UI.

Double click the executable to run, and close the window it opens up to stop the program. It will save a configuration file in the same folder the .exe is located (it saves the file in the current working directory)

1. Download the executable from the releases page
2. Run the executable and navigate to http://localhost:9999
3. Create an authentication token at https://pulsoid.net/ui/keys. No pulsoid subscription is required
4. Copy the token and paste it into the "Pulsoid access token" field on the web UI and press the "Update pulsoid access token" button

