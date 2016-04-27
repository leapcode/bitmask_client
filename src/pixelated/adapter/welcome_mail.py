#
# Copyright (c) 2015 ThoughtWorks, Inc.
#
# Pixelated is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# Pixelated is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Affero General Public License for more details.
#
# You should have received a copy of the GNU Affero General Public License
# along with Pixelated. If not, see <http://www.gnu.org/licenses/>.
import pkg_resources
from email import message_from_file
from pixelated.adapter.model.mail import InputMail


def add_welcome_mail(mail_store):
    welcome_mail = pkg_resources.resource_filename(
        'pixelated.assets', 'welcome.mail')

    with open(welcome_mail) as mail_template_file:
        mail_template = message_from_file(mail_template_file)

    input_mail = InputMail.from_python_mail(mail_template)
    mail_store.add_mail('INBOX', input_mail.raw)
