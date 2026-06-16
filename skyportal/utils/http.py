def serialize_requests_request(request):
    if request.body is not None:
        if isinstance(request.body, bytes):
            body = request.body.decode()
        else:
            body = request.body
    else:
        body = ""

    return {
        "headers": dict(request.headers),
        "body": body,
        "url": request.url,
        "method": request.method,
    }


def serialize_requests_request_xml(payload):
    return {"payload": payload}


def serialize_requests_response(response):
    return {
        "headers": dict(response.headers),
        "content": response.text,
        "cookies": response.cookies.get_dict(),
        "elapsed": response.elapsed.total_seconds(),
        "status_code": response.status_code,
        "ok": response.ok,
    }


def serialize_requests_response_xml(response):
    return {"response": response}


def serialize_tornado_request(handler):
    return {
        "headers": dict(handler.request.headers),
        "body": handler.request.body.decode(),
        "url": handler.request.uri,
        "method": handler.request.method,
    }


# --- aiohttp equivalents (facility_apis are async; aiohttp has no prepared
# request object like `requests`, so the request side is serialized from the
# call arguments captured at the call site). Output JSONB shape matches the
# `requests` serializers so FacilityTransaction storage is unchanged.


def serialize_aiohttp_request(method, url, headers=None, body=None):
    """Serialize an outgoing aiohttp request from its call arguments."""
    import json as _json

    if isinstance(body, bytes):
        body = body.decode()
    elif body is not None and not isinstance(body, str):
        body = _json.dumps(body)
    return {
        "headers": dict(headers or {}),
        "body": body if body is not None else "",
        "url": str(url),
        "method": str(method).upper(),
    }


async def serialize_aiohttp_response(response, content=None):
    """Serialize an aiohttp ClientResponse to the FacilityTransaction shape.

    Pass ``content`` if the body has already been read (e.g. ``await
    response.text()``) to avoid reading the stream twice."""
    if content is None:
        content = await response.text()
    return {
        "headers": dict(response.headers),
        "content": content,
        "cookies": {key: morsel.value for key, morsel in response.cookies.items()},
        "elapsed": None,  # aiohttp does not expose request elapsed time
        "status_code": response.status,
        "ok": response.status < 400,
    }
