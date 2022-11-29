import urllib3
from bs4 import BeautifulSoup

class Oauth():
    def __init__(self, client, env, user_name):
        self.client = client
        self.env = env
        self.user_name = user_name

    def do_login(self, response):
        if "Log in with OpenShift" in response.text:
            response = self._do_login_with_openshift(response)
            if response is False:
                return False

        response = self._do_login_with(response, self.env.IDP_NAME)
        if response is False:
            return False

        response = self._do_log_in_to_your_account(response, self.user_name, self.env.USER_PASSWORD)
        if response is False:
            return False

        if "Authorize" in response.text:
            response = self._do_authorize_service_account(response)
            if response is False:
                return False

        return response

    def _do_login_with_openshift(self, response):
        print("Log in with OpenShift")
        #
        # Page: Log in with OpenShift
        #
        soup = BeautifulSoup(response.text, features="lxml")
        action = soup.body.find("form").get("action")

        return self.client.get(action, params={"rd":"/"}, name=action)

    def _do_login_with(self, response, method):
        print("Log in with ...")
        #
        # Page: Log in with ...
        #
        url = urllib3.util.url.parse_url(response.url)
        oauth_host = f"{url.scheme}://{url.netloc}"

        soup = BeautifulSoup(response.text, features="lxml")
        for auth_type in soup.find_all("a"):
            if auth_type.text != method: continue
            action = auth_type.get("href")
            break
        else:
            print("FAILED")
            return False

        return self.client.get(oauth_host + action, name=action.partition("?")[0])


    def _do_log_in_to_your_account(self, response, username, password):
        print("Log in to your account")
        #
        # Page: Log in to your account
        #
        soup = BeautifulSoup(response.text, features="lxml")
        form = soup.body.find("form")
        action = form.get("action")

        url = urllib3.util.url.parse_url(response.url)
        oauth_host = f"{url.scheme}://{url.netloc}"

        params = {}
        for form_input in form.find_all("input"):
            if form_input.get("type") == "hidden":
                params[form_input.get("name")] = form_input.get("value")

        with self.client.post(oauth_host + action, data=params|{
            "username": username,
            "password": password,
        }, catch_response=True) as response:
            soup = BeautifulSoup(response.text, features="lxml")

            if "Log in" in str(soup.title):
                print("Authentication failed")
                response.failure("Authentication failed")
                return False

        return response

    def _do_authorize_service_account(self, response):
        print("Authorize ...")
        #
        # Authorize ...
        #

        url = urllib3.util.url.parse_url(response.url)
        oauth_host = f"{url.scheme}://{url.netloc}"
        next_url = oauth_host + url.path

        soup = BeautifulSoup(response.text, features="lxml")

        action = soup.find("form").get("action")
        params = {}
        form = soup.body.find("form")
        for form_input in form.find_all("input"):
            name = form_input.get("name")
            value = form_input.get("value")
            if form_input.get("type") == "hidden":
                params[name] = value
                continue

            if form_input.get("type") == "checkbox":
                if name not in params:
                    params[name] = []
                params[name].append(value)
                continue

            if form_input.get("type") == "submit" and name == "approve":
                params[name] = value
                continue

        next_response = self.client.post(next_url, data=params)

        return next_response
