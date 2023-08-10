#!/usr/bin/env python
import os
import urllib
import requests
import time
from typing import Optional, Mapping
from requests.exceptions import InvalidJSONError, JSONDecodeError
from urllib3.exceptions import ProtocolError
import argparse

token = os.getenv('TOKEN')
protocol = os.getenv('PROTOCOL')
host = os.getenv('HOST')
base_url = f"{protocol}://{host}/"

MAX_ATTEMPTS = 10
SLEEP_TIME = 5


def api(
    method: str,
    endpoint: str,
    data: Optional[Mapping] = None,
    token: str = token,
    base_url: str = base_url,
    max_attempts: int = MAX_ATTEMPTS,
    sleep_time: int = SLEEP_TIME,
):
    method = method.upper()
    headers = {"Authorization": f"token {token}"}
    kwargs = {
        "method": method,
        "url": urllib.parse.urljoin(base_url, endpoint),
        "headers": headers,
    }
    if method not in ("GET", "HEAD"):
        kwargs["json"] = data
    elif method == "GET":
        kwargs["params"] = data

    for attempt in range(max_attempts):
        try:
            response = requests.request(**kwargs)
            break
        except (
            InvalidJSONError,
            ConnectionError,
            ProtocolError,
            OSError,
            JSONDecodeError,
        ):
            print(f'Error - Retrying (attempt {attempt+1}).')
            time.sleep(sleep_time)
            continue

    return response
    

def run_analysis(service, model):
    services_response = api('GET', 'api/analysis_service')
    try:
        services_data = services_response.json().get('data')
    except Exception as e:
        print(f"Error querying available services: {e}")
        return
    
    service_id = None
    if services_data is not None:
        for srv in services_data:
            name = srv['name']
            if name == service:
                service_id = srv['id']
    else:
        print("No available analysis services.")
        return
    
    if service_id is not None:
        print(f"Found service under ID {service_id}. Running {service} using {model} model...")
        api('POST', f'api/obj/ZTF21aaqjmps/analysis/{service_id}', {'analysis_parameters': {'source':model}}).json()


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--service",
        type=str,
        default=None,
        help="Name of analysis service to run",
    )
    parser.add_argument(
        "--model",
        type=str,
        default=None,
        help="Name of model to use for analysis run",
    )

    args = parser.parse_args()
    
    run_analysis(service=args.service, model=args.model)
