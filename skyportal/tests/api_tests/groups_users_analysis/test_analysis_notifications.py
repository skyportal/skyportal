from skyportal.models import DBSession, ObjAnalysis, user_notification


class InlineIOLoop:
    @staticmethod
    def current():
        return InlineIOLoop

    @staticmethod
    def run_in_executor(executor, func):
        func()


def test_analysis_completion_is_notified_once(public_obj_analysis, monkeypatch):
    posted = []
    monkeypatch.setattr(user_notification, "IOLoop", InlineIOLoop)
    monkeypatch.setattr(
        user_notification,
        "post_notification",
        lambda body, timeout=None: posted.append(body),
    )

    session = DBSession()
    analysis = session.get(ObjAnalysis, public_obj_analysis.id)
    analysis.status = "completed"
    session.commit()
    analysis.status_message = "results saved"
    session.commit()

    assert posted == [{"target_class_name": "ObjAnalysis", "target_id": analysis.id}]
