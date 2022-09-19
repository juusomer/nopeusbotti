import paho.mqtt.client as mqtt
from gql import Client, gql
from gql.transport.aiohttp import AIOHTTPTransport

ROUTE_GRAPHQL_URL = "https://api.digitransit.fi/routing/v1/routers/hsl/index/graphql"

MQTT_BROKER_URL = "mqtt.hsl.fi"
MQTT_BROKER_PORT = 8883
MQTT_KEEPALIVE = 60


def process_position_messages(on_connect, on_message):
    client = mqtt.Client()
    client.tls_set()
    client.on_connect = on_connect
    client.on_message = on_message
    client.connect(MQTT_BROKER_URL, MQTT_BROKER_PORT, MQTT_KEEPALIVE)
    client.loop_forever()


def get_route(route_number):
    query = gql(
        f"""
        {{
            routes(name: "{route_number}", transportModes: BUS) {{
                gtfsId
            }}
        }}
        """
    )
    transport = AIOHTTPTransport(url=ROUTE_GRAPHQL_URL)
    client = Client(transport=transport, fetch_schema_from_transport=True)
    return client.execute(query)
