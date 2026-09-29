import requests


class KlipperClient:

    def __init__(self, base_url, timeout=120):
        """
        Create a connection object for Moonraker.

        Example:
            http://192.168.0.2:7125
        """

        self.base_url = base_url.rstrip("/")
        self.timeout = timeout


    def check_connection(self):
        """
        Test whether Moonraker is reachable.
        Does NOT move the machine.
        """

        url = self.base_url + "/printer/info"

        response = requests.get(
            url,
            timeout=5
        )

        response.raise_for_status()

        return response.json()


    def run_gcode(self, script):
        """
        Send G-code or a Klipper macro through Moonraker.
        """

        url = self.base_url + "/printer/gcode/script"

        response = requests.post(
            url,
            json={
                "script": script
            },
            timeout=self.timeout
        )

        response.raise_for_status()

        data = response.json()

        if "error" in data:
            raise RuntimeError(
                f"Klipper error: {data['error']}"
            )

        return data


    def get_last_probe_position(self):
        """
        Read the most recent probe contact position.

        Expected result:
            X
            Y
            Z

        Z is used as pTouch.
        """

        url = self.base_url + "/printer/objects/query"

        response = requests.post(
            url,
            json={
                "objects": {
                    "probe": [
                        "last_probe_position"
                    ]
                }
            },
            timeout=10
        )

        response.raise_for_status()

        data = response.json()

        try:

            position = (
                data["result"]
                ["status"]
                ["probe"]
                ["last_probe_position"]
            )

        except KeyError:

            raise RuntimeError(
                "Klipper did not return "
                "probe.last_probe_position"
            )

        if position is None:

            raise RuntimeError(
                "No probe result is available yet. "
                "Run LAYER_TOUCH or PROBE_BASE first."
            )


        # Depending on the returned format,
        # position may be a list [X,Y,Z]
        # or a dictionary.
        if isinstance(position, dict):

            x = float(position["x"])
            y = float(position["y"])
            z = float(position["z"])

        else:

            x = float(position[0])
            y = float(position[1])
            z = float(position[2])


        return {
            "x": x,
            "y": y,
            "z": z
        }