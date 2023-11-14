import logging
import urllib3
from bs4 import BeautifulSoup

import common

class Oauth(common.ContextBase):
    def __init__(self, context):
        common.ContextBase.__init__(self, context)

    def do_login(self, response):
        if "Log in with OpenShift" in response.text:
            response = self._do_login_with_openshift(response)
            if not response:
                return response

        response = self._do_login_with(response, self.env.IDP_NAME)
        if not response:
            return response

        response = self._do_log_in_to_your_account(response, self.env.IDP_NAME,
                                                   self.user_name, self.env.USER_PASSWORD)
        if not response:
            return response

        if "Authorize" in response.text:
            response = self._do_authorize_service_account(response)
            if not response:
                return response

        return response


    def _do_login_with_openshift(self, response):
        logging.info("Log in with OpenShift")
        #
        # Page: Log in with OpenShift
        #
        soup = BeautifulSoup(response.text, features="lxml")
        action = soup.body.find("form").get("action")

        return self.client.get(action, params={"rd":"/"}, name="<oauth_host>/{action}")

    def _do_login_with(self, response, method):
        logging.info("Log in with ...")
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
            logging.error(f"Could not find the authentication method '{method}' in the oauth page ...")
            common.debug_point()
            if response: response.status_code = 599
            return response

        return self.client.get(oauth_host + action, name="<oauth_host>"+action.partition("?")[0])

    def _do_log_in_to_your_account(self, response, method, username, password):
        logging.info("Log in to your account")
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

        with self.client.post(oauth_host + action,
                              name="<oauth_host>"+action.replace(method, "{oauth method}"),
                              data=params|{
                                  "username": username,
                                  "password": password,
                              }, catch_response=True) as response:
            soup = BeautifulSoup(response.text, features="lxml")

            if "Log in" in str(soup.title):
                logging.error("Authentication failed ...")
                response.failure("Authentication failed")

                if response: response.status_code = 599
                return response

        return response

    def _do_authorize_service_account(self, response):
        logging.info("Authorize ...")
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

        next_response = self.client.post(next_url, data=params, name="<oauth_host>"+url.path)
        if not next_response:
            logging.error("Authorize failed ...")
            common.debug_point()
        return next_response
