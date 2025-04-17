from broadcaster import Broadcast
from dotenv import dotenv_values

db_url = dotenv_values('.env')['DATABASE_URL']
# Strip unsupported psycopg suffix for broadcaster
broker_url = db_url.replace('+psycopg', '')
broadcast = Broadcast(broker_url)
