import base64
import copy
import functools
import io
import json
import os
import tempfile
import traceback

import joblib
import numpy as np
import pandas as pd
import requests
import tornado.escape
import tornado.web
import yaml
from astropy.table import Table
from tornado.ioloop import IOLoop

from baselayer.app.env import load_env
from baselayer.app.models import init_db
from baselayer.log import make_log
from skyportal.utils.embedding_store_config import summary_embeddings_enabled

_, cfg = load_env()
log = make_log("openai_analysis_service")

# The triage task reads the classification analysis and posts its comment through
# the database (the service runs inside the deployment), so it connects on import.
init_db(**cfg["database"])

# Preamble: get the embeddings and summary parameters ready
summarize_embedding_config = (
    cfg["analysis_services.openai_analysis_service.embeddings_store.summary"] or {}
)
# The embedding model is configured apart from the chat model.
summarize_embedding_base_url = summarize_embedding_config.get("base_url") or None
summarize_embedding_api_key = summarize_embedding_config.get("api_key") or None
summarize_embedding_model = summarize_embedding_config.get("model")
# This service only produces the vector; SkyPortal stores it when it comes back.
EMBED_SUMMARIES = summary_embeddings_enabled(summarize_embedding_config)

summary_config = copy.deepcopy(cfg["analysis_services.openai_analysis_service.summary"])
if summary_config.get("api_key"):
    # there may be a global API key set in the config file
    openai_api_key = summary_config.pop("api_key")
elif os.path.exists(".secret"):
    # try to get this key from the dev environment, useful for debugging
    openai_api_key = yaml.safe_load(open(".secret")).get("OPENAI_API_KEY")
else:
    openai_api_key = None

default_analysis_parameters = {
    "model": "gpt-3.5-turbo",
    "temperature": 0.1,
    "max_tokens": 1500,
    "top_p": 1.0,
    "frequency_penalty": 0.0,
    "presence_penalty": 1,
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
        "openai_api_key": tmp_analysis_parameters["openai_api_key"],
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

        # Unset base_url means api.openai.com.
        client = OpenAI(
            api_key=analysis_parameters.get("openai_api_key"),
            base_url=analysis_parameters.get("base_url") or None,
        )

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
        redshift = Table.read(data_dict["inputs"]["redshift"], format="ascii.csv")
        z = float(redshift["redshift"][0])
        if np.ma.is_masked(z) or np.isnan(z):
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
                "message": f"OpenAI summarization failed: {e}",
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

    if EMBED_SUMMARIES:
        # Only OpenAI itself, configured without a key of its own, is reached
        # with the key this run was given, which may be the requesting user's.
        embedding_key = summarize_embedding_api_key
        if not embedding_key and not summarize_embedding_base_url:
            embedding_key = analysis_parameters["openai_api_key"]
        embedding_client = OpenAI(
            api_key=embedding_key or "none",
            base_url=summarize_embedding_base_url,
        )
        try:
            response = embedding_client.embeddings.create(
                input=openai_summary,
                model=summarize_embedding_model,
            )
            result["embedding"] = response.data[0].embedding
            result["embedding_model"] = summarize_embedding_model
        except Exception as e:
            # Unindexed, the summary is missing from the search, not lost.
            log(f"Embedding the summary failed, returning it unindexed: {e}")

    f = tempfile.NamedTemporaryFile(suffix=".joblib", prefix="results_", delete=False)
    f.close()
    joblib.dump(result, f.name, compress=3)
    result_data = base64.b64encode(open(f.name, "rb").read())
    try:
        os.remove(f.name)
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


def extract_flare(analysis_results):
    """Pull the classifier block out of an analysis's results dict, or None."""
    if not isinstance(analysis_results, dict):
        return None
    cls = analysis_results.get("classification")
    if not isinstance(cls, dict) or not cls.get("probabilities"):
        return None
    return {
        "classification": cls,
        "triage": analysis_results.get("triage") or {},
        "context": analysis_results.get("context") or {},
    }


def build_triage_prompt(prompt, source_id, flare):
    """Seed the LLM with the classifier's numbers; ask for interpretation, not a
    restatement. flare is the dict from extract_flare."""
    cls = flare["classification"]
    parts = [prompt, "'''", f"Source: {source_id}"]
    probs = ", ".join(
        f"{k} {v:.3f}"
        for k, v in sorted(cls["probabilities"].items(), key=lambda kv: -kv[1])
    )
    parts.append(f"Class probabilities: {probs}")
    parts.append(f"Predicted: {cls.get('predicted')}")
    if cls.get("prediction_set") is not None:
        parts.append(
            f"{int((1 - cls.get('alpha', 0.1)) * 100)}% set: {cls['prediction_set']}"
        )
    if cls.get("credibility") is not None:
        parts.append(f"Credibility: {cls['credibility']}")
    anomaly = cls.get("anomaly") or {}
    if anomaly:
        parts.append(f"Anomaly: {json.dumps(anomaly)}")
    if flare["context"]:
        parts.append(f"Host/context: {json.dumps(flare['context'])}")
    rule = flare["triage"]
    if rule:
        parts.append(
            f"Rule verdict (authoritative): {rule.get('verdict')} priority {rule.get('priority')}"
        )
    parts.append("'''")
    return "\n".join(parts)


def parse_triage_response(text):
    """The LLM is asked for strict JSON; tolerate a fenced or padded object."""
    keys = ("summary", "evidence", "suggested_action", "caveats")
    try:
        obj = json.loads(text)
    except Exception:  # noqa BLE001 — fall back to the first {...} span
        start, end = text.find("{"), text.rfind("}")
        if start == -1 or end <= start:
            return None
        try:
            obj = json.loads(text[start : end + 1])
        except Exception:  # noqa BLE001
            return None
    if not isinstance(obj, dict):
        return None
    return {k: obj.get(k) for k in keys if obj.get(k)}


def format_triage_comment(parsed, flare):
    """Render the parsed triage as a source comment; the rule verdict leads."""
    rule = flare["triage"]
    lines = ["**FLARE triage**"]
    if rule.get("verdict"):
        pr = (
            f" (priority {rule['priority']})"
            if rule.get("priority") is not None
            else ""
        )
        lines.append(f"- Verdict: `{rule['verdict']}`{pr}")
    labels = {
        "summary": "Summary",
        "evidence": "Evidence",
        "suggested_action": "Suggested action",
        "caveats": "Caveats",
    }
    for key, label in labels.items():
        if parsed.get(key):
            lines.append(f"- {label}: {parsed[key]}")
    return "\n".join(lines)


def run_triage(data_dict):
    """Enrich a classifier analysis with an LLM triage and post it as a source
    comment. The service runs inside the deployment, so it reads the analysis and
    writes the comment through the models -- no SkyPortal token or URL needed."""
    import sqlalchemy as sa

    from skyportal.models import Comment, DBSession, Group, ObjAnalysis

    rez = {"status": "failure", "message": "", "analysis": {}}
    params = data_dict["inputs"].get("analysis_parameters", {}) or {}
    source_id = data_dict.get("resource_id")
    if not source_id:
        rez["message"] = "triage needs a source"
        return rez
    triage_cfg = cfg["analysis_services.openai_analysis_service.triage"] or {}
    openai_key = default_analysis_parameters.get("openai_api_key") or params.get(
        "openai_api_key"
    )
    if not openai_key and not default_analysis_parameters.get("base_url"):
        rez["message"] = "OpenAI API key not set"
        return rez

    # 1) the latest completed classification analysis for this source (or a named one)
    flare = author_id = group_ids = None
    try:
        with DBSession() as session:
            analysis_id = params.get("analysis_id")
            if analysis_id is not None:
                rows = [session.get(ObjAnalysis, int(analysis_id))]
            else:
                rows = session.scalars(
                    sa.select(ObjAnalysis)
                    .where(ObjAnalysis.obj_id == source_id)
                    .order_by(ObjAnalysis.created_at.desc())
                ).all()
            for a in rows:
                if a is None or a.status != "completed":
                    continue
                found = extract_flare(a.serialize_results_data())
                if found:
                    flare = found
                    author_id = a.author_id
                    group_ids = [g.id for g in a.groups]
                    break
    except Exception as e:  # noqa BLE001
        rez["message"] = f"could not read classification analysis: {e}"
        return rez
    finally:
        DBSession.remove()
    if not flare:
        rez["message"] = "no completed classification analysis found for this source"
        return rez

    # 2) LLM triage, holding no DB connection during the call
    try:
        from openai import OpenAI

        client = OpenAI(
            api_key=openai_key or "none",
            base_url=default_analysis_parameters.get("base_url") or None,
        )
        # The person triggering the run owns the prompt; the config is only the
        # default when the request does not supply one.
        prompt = params.get("prompt") or triage_cfg.get("prompt", "")
        response = client.chat.completions.create(
            messages=[
                {"role": "system", "content": "You return only strict JSON."},
                {
                    "role": "user",
                    "content": build_triage_prompt(prompt, source_id, flare),
                },
            ],
            model=default_analysis_parameters["model"],
            temperature=default_analysis_parameters["temperature"],
            max_tokens=default_analysis_parameters["max_tokens"],
        )
    except Exception as e:  # noqa BLE001
        rez["message"] = f"LLM triage failed: {e}"
        return rez

    parsed = parse_triage_response(response.choices[0].message.content or "")
    if not parsed:
        rez["message"] = "LLM triage returned no usable JSON"
        return rez

    # 3) post the verdict as a source comment, attributed to the analysis author
    try:
        with DBSession() as session:
            groups = (
                session.scalars(sa.select(Group).where(Group.id.in_(group_ids))).all()
                if group_ids
                else []
            )
            session.add(
                Comment(
                    text=format_triage_comment(parsed, flare),
                    obj_id=source_id,
                    author_id=author_id,
                    groups=list(groups),
                    bot=True,
                )
            )
            session.commit()
    except Exception as e:  # noqa BLE001
        rez["message"] = f"could not post triage comment: {e}"
        return rez
    finally:
        DBSession.remove()

    log(f"FLARE triage posted for {source_id}")
    rez.update({"status": "success", "message": "triage posted as a source comment"})
    return rez


class SummarizeHandler(tornado.web.RequestHandler):
    def set_default_headers(self):
        self.set_header("Content-Type", "application/json")

    def error(self, code, message):
        self.set_status(code)
        self.write({"message": message})

    def get(self):
        self.write({"status": "active"})

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

        # analysis_parameters.task="triage" enriches a classifier analysis and
        # posts a source comment; the default remains source summarization.
        task = (data_dict["inputs"].get("analysis_parameters") or {}).get("task")
        job = run_triage if task == "triage" else run_openai_summarization
        runner = functools.partial(job, data_dict)
        future_result = IOLoop.current().run_in_executor(None, runner)
        future_result.add_done_callback(openai_analysis_done_callback)

        return self.write(
            {
                "status": "pending",
                "message": "openai_analysis_service: analysis started",
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
    port = cfg["analysis_services.openai_analysis_service.port"]
    openai_analysis.listen(port)
    log(f"Listening on port {port}")
    tornado.ioloop.IOLoop.current().start()
