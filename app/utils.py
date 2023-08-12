import pytz
from datetime import datetime

def convert_time_utc_to_local(timezone, data):
    if data is not None:
        # print("DATA ::", data)
        utc_datetime = datetime.strptime(data, "%Y-%m-%dT%H:%M:%SZ")
        # print("utc_datetime",utc_datetime)
        target_timezone = pytz.timezone(timezone)
        # print("target_timezone",target_timezone)
        converted_time = utc_datetime.replace(tzinfo=pytz.utc).astimezone(target_timezone)
        # print("converted_time",converted_time)
        final_time = converted_time.strftime("%Y-%m-%dT%H:%M:%SZ")
        # print("final_time",final_time)

        return final_time
