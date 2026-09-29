from waam_slicer.klipper_client import KlipperClient


MOONRAKER_URL = "http://192.168.0.2:7125"


client = KlipperClient(
    MOONRAKER_URL
)


print("Connecting to Klipper...")


try:

    result = client.check_connection()

    print("Connection successful.")

    print(result)


except Exception as error:

    print("Connection failed.")

    print(error)