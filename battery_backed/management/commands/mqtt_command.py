from typing import Any, Optional
from django.core.management.base import BaseCommand
from battery_backed.models import BatteryLiveStatus
from datetime import datetime
from pytz import timezone
import paho.mqtt.client as mqtt
import json


class Command(BaseCommand):
    help = 'MQTT Processing'

    def validate_json(self, json_data: str) -> bool:
        try:
            json.loads(json_data)
            return True
        except ValueError:
            return False
        
    def handle(self, *args: Any, **options: Any) -> Optional[str]:   

        def on_connect(client, userdata, flags, rc):           
            if rc == 0:
                print("Connected successfully")
                client.subscribe("battery_scada/#")
            else:
                print(f"Connection failed with code {rc}")

        def on_message(client, userdata, msg):            
            topic = msg.topic
            print(f"Received message on topic: {topic}")
            
            # Assuming payload is already a dictionary-like object (not a JSON string)
            try:
                payload_str = msg.payload.decode()  # Decode bytes to string
                

                # Check if payload looks like a dictionary in string form, if so, evaluate it
                # Use `json.loads()` if it was a JSON-encoded string, but seems like it's Python serialized.
                # If it is indeed a dictionary-like payload, use `eval()`, but be careful with it!
                data_out = eval(payload_str)  # In a safe environment, consider using literal_eval from ast
                print(f"Evaluated payload: {data_out}")

                if isinstance(data_out, dict):
                    dev_id = data_out.get('devId', None)                   
                    soc = data_out.get('soc', None)
                    flow_last_min = data_out.get('flow_last_min', None)
                    invertor = data_out.get('invertor', None)
                    timestamp = data_out.get('timestamp', None)
                    print(f"SOC:{soc}, flow: {flow_last_min}, inv: {invertor}")
                    if dev_id is not None and soc is not None and flow_last_min is not None and invertor is not None and timestamp is not None:        
                                                           
                        battery = BatteryLiveStatus(  
                            timestamp=timestamp,
                            devId=dev_id,                           
                            state_of_charge=soc, 
                            flow_last_min= flow_last_min, 
                            invertor_power= invertor
                        )
                        print(battery)
                        battery.save()


            except Exception as e:
                print(f"Error processing the payload: {e}")

                  
        client = mqtt.Client()
        client.on_connect = on_connect
        client.on_message = on_message

        client.connect("159.89.103.242", 1883)        

        client.loop_forever()