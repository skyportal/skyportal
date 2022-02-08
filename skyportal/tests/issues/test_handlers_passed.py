
from skyportal.handlers.api.telescope import TelescopeHandler
from skyportal.handlers.api.instrument import InstrumentHandler
from skyportal.handlers.api.stream import StreamHandler
from skyportal.handlers.api.filter import FilterHandler
from skyportal.handlers.api.source import SourceHandler

import json
import ast
from tornado import httputil
import pytest

stream_id = None
filter_id = None

class FakeApplication:
    """Mimics the Application class of tornado.web.
    Subclasses were minimum required to import the class.
    """

    def __init__(self,) -> None:
        super().__init__()
        self.ui_methods = {}
        self.ui_modules = {}
        self.settings = {}



class FakeRequest(httputil.HTTPServerRequest):
    """Mimics the HTTP request handler of tornado.web.
    Subclasses were minimum required to import the class.
    """

    def __init__(
        self,
    ):
        self.test = True
        
        super().__init__()

        class FakeConnection(object):
            """Mimics the connection within the HTTP request handler."""

            def __init__(
                self,
            ):
                def set_close_callback(self):
                    return True

                self.set_close_callback = set_close_callback



        self.connection = FakeConnection()

application = FakeApplication()
fake_request = FakeRequest()

# In this test, we post a new Telescope using the TelescopeHandler

def test_telescope_handler(super_admin_user):

    #TELESCOPE
    telescope_handler = TelescopeHandler(
        application=application,
        request=fake_request,
    )
    telescope_handler.current_user = super_admin_user

    body = {
        'name': 'ZTF2',
        'nickname': 'ZTF2_nickname',
        'diameter': 14
        }

    telescope_handler.request.body = json.dumps(body, indent=2).encode('utf-8')
    try:
        telescope_handler.post()
    except: None

    assert telescope_handler.get_status() == 200
    #============================================================================


# In this test, we post a new Instrument using the InstrumentHandler
@pytest.mark.run(after='test_telescope_handler')
def test_instrument_handler(super_admin_user):

    #INSTRUMENT
    instrument_handler = InstrumentHandler(
        application=application,
        request=fake_request,
    )

    instrument_handler.current_user = super_admin_user

    body = {
        'name': 'ZTF2_instrument',
        'type': 'imager',
        'telescope_id': 1,
        'filters': ['ztfr', 'ztfg', 'ztfi'],
    }
    
    instrument_handler.request.body = json.dumps(body, indent=2).encode('utf-8')
    try:
        instrument_handler.post()
    except: None

    assert instrument_handler.get_status() == 200
    #============================================================================


# In this test, we post a new Stream using the StreamHandler
@pytest.mark.run(after='test_instrument_handler')
def test_stream_handler(super_admin_user):

    #STREAM
    stream_handler = StreamHandler(
        application=application,
        request=fake_request,
    )

    body = {
        'name': 'test_stream'
    }

    stream_handler.current_user = super_admin_user
    stream_handler.request.body = json.dumps(body, indent=2).encode('utf-8')
    try:
        stream_handler.post()
    except: None

    assert stream_handler.get_status() == 200

    stream_id = ast.literal_eval(stream_handler._write_buffer[0].decode('utf-8'))['data']['id']
    assert stream_id is not None
    #============================================================================

@pytest.mark.run(after='test_stream_handler')
def test_stream_get(super_admin_user):
    stream_handler = StreamHandler(
        application=application,
        request=fake_request,
    )
    stream_handler.current_user = super_admin_user
    try:
        stream_handler.get()
    except: None
    stream_id = json.loads(stream_handler._write_buffer[0].decode('utf-8'))['data'][0]['id']

    print(stream_id)
    assert stream_id is not None


# In this test, we post a new Filter using the FilterHandler
@pytest.mark.run(after='test_stream_get')
def test_filter_handler(super_admin_user):
    #STREAM
    stream_handler = StreamHandler(
        application=application,
        request=fake_request,
    )
    stream_handler.current_user = super_admin_user
    try:
        stream_handler.get()
    except: None
    stream_id = json.loads(stream_handler._write_buffer[0].decode('utf-8'))['data'][0]['id']

    #FILTER
    filter_handler = FilterHandler(
        application=application,
        request=fake_request,
    )

    body = {
        'name': 'test_filter',
        'stream_id': stream_id,
        'group_id': 1,
    }

    
    filter_handler.current_user = super_admin_user
    filter_handler.request.body = json.dumps(body, indent=2).encode('utf-8')
    try:
        filter_handler.post()
    except: None
    assert filter_handler.get_status() == 200
    
    #============================================================================

# In this test, we post a new Source using the SourceHandler
@pytest.mark.run(after='test_filter_handler')
def test_source_handler(super_admin_user):
    
    #SOURCE    
    source_handler = SourceHandler(
        application=application,
        request=fake_request,
    )

    body = {
        'id': 'ZTF_TEST',
        'ra': 10,
        'dec': 10,
        'group_ids': [1],     
    }

    source_handler.current_user = super_admin_user
    source_handler.request.body = json.dumps(body, indent=2).encode('utf-8')
    try:
        source_handler.post()
    except: None

    assert source_handler.get_status() == 200
    #============================================================================