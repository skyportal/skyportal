import yaml

import gcn

from baselayer.log import make_log

from skyportal.tests import api


def get_token():
    try:
        token = yaml.load(open('.tokens.yaml'), Loader=yaml.Loader)['INITIAL_ADMIN']
        print('Token loaded from `.tokens.yaml`')
        return token
    except (FileNotFoundError, TypeError, KeyError):
        print('Error: no token specified, and no suitable token found in .tokens.yaml')
        return None


admin_token = get_token()


@gcn.include_notice_types(
    gcn.NoticeType.FERMI_GBM_FLT_POS,
    gcn.NoticeType.FERMI_GBM_GND_POS,
    gcn.NoticeType.FERMI_GBM_FIN_POS,
    gcn.NoticeType.FERMI_GBM_SUBTHRESH,
    gcn.NoticeType.LVC_PRELIMINARY,
    gcn.NoticeType.LVC_INITIAL,
    gcn.NoticeType.LVC_UPDATE,
    gcn.NoticeType.LVC_RETRACTION,
    gcn.NoticeType.LVC_TEST,
    gcn.NoticeType.AMON_ICECUBE_COINC,
    gcn.NoticeType.AMON_ICECUBE_HESE,
    gcn.NoticeType.ICECUBE_ASTROTRACK_GOLD,
    gcn.NoticeType.ICECUBE_ASTROTRACK_BRONZE,
)
def handle(payload):
    response_status, data = api(
        'POST', 'gcn_event', data={'xml': payload}, token=admin_token
    )


if __name__ == "__main__":
    log = make_log("gcnserver")

    gcn.listen(handler=handle)
