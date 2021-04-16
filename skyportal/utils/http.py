def serialize_requests_request(request):
    if request.body is not None:
        body = request.body.decode()
    else:
        body = ''

    return {
        'headers': dict(request.headers),
        'body': body,
        'url': request.url,
        'method': request.method,
    }


def serialize_requests_request_xml(payload):
    return {'payload': payload}


def serialize_requests_response(response):
    return {
        'headers': dict(response.headers),
        'content': response.text,
        'cookies': response.cookies.get_dict(),
        'elapsed': response.elapsed.total_seconds(),
        'status_code': response.status_code,
        'ok': response.ok,
    }


def serialize_requests_response_xml(response):
    return {'response': response}


def serialize_tornado_request(handler):
    return {
        'headers': dict(handler.request.headers),
        'body': handler.request.body.decode(),
        'url': handler.request.uri,
        'method': handler.request.method,
    }
