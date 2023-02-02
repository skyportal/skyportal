# Follow-up triggering

The vast majority of follow-up instruments will require some form of authentication. All such information is passed through the `altdata` variable of the `Allocation`s API. We briefly describe the authentication form the available telescopes take below:

* ATLAS Forced Photometry: A user account must be made on https://fallingstar-data.com/forcedphot/, at which point the authentication takes the form `{"api_token": "testtoken"}`.
* KAIT: A username and password are passed as `{"username": "username", "password": "password"}`.
* LCO: A user account must be made on https://lco.global/, at which point the authentication takes the form `{"PROPOSAL_ID": "your_proposal_ID", "API_TOKEN": "testtoken", "API_ARCHIVE_TOKEN": "testarchivetoken"}`. The submission token is available directly from https://observe.lco.global while the archive token can be aquired by API:
ar = requests.post('https://archive-api.lco.global/api-token-auth/',
                       data = {'username': username, 'password': password})
ar_token = ar.json()['token']
* LT: A proposal ID, username, and password are passed as `{"username": "username", "password": "password", "LT_proposalID": "your_proposal_ID"}`.
* MMA: There are two generic methods for distributing observation plans. The first is through API, where the user provides {"protocol": "http/https", "host": "host", "port": "port", "access_token": "token"}, and the second through scp, where the user provides {"host": "host", "port": "port", "username": "username", "password": "password", "directory": "output_directory"}.
* NICER: A username and password (as entered at https://heasarc.gsfc.nasa.gov/ark/nicertoo/) are passed as `{"username": "username", "password": "password"}`.
* SLACK: As discussed further [here](./slack.html), slack information is pass as `{"slack_workspace": "XXX", "slack_channel": "YYY", "slack_token": "ZZZ"}`.
* SWIFT Triggering: A username and password are passed as `{"username": "username", "secret": "password"}`.
* SWIFT XRT Reductions: A user account must be made with the Swift-XRT data products API platform (see https://www.swift.ac.uk/user_objects/register.php to register). The authentication then is the email of the user `"XRT_UserID": "swift_email"}` where swift_email is the email address used upon sign up.
* ZTF Triggering: An API token for an admin user for [Kowalski](https://github.com/dmitryduev/kowalski) can be passed as `{"access_token": "your_token"}`.
* ZTF Forced Photometry: A user account must be made with the ZTF forced photometry service (see https://zwicky.tf/vgt). The authentication then takes the form `{"ipac_http_user": "http_user", "ipac_http_password": "http_password", "ipac_email": "email", "ipac_userpass": "password"}` where http_user and http_password are provided in the documentation and ipac_email and ipac_userpass are provided for the specific account. Note that IPAC's forced photometry database is updated once per hour, on the hour, and requests will only be available after this update.
