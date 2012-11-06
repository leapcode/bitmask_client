"""
mixins used in First Run Wizard
"""


class UserFormMixIn(object):

    def reset_validation_status(self):
        """
        empty the validation msg
        """
        self.validationMsg.setText('')

    def set_validation_status(self, msg):
        """
        set generic validation status
        """
        self.validationMsg.setText(msg)
