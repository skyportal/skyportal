import copy
import io
import os
import functools
import tempfile
import base64
import traceback
import json
import yaml

import numpy as np
import pandas as pd
import requests
from astropy.table import Table
import joblib

from pinecone import Pinecone

from tornado.ioloop import IOLoop
import tornado.web
import tornado.escape

from baselayer.log import make_log
from baselayer.app.env import load_env

_, cfg = load_env()
log = make_log('openai_analysis_service')

# Preamble: get the embeddings and summary parameters ready
# for now, we only support pinecone embeddings
summarize_embedding_config = cfg[
    'analysis_services.openai_analysis_service.embeddings_store.summary'
]
pinecone_client = None
USE_PINECONE = False
if (
    summarize_embedding_config.get("location") == "pinecone"
    and summarize_embedding_config.get("api_key")
    and summarize_embedding_config.get("index_name")
    and summarize_embedding_config.get("index_size")
):
    log("initializing pinecone...")
    pinecone_client = Pinecone(
        api_key=summarize_embedding_config.get("api_key"),
    )

    summarize_embedding_index = summarize_embedding_config.get("index_name")
    if summarize_embedding_index not in [
        index.name for index in pinecone_client.list_indexes().indexes
    ]:
        # check if we have the spec variable in the config
        pod_spec_required_keys = ["environment", "pod_type"]
        serverless_spec_required_keys = ["cloud", "region"]

        pod_spec_optional_keys = ["replicas", "pods", "shards"]

        has_pod_spec = all(
            summarize_embedding_config.get(k) is not None
            for k in pod_spec_required_keys
        )
        has_serverless_spec = all(
            summarize_embedding_config.get(k) is not None
            for k in serverless_spec_required_keys
        )

        if has_pod_spec:
            USE_PINECONE = True
        else:
            log(
                "Pod spec not found in the config file, cannot create index in pinecone"
            )

        if USE_PINECONE:
            spec = {
                "pod": {
                    "environment": summarize_embedding_config.get("environment"),
                    "pod_type": summarize_embedding_config.get("pod_type"),
                }
            }
            for k in pod_spec_optional_keys:
                if summarize_embedding_config.get(k) is not None:
                    spec["pod"][k] = summarize_embedding_config.get(k)
            if has_serverless_spec:
                spec = {
                    "serverless": {
                        "cloud": summarize_embedding_config.get("cloud"),
                        "region": summarize_embedding_config.get("region"),
                    }
                }
            pinecone_client.create_index(
                summarize_embedding_index,
                dimension=summarize_embedding_config.get("index_size"),
                spec=spec,
            )
            log(f"index {summarize_embedding_index} created in pinecone")
    else:
        USE_PINECONE = True
else:
    log(
        "Pinecone access does not seem to be configured in the config file, not using pinecone"
    )

summary_config = copy.deepcopy(cfg['analysis_services.openai_analysis_service.summary'])
if summary_config.get("api_key"):
    # there may be a global API key set in the config file
    openai_api_key = summary_config.pop("api_key")
elif os.path.exists(".secret"):
    # try to get this key from the dev environment, useful for debugging
    openai_api_key = yaml.safe_load(open(".secret")).get("OPENAI_API_KEY")
else:
    openai_api_key = None

default_analysis_parameters = {
    **dict(
        model="gpt-3.5-turbo",
        temperature=0.1,
        max_tokens=1500,
        top_p=1.0,
        frequency_penalty=0.0,
        presence_penalty=1,
    ),
    **summary_config.copy(),
}
default_analysis_parameters["openai_api_key"] = openai_api_key


def upload_analysis_results(results, data_dict, request_timeout=60):
    """
    Upload the results to the webhook.
    """

    log("Uploading results to webhook")
    if data_dict["callback_method"] != "POST":
        log("Callback URL is not a POST URL. Skipping.")
        return
    url = data_dict["callback_url"]
    try:
        _ = requests.post(
            url,
            json=results,
            timeout=request_timeout,
        )
    except requests.exceptions.Timeout:
        # If we timeout here then it's precisely because
        # we cannot write back to the SkyPortal instance.
        # So returning something doesn't make sense in this case.
        # Just log it and move on...
        log("Callback URL timedout. Skipping.")
    except Exception as e:
        log(f"Callback exception {e}.")


def create_summary_string(source_id, prompt, comments, classifications, redshift):
    """
    Create a summary string from the comments, classifications, and redshift.
    """
    if len(comments) == 0 and len(classifications) == 0:
        return None

    summary_string = f"{prompt}\n'''"
    if source_id is not None:
        summary_string += f"Source ID: {source_id}\n"

    if redshift is not None:
        summary_string = f"Redshift: {redshift:.4f}\n"

    if len(classifications) > 0:
        summary_string += "Classifications:\n"
        for r in set(classifications["classification"]):
            summary_string += f"  - {r}\n"

    if len(comments) > 0:
        summary_string += "Comments (given in reverse chronological order):\n"
        for r in set(comments["text"]):
            summary_string += f"  - {r}\n"

    summary_string += "'''"
    return summary_string


def run_openai_summarization(data_dict):
    """
    Use an AI summarization engine (`openai`) to produce
    a human-readable summary of the source.

    For this analysis, we expect the `inputs` dictionary to have the following keys:
       - comments: a list of comments from about the source
       - annotations: a list of annotations about the source
       - redshift: the (known) redshift of the object

    """
    tmp_analysis_parameters = data_dict["inputs"].get("analysis_parameters", {})
    analysis_parameters = {
        **default_analysis_parameters,
        **tmp_analysis_parameters["summary_parameters"],
        **dict(openai_api_key=tmp_analysis_parameters["openai_api_key"]),
    }
    #
    # the following code transforms these inputs from SkyPortal
    # to the format that will give us a good summary from OpenAI.
    #
    rez = {"status": "failure", "message": "", "analysis": {}}

    if analysis_parameters.get("openai_api_key") is None:
        log("No OpenAI API key set. Skipping and setting this analysis to failure.")
        rez.update(
            {
                "status": "failure",
                "message": "OpenAI API key not set",
            }
        )
        return rez
    try:
        from openai import OpenAI

        client = OpenAI(api_key=analysis_parameters.get("openai_api_key"))

    except Exception as e:
        rez.update(
            {
                "status": "failure",
                "message": f"OpenAI API key is not set {e}",
            }
        )
        return rez

    try:
        classifications = pd.read_csv(
            io.StringIO(data_dict["inputs"]["classifications"])
        ).drop_duplicates(keep="first")
    except Exception as e:  # noqa F841
        classifications = pd.DataFrame({"classification": []})

    try:
        comments = pd.read_csv(
            io.StringIO(data_dict["inputs"]["comments"])
        ).drop_duplicates(keep="first")
    except Exception as e:  # noqa F841
        comments = pd.DataFrame({"text": []})

    try:
        redshift = Table.read(data_dict["inputs"]["redshift"], format='ascii.csv')
        z = float(redshift['redshift'][0])
        if np.ma.is_masked(z):
            z = None
        source_id = data_dict.get("resource_id", "unknown")
    except Exception as e:
        rez.update(
            {
                "status": "failure",
                "message": f"input data is not in the expected format {e}",
            }
        )
        return rez

    log("Running OpenAI summarization")
    # create the summary string
    summary_string = create_summary_string(
        source_id, analysis_parameters.get("prompt"), comments, classifications, z
    )
    if summary_string is None:
        rez.update(
            {
                "status": "failure",
                "message": "No comments or classifications to summarize",
            }
        )
        return rez

    try:
        response = client.chat.completions.create(
            messages=[
                {
                    "role": "system",
                    "content": "You are an authoritative expert in astronomical time-domain research.",
                },
                {
                    "role": "user",
                    "content": summary_string,
                },
            ],
            model=analysis_parameters["model"],
            temperature=analysis_parameters["temperature"],
            max_tokens=analysis_parameters["max_tokens"],
            top_p=analysis_parameters["top_p"],
            frequency_penalty=analysis_parameters["frequency_penalty"],
            presence_penalty=analysis_parameters["presence_penalty"],
        )
    except Exception as e:
        log(f"OpenAI summarization failed {e}")
        rez.update(
            {
                "status": "failure",
                "message": f"OpenAI summarization failed {e}",
            }
        )
        return rez

    openai_summary = response.choices[0].message.content

    # remove dislaimers & newlines
    openai_summary = openai_summary.replace("Based on the given information, it", "It")
    sentences = openai_summary.split(". ")
    temp_summary = []
    for s in sentences:
        if s.startswith("This is an automated summary"):
            continue
        if s.find("As an AI language model") != -1:
            continue
        if s.find("OpenAI") != -1:
            continue
        temp_summary.append(s)
    openai_summary = ". ".join(temp_summary).replace("\n", " ")
    result = {"summary": openai_summary}

    if USE_PINECONE:
        e = client.embeddings.create(
            input=openai_summary,
            model=summarize_embedding_config.get("model", "text-embedding-ada-002"),
        )
        pinecone_index = pinecone_client.Index(summarize_embedding_index)
        metadata = {}
        if z is not None:
            metadata["redshift"] = z

        if len(classifications) > 0:
            metadata["class"] = list(set(classifications["classification"]))
        else:
            metadata["class"] = []

        metadata["summary"] = openai_summary

        pinecone_index.upsert([(source_id, e.data[0].embedding, metadata)])
        result["embedding"] = e.data[0].embedding

    f = tempfile.NamedTemporaryFile(suffix=".joblib", prefix="results_", delete=False)
    f.close()
    joblib.dump(result, f.name, compress=3)
    result_data = base64.b64encode(open(f.name, "rb").read())
    try:
        os.remove(f)
    except:  # noqa E722
        pass

    analysis_results = {
        "results": {"format": "joblib", "data": result_data},
    }
    rez.update(
        {
            "analysis": analysis_results,
            "status": "success",
            "message": "OpenAI summarization completed",
        }
    )

    log(f"OpenAI summarization for {source_id} completed")
    return rez


class SummarizeHandler(tornado.web.RequestHandler):
    def set_default_headers(self):
        self.set_header('Content-Type', 'application/json')

    def error(self, code, message):
        self.set_status(code)
        self.write({'message': message})

    def get(self):
        self.write({'status': 'active'})

    def post(self):
        """
        Analysis endpoint which sends the `data_dict` off for
        processing, returning immediately. The idea here is that
        the analysis summarization may take awhile to run so we
        need async behavior.
        """
        try:
            data_dict = tornado.escape.json_decode(self.request.body)
        except json.decoder.JSONDecodeError:
            err = traceback.format_exc()
            log(f"JSON decode error: {err}")
            return self.error(400, "Invalid JSON")

        required_keys = ["inputs", "callback_url", "callback_method"]
        for key in required_keys:
            if key not in data_dict:
                log(f"missing required key {key} in data_dict")
                return self.error(400, f"missing required key {key} in data_dict")

        def openai_analysis_done_callback(
            future,
            logger=log,
            data_dict=data_dict,
        ):
            """
            Callback function for when the openai analysis service is done.
            Sends back results/errors via the callback_url.

            This is run synchronously after the future completes
            so there is no need to await for `future`.
            """
            try:
                result = future.result()
            except Exception as e:
                # catch all the exceptions and log them,
                # try to write back to SkyPortal something
                # informative.
                logger(f"{str(future.exception())[:1024]} {e}")
                result = {
                    "status": "failure",
                    "message": f"{str(future.exception())[:1024]}{e}",
                }
            finally:
                upload_analysis_results(result, data_dict)

        runner = functools.partial(run_openai_summarization, data_dict)
        future_result = IOLoop.current().run_in_executor(None, runner)
        future_result.add_done_callback(openai_analysis_done_callback)

        return self.write(
            {
                'status': 'pending',
                'message': 'openai_analysis_service: analysis started',
            }
        )


def make_app():
    return tornado.web.Application(
        [
            (r"/summarize", SummarizeHandler),
        ]
    )


if __name__ == "__main__":
    openai_analysis = make_app()
    port = cfg['analysis_services.openai_analysis_service.port']
    openai_analysis.listen(port)
    log(f'Listening on port {port}')
    tornado.ioloop.IOLoop.current().start()
