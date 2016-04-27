import os
import requests


class FeedbackService(object):
    FEEDBACK_URL = os.environ.get('FEEDBACK_URL')

    def __init__(self, leap_session):
        self.leap_session = leap_session

    def open_ticket(self, feedback):
        account_mail = self.leap_session.account_email()
        data = {
            "ticket[comments_attributes][0][body]": feedback,
            "ticket[subject]": "Feedback user-agent from {0}".format(account_mail),
            "ticket[email]": account_mail,
            "ticket[regarding_user]": account_mail
        }

        return requests.post(self.FEEDBACK_URL, data=data, verify=False)
