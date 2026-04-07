import json
import os
import shutil
import requests


class ADAConnector:
    def __init__(self, keychain=None,config=None):
        self.config = config
        self.ada_user = keychain['username']
        self.ada_pass = keychain['password']
        self.token = self.obtain_token()
    '''
    keychain = {'username': 'alice', 'password': 's3cret'}
    config = {
        'ada_url': 'https://ada.example',
        'affiliate_name': 'ACME',
        'data_staging_folder': '/tmp/ada_staging',
        'default_template': 'MemberUpload'
    }
    '''
    def obtain_token(self):
        user = self.ada_user
        password = self.ada_pass
        resp = requests.post(
            f"{self.config['ada_url']}/api/users/token/access_token",
            params=dict(username=user, password=password)
        )
        if resp.status_code == 200:
            ada_token = resp.headers["x-access-token"]
        elif resp.status_code == 401:
            ...  # handle failure to authorize
        else:
            ...  # handle unexpected response (server error?)
        print(ada_token[:6])  # --> 'eyJhbG'
        return ada_token

    def create_json_template(self, template_name):
        json_data = open(self.config['data_staging_folder'] + '/' + "upload-template.json")
        data = json.load(json_data)
        resp = requests.post(
            f"{self.config['ada_url']}/api/template/",
            params={"affiliate": self.config['affiliate_name'], "name": template_name},
            headers={"Authorization": f"Bearer {self.token}"},
            json=data
        )
        if resp.status_code == 201:
            ada_template = resp.json()["filename"]
            return ada_template
        elif resp.status_code == 401:
            # There are errors in the format of the template
            print(resp.json()["message"])
            print(resp.json()["details"])
        elif resp.status_code == 403:
            print(f"Permission denied for affiliate {resp.json()['affiliate']}")
        else:
            pass

    # Step 2 Upload Your Membership File (preferably in .csv format)
    def upload(self, file_path_name):
        resp = requests.post(
            f"{self.config['ada_url']}/api/uploads",
            params={"affiliate": self.config['affiliate_name']},
            files={"file": open(file_path_name)},
            headers={"Authorization": f"Bearer {self.token}"}
        )
        if resp.status_code == 201:
            affiliate_data = resp.json()["filename"]
            return affiliate_data
        elif resp.status_code == 401:
            # Usually a data problem, such as an unsupported file type
            print(resp.json()["message"])
            print(resp.json()["details"])
        elif resp.status_code == 403:
            print(f"Permission denied for affiliate {resp.json()['affiliate']}")
        else:
            pass

    def get_blank_template(self):
        resp = requests.get(f"{self.config['ada_url']}/api/template/new")
        return resp

    def clear_staging_folder(self, folder):
        for filename in os.listdir(folder):
            print(filename)
            if filename != '.gitkeep':
                file_path = os.path.join(folder, filename)
                try:
                    if os.path.isfile(file_path) or os.path.islink(file_path):
                        os.unlink(file_path)
                    elif os.path.isdir(file_path):
                        shutil.rmtree(file_path)
                except Exception as e:
                    print('Failed to delete %s. Reason: %s' % (file_path, e))

    def get_templates(self):
        resp = requests.get(
            f"{self.config['ada_url']}/api/templates",
            params={"affiliate": self.config['affiliate_name']},
            headers={"Authorization": f"Bearer {self.token}"}
        )
        return resp.json()

    # Step 4 Process the File
    def process_ada_file(self, ada_file, template_name):
        resp = requests.post(
            f"{self.config['ada_url']}/api/process",
            params={"affiliate": self.config['affiliate_name'], "template": template_name, "data": ada_file},
            headers={"Authorization": f"Bearer {self.token}"},
        )
        if resp.status_code == 201:
            return resp.json()
        elif resp.status_code == 400:
            # There are errors in the format of the template
            print('Content: ' + resp.json().get("content"))
            print('Message: ' + resp.json().get("message"))
            print('Details: ' + resp.json().get("details"))
        elif resp.status_code == 403:
            print(f"Permission denied for affiliate {resp.json()['affiliate']}")
        else:
            ...  # handle unexpected response (server error?)

    # Step 5 Preview the File
    def ada_get_summary(self, ada_file):
        resp = requests.get(
            f"{self.config['ada_url']}/api/summary",
            params={"affiliate": self.config['affiliate_name'], "ada_file": ada_file},
            headers={"Authorization": f"Bearer {self.token}"},
        )
        return resp.json()

    # Step 6 Confirm Submission
    def ada_patch_summary(self, ada_file):
        resp = requests.patch(
            f"{self.config['ada_url']}/api/summary",
            params={"affiliate": self.config['affiliate_name'], "ada_file": ada_file},
            headers={"Authorization": f"Bearer {self.token}"},
        )
        return resp.json()

    def get_default_template(self):
        resp = requests.get(f"{self.config['ada_url']}/api/template/new")
        return resp

    def get_ada_template_name(self, template_name):
        template_list = self.get_templates()
        for x in template_list:
            if x['name'] == template_name:
                return f"{x['created']}{'/'}{x['name']}"

    def upload_file_to_ada(self, file_path_name, template_name=None):
        # uploads membership file to ada needs file path name
        affiliate_data = self.upload(file_path_name)
        # if the template name is not provided, it will use the default template
        if template_name is None:
            # finds default template in config file
            if self.config['default_template']:
                template = self.get_ada_template_name(self.config['default_template'])
            # if template not in config will get most recently created template
            else:
                # get a list of existing template
                list_of_template = self.get_templates()
                template = f"{list_of_template[0]['created']}{'/'}{list_of_template[0]['name']}"
        else:
            template = self.get_ada_template_name(template_name)
        data = "/".join(affiliate_data.split("/")[2:])
        submit = self.process_ada_file(template_name=template, ada_file=data)
        # get summary of the processed file
        ada_file_path = "/".join(submit['full_path'].split("/")[2:-1])
        summary = self.ada_get_summary(ada_file=ada_file_path)
        print(summary)
        confirm = self.ada_patch_summary(ada_file=ada_file_path)
        print(confirm)
