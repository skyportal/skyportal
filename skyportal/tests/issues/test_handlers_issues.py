from skyportal.handlers.api.stream import StreamHandler
from skyportal.handlers.api.filter import FilterHandler
from skyportal.handlers.api.candidate import CandidateHandler
from skyportal.handlers.api.photometry import PhotometryHandler
from urllib import request
import json
from tornado import httputil


stream_id = None

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

# In this test, we post a new Candidate using the CandidateHandler
def test_candidate_handler(super_admin_user):
    filter_handler = FilterHandler(
        application=application,
        request=fake_request,
    )
    filter_handler.current_user = super_admin_user
    try:
        filter_handler.get()
    except: None
    filter_id = json.loads(filter_handler._write_buffer[0].decode('utf-8'))['data'][0]['id']

    #CANDIDATE   
    candidate_handler = CandidateHandler(
        application=application,
        request=fake_request,
    )

    body = {
        'id': 'ZTF_TEST',
        'filter_ids': [filter_id],
        'passed_at': 59000,
        'ra': 10,
        'dec': 10,    
    }

    candidate_handler.current_user = super_admin_user
    candidate_handler.request.body = json.dumps(body, indent=2).encode('utf-8')
    try:
        candidate_handler.post()
    except: None

    assert candidate_handler.get_status() == 200

    
    #============================================================================


def test_photometry_handler(super_admin_user):

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

    #PHOTOMETRY
    photometry_handler = PhotometryHandler(
    application=application,
    request=fake_request,
    )

    body = {
        'obj_id': 'ZTF_TEST',
        'filter': 'ztfr',
        'mjd': 59800.3,
        'mag': 18,
        'magerr': 0.1,
        'limiting_mag': 21,
        'magsys': 'ab',
        'ra': 18,
        'dec': 18,
        'instrument_id': 1,
        'group_ids': 'all',
        'stream_ids': [stream_id]
        
    }

    photometry_handler.current_user = super_admin_user
    photometry_handler.request.body = json.dumps(body, indent=2).encode('utf-8')
    try:
        photometry_handler.post()
    except: None

    assert photometry_handler.get_status() == 200



def candidate_handler_get(super_admin_user):
    #CANDIDATE   
    candidate_handler = CandidateHandler(
        application=application,
        request=fake_request,
    )

    candidate_handler.current_user = super_admin_user

    try:
        candidate_handler.get()
    except: None
    nb_candidates = json.loads(candidate_handler._write_buffer[0].decode('utf-8'))['data']['totalMatches']
    assert nb_candidates > 0


def test_photometry_handler_get(super_admin_user):
    #CANDIDATE   
    photometry_handler = PhotometryHandler(
        application=application,
        request=fake_request,
    )

    photometry_handler.current_user = super_admin_user

    try:
        photometry_handler.get()
    except: None
    assert photometry_handler.get_status() == 200

    print(photometry_handler._write_buffer)
    assert len(photometry_handler._write_buffer) is not 0




