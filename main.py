# -*- coding: utf-8 -*-
"""
Created on Sun Feb 25 10:07:22 2024

@author: founta
"""

import json, time, sanic, os
from sanic import response
from sanic.log import logger

from pathlib import Path
from threading import Thread
from websockets.sync.client import connect

from pythonosc import udp_client

access_token = None
hr = None
hr_prefix="♡  "
text_extra=""
text_lifetime=0
text_expire_time=None
stop = False
update_interval=5 #s
user_updated=False
osc_udp = udp_client.SimpleUDPClient("127.0.0.1", 9000)

web_app = sanic.Sanic("vrchat_heartrate_sender")

exe_path = Path(os.getcwd())
config_fname = exe_path / "hr_save.json"

def flush_config():
    global config_fname, access_token, update_interval, hr_prefix
    with open(config_fname, "w") as f:
        if access_token is None:
            access_token = ""
        f.write(json.dumps({"access_token": access_token, "update_interval": update_interval, "hr_prefix": hr_prefix}, indent=2))
        print("wrote config file to %s" % (str(config_fname)))

def send_text_to_vrc(text):
    global osc_udp
    osc_udp.send_message("/chatbox/input", [text, True, False]) #text, send now, notification

def vrchat_textbox_updater():
    global stop,hr,update_interval,user_updated,text_extra,text_expire_time
    while not stop:
        text = ""
        if hr is not None:
            text += "%s%d" % (hr_prefix, hr)
        if len(text_extra):
            text += "\n" + text_extra
        if len(text):
            logger.info("Sent '%s' to VRC OSC!" % (text))
            send_text_to_vrc(text)
        
        iter_sleep = update_interval / 20
        sleep_end = time.time() + update_interval
        while time.time() < sleep_end:
            if user_updated:
                user_updated = False
                break
            if text_expire_time is not None and text_expire_time != 0:
                if time.time() > text_expire_time:
                    text_expire_time = None
                    text_extra = ""
                    break
            time.sleep(iter_sleep)

def read_hr_target():
    global stop,hr,access_token
    while access_token is None and not stop:
        time.sleep(1)
    url = "wss://dev.pulsoid.net/api/v1/data/real_time?access_token=%s" % \
        (access_token)
    if access_token is not None and not stop:
        logger.info("Connecting to pulsoid...")
        with connect(url) as ws:
            logger.info("connected to pulsoid!")
            while not stop:
                msg = ws.recv()
                try:
                    msg_json = json.loads(msg)
                except json.JSONDecodeError:
                    logger.error("could not parse pulsoid message!")
                hr = msg_json["data"]["heart_rate"]
                logger.info("Read a heartrate of %d from pulsoid!" % (hr))

def check_args(request, expected_key):
    args = None
    good = True
    try:
        args = json.loads(request.body)
    except json.JSONDecodeError:
        logger.error("unable to parse request arguments")
        good = False
    if expected_key not in args.keys():
        logger.error("malformed request -- missing key %s" % (expected_key))
        good = False
    return good, args[expected_key]
    
@web_app.route("/api/update_text", methods=["POST"])
async def update_text(request):
    global user_updated, text_extra, text_lifetime, text_expire_time
    global update_interval, hr_prefix
    ok1, text = check_args(request, "text_extra")
    ok2, lifetime = check_args(request, "text_lifetime")
    ok3, interval = check_args(request, "update_interval")
    ok4, prefix = check_args(request, "hr_prefix")
    
    do_config_update = False

    if ok2:
        text_lifetime = float(lifetime)
        user_updated = True
    else:
        logger.warn("update text could not update text lifetime")

    if ok3:
        if (update_interval != float(interval)):
            do_config_update = True
        update_interval = float(interval)
        user_updated = True
    else:
        logger.warn("update text could not update interval")

    if ok3:
        if hr_prefix != prefix:
            do_config_update = True
        hr_prefix = prefix
        user_updated = True
    else:
        logger.warn("update text could not update prefix")

    if ok1:
        text_extra = text
        if text_lifetime == 0:
            text_expire_time = None
        else:
            text_expire_time = time.time() + text_lifetime
        user_updated = True
    else:
        logger.warn("update text could not update text")
    
    logger.info("Updated text and such")
    if do_config_update:
        flush_config()
    return response.empty(status=200)

@web_app.route("/api/update_token", methods=["POST"])
async def update_token(request):
    global access_token
    ok, value = check_args(request, "access_token")
    if ok:
        access_token = value
    else:
        logger.error("update token could not validate args")
    logger.info("Updated pulsoid access token! to %s" % (access_token))
    flush_config()
    return response.empty(status=200)

@web_app.route("/", methods=["GET"])
async def splash(request):
    html = """<!DOCTYPE html>
    <html lang="en" dir="ltr">
	<head>
		<meta charset="utf-8">
	</head>
	<body>
    <script>
        function update_token()
        {
          var token_field = document.getElementById("access_token")
          
          var http = new XMLHttpRequest();
          http.open("POST", window.location.protocol + "//" + window.location.host + "/api/update_token", false);
          http.setRequestHeader("Content-type", "application/json")
          
          var send_payload = {"access_token":token_field.value}
          http.send(JSON.stringify(send_payload));
        }
        
        function update_text()
        {
          var text_extra = document.getElementById("text_extra")
          var hr_prefix = document.getElementById("hr_prefix")
          var update_interval = document.getElementById("update_interval")
          var text_lifetime = document.getElementById("text_lifetime")

          var http = new XMLHttpRequest();
          http.open("POST", window.location.protocol + "//" + window.location.host + "/api/update_text", false);
          http.setRequestHeader("Content-type", "application/json")
          
          var send_payload = {"text_extra":text_extra.value, "hr_prefix":hr_prefix.value, "update_interval":update_interval.value, "text_lifetime":text_lifetime.value}
          http.send(JSON.stringify(send_payload));
        }
    </script>
    
    <label for="access_token">Pulsoid access token</label>
    <input type="password" id="access_token" name="Access token" value="%s"/><br>
    <button type="button" id="update_access_token" onclick="update_token()">Update pulsoid access token</button><br><br>
    

    <label for="hr_prefix">Heart rate prefix text</label>
    <input type="text" id="hr_prefix" name="Heart rate prefix text" value="%s"/><br>
    
    <label for="update_interval">VRC text update interval, in seconds</label>
    <input type="number" id="update_interval" name="Heart rate update interval (seconds)" value="%f"/><br><br>
    
    <label for="text_extra">Extra text to append under the heart rate</label>
    <input type="text" id="text_extra" name="Extra message to append under the heart rate" value=""/><br>
    
    <label for="text_lifetime">How long to display the extra text for (in seconds). 0 for infinite</label>
    <input type="number" id="text_lifetime" name="text_lifetime" value="0"/><br>
    <button type="button" id="update" onclick="update_text()">Update text</button>
    
""" % (access_token if access_token is not None else "", hr_prefix, update_interval)
    logger.info("Served splash screen...")
    return response.html(html)

def if_present(key, conf):
    if key in conf.keys():
        return conf[key]

if __name__ == "__main__":
    print("trying to read config file at %s" % (str(config_fname)))
    if config_fname.exists():
        try:
            with open(config_fname, "r") as f:
                config = json.load(f)
                access_token = if_present("access_token", config)
                if access_token == "":
                    access_token = None
                update_interval = if_present("update_interval", config)
                hr_prefix = if_present("hr_prefix", config)
        except:
            print("Unable to load configuration file, proceeding with defaults")
    else:
        print("configuration file not found! proceeding with defaults")

    hr_thd = Thread(target=read_hr_target)
    hr_thd.start()
    
    vrc_update_thread = Thread(target=vrchat_textbox_updater)
    vrc_update_thread.start()


    web_app.run(host="localhost", port=9999, debug=False, access_log=False, single_process=True)

    stop = True
    hr_thd.join()
    vrc_update_thread.join()
    web_app.stop()
    
    flush_config()