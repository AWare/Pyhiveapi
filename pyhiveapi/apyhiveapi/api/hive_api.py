"""Hive API Module."""
# pylint: skip-file
import json

import requests
import urllib3
from pyquery import PyQuery

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)


class HiveApi:
    """Hive API Code."""

    def __init__(self, hiveSession=None, websession=None, token=None):
        """Hive API initialisation."""
        self.cameraBaseUrl = "prod.hcam.bgchtest.info"
        self.baseUrl = "https://beekeeper.hivehome.com/1.0"

        self.urls = {
            "properties": "https://sso.hivehome.com/",
            "login": "https://beekeeper.hivehome.com/1.0/cognito/login",
            "refresh": "https://beekeeper.hivehome.com/1.0/cognito/refresh-token",
            "long_lived": "https://api.prod.bgchprod.info/omnia/accessTokens",
            "weather": "https://weather.prod.bgchprod.info/weather",
            "holiday_mode": "/holiday-mode",
            "all": f"{self.baseUrl}/nodes/all",
            "alarm": f"{self.baseUrl}/security-lite",
            "cameraImages": f"https://event-history-service.{self.cameraBaseUrl}/v1/events/cameras?latest=true&cameraId={{0}}",
            "cameraRecordings": f"https://event-history-service.{self.cameraBaseUrl}/v1/playlist/cameras/{{0}}/events/{{1}}.m3u8",
            "devices": f"{self.baseUrl}/devices",
            "products": f"{self.baseUrl}/products",
            "actions": f"{self.baseUrl}/actions",
            "nodes": "/nodes/{0}/{1}",
        }
        self.timeout = 10
        self.json_return = {
            "original": "No response to Hive API request",
            "parsed": "No response to Hive API request",
        }
        self.session = hiveSession
        self.token = token

        self.homeID = None
        if self.session is not None:
            self.homeID = self.session.config.homeID

    def getParams(self, products=False, devices=False, actions=False):
        """Get parameters."""
        params = {
            "products": products,
            "devices": devices,
            "actions": actions,
        }
        if self.homeID is not None:
            params.update({"homeId": self.homeID})
        return params

    def getHomeIdParam(self):
        """Get homeId parameter if set."""
        if self.homeID is not None:
            return {"homeId": self.homeID}
        return {}

    def request(self, type, url, jsc=None, camera=False, params={}):
        """Make API request."""
        if self.session is not None:
            if camera:
                self.headers = {
                    "content-type": "application/json",
                    "Accept": "*/*",
                    "Authorization": f"Bearer {self.session.tokens.tokenData['token']}",
                    "x-jwt-token": self.session.tokens.tokenData["token"],
                }
            else:
                self.headers = {
                    "content-type": "application/json",
                    "Accept": "*/*",
                    "authorization": self.session.tokens.tokenData["token"],
                }
        else:
            if camera:
                self.headers = {
                    "content-type": "application/json",
                    "Accept": "*/*",
                    "Authorization": f"Bearer {self.token}",
                    "x-jwt-token": self.token,
                }
            else:
                self.headers = {
                    "content-type": "application/json",
                    "Accept": "*/*",
                    "authorization": self.token,
                }

        if type == "GET":
            return requests.get(
                url=url,
                headers=self.headers,
                data=jsc,
                timeout=self.timeout,
                params=params,
            )
        if type == "POST":
            return requests.post(
                url=url,
                headers=self.headers,
                data=jsc,
                timeout=self.timeout,
                params=params,
            )

    def refreshTokens(self, tokens={}):
        """Get new session tokens - DEPRECATED NOW BY AWS TOKEN MANAGEMENT."""
        url = self.urls["refresh"]
        if self.session is not None:
            tokens = self.session.tokens.tokenData
        jsc = (
            "{"
            + ",".join(
                ('"' + str(i) + '": ' '"' + str(t) + '" ' for i, t in tokens.items())
            )
            + "}"
        )
        try:
            info = self.request("POST", url, jsc)
            data = json.loads(info.text)
            if "token" in data and self.session:
                self.session.updateTokens(data)
                self.baseUrl = info["platform"]["endpoint"]
                self.cameraBaseUrl = info["platform"]["cameraPlatform"]
            self.json_return.update({"original": info.status_code})
            self.json_return.update({"parsed": info.json()})
        except (OSError, RuntimeError, ZeroDivisionError):
            self.error()

        return self.json_return

    def getLoginInfo(self):
        """Get login properties to make the login request."""
        url = self.urls["properties"]
        try:
            data = requests.get(url=url, verify=False, timeout=self.timeout)
            html = PyQuery(data.content)
            json_data = json.loads(
                '{"'
                + (html("script:first").text())
                .replace(",", ', "')
                .replace("=", '":')
                .replace("window.", "")
                + "}"
            )

            loginData = {}
            loginData.update({"UPID": json_data["HiveSSOPoolId"]})
            loginData.update({"CLIID": json_data["HiveSSOPublicCognitoClientId"]})
            loginData.update({"REGION": json_data["HiveSSOPoolId"]})
            return loginData
        except (OSError, RuntimeError, ZeroDivisionError):
            self.error()

    def getAll(self):
        """Build and query all endpoint."""
        json_return = {}
        url = self.urls["all"]
        params = self.getParams(
            products=True, devices=True, actions=True
        )
        try:
            info = self.request("GET", url, params=params)
            json_return.update({"original": info.status_code})
            json_return.update({"parsed": info.json()})
        except (OSError, RuntimeError, ZeroDivisionError):
            self.error()

        return json_return

    def getHomes(self):
        """Build and query all endpoint."""
        json_return = {}
        url = self.urls["all"]
        params = self.getParams()
        try:
            info = self.request("GET", url, params=params)
            all = info.json()
            json_return.update({"original": info.status_code})
            json_return.update({"parsed": all["homes"]})
        except (OSError, RuntimeError, ZeroDivisionError):
            self.error()

        return json_return

    def getAlarm(self, homeID=None):
        """Build and query alarm endpoint."""
        if self.session is not None:
            homeID = self.session.config.homeID
        url = self.urls["alarm"]
        params = {}
        if homeID:
            params = {"homeID": homeID}
        if self.homeID:
            # ignore homeID if set in session
            params = self.getHomeIdParam()
        try:
            info = self.request("GET", url, params=params)
            self.json_return.update({"original": info.status_code})
            self.json_return.update({"parsed": info.json()})
        except (OSError, RuntimeError, ZeroDivisionError):
            self.error()

        return self.json_return

    def getCameraImage(self, device=None, accessToken=None):
        """Build and query camera endpoint."""
        json_return = {}
        url = self.urls["cameraImages"].format(device["props"]["hardwareIdentifier"])
        try:
            info = self.request("GET", url, camera=True)
            json_return.update({"original": info.status_code})
            json_return.update({"parsed": info.json()})
        except (OSError, RuntimeError, ZeroDivisionError):
            self.error()

        return json_return

    def getCameraRecording(self, device=None, eventId=None):
        """Build and query camera endpoint."""
        json_return = {}
        url = self.urls["cameraRecordings"].format(
            device["props"]["hardwareIdentifier"], eventId
        )
        try:
            info = self.request("GET", url, camera=True)
            json_return.update({"original": info.status_code})
            json_return.update({"parsed": info.text.split("\n")[3]})
        except (OSError, RuntimeError, ZeroDivisionError):
            self.error()

        return json_return

    def getDevices(self):
        """Call the get devices endpoint."""
        url = self.urls["devices"]
        params = self.getParams(devices=True)
        try:
            response = self.request("GET", url, params=params)
            self.json_return.update({"original": response.status_code})
            self.json_return.update({"parsed": response.json()})
        except (OSError, RuntimeError, ZeroDivisionError):
            self.error()

        return self.json_return

    def getProducts(self):
        """Call the get products endpoint."""
        url = self.urls["products"]
        params = self.getParams(products=True)
        try:
            response = self.request("GET", url, params=params)
            self.json_return.update({"original": response.status_code})
            self.json_return.update({"parsed": response.json()})
        except (OSError, RuntimeError, ZeroDivisionError):
            self.error()

        return self.json_return

    def getActions(self):
        """Call the get actions endpoint."""
        url = self.urls["all"]
        params = self.getHomeIdParam()
        try:
            response = self.request("GET", url, params=params)
            all = response.json()
            self.json_return.update({"original": response.status_code})
            self.json_return.update({"parsed": all["actions"]})
        except (OSError, RuntimeError, ZeroDivisionError):
            self.error()

        return self.json_return

    def motionSensor(self, sensor, fromepoch, toepoch):
        """Call a way to get motion sensor info."""
        url = (
            self.urls["base"]
            + self.urls["products"]
            + "/"
            + sensor["type"]
            + "/"
            + sensor["id"]
            + "/events?from="
            + str(fromepoch)
            + "&to="
            + str(toepoch)
        )
        try:
            response = self.request("GET", url)
            self.json_return.update({"original": response.status_code})
            self.json_return.update({"parsed": response.json()})
        except (OSError, RuntimeError, ZeroDivisionError):
            self.error()

        return self.json_return

    def getWeather(self, weather_url):
        """Call endpoint to get local weather from Hive API."""
        t_url = self.urls["weather"] + weather_url
        url = t_url.replace(" ", "%20")
        try:
            response = self.request("GET", url)
            self.json_return.update({"original": response.status_code})
            self.json_return.update({"parsed": response.json()})
        except (OSError, RuntimeError, ZeroDivisionError, ConnectionError):
            self.error()

        return self.json_return

    def setHome(self, homeID):
        """Set the homeID."""
        self.homeID = homeID

    def setState(self, n_type, n_id, **kwargs):
        """Set the state of a Device."""
        jsc = (
            "{"
            + ",".join(
                ('"' + str(i) + '": ' '"' + str(t) + '" ' for i, t in kwargs.items())
            )
            + "}"
        )

        url = self.urls["base"] + self.urls["nodes"].format(n_type, n_id)

        try:
            response = self.request("POST", url, jsc)
            self.json_return.update({"original": response.status_code})
            self.json_return.update({"parsed": response.json()})
        except (OSError, RuntimeError, ZeroDivisionError, ConnectionError):
            self.error()

        return self.json_return

    def setAction(self, n_id, data):
        """Set the state of a Action."""
        jsc = data
        url = self.urls["base"] + self.urls["actions"] + "/" + n_id
        try:
            response = self.request("POST", url, jsc)
            self.json_return.update({"original": response.status_code})
            self.json_return.update({"parsed": response.json()})
        except (OSError, RuntimeError, ZeroDivisionError, ConnectionError):
            self.error()

        return self.json_return

    def error(self):
        """An error has occurred interacting with the Hive API."""
        self.json_return.update({"original": "Error making API call"})
        self.json_return.update({"parsed": "Error making API call"})


class UnknownConfig(Exception):
    """Unknown API config."""
