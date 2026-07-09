from datetime import datetime

def current_time():

    now = datetime.now()

    return now.strftime("The current time is %I:%M %p")
