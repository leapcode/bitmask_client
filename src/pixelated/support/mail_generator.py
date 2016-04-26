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


from email.mime.text import MIMEText
from email.utils import formatdate
from random import Random
from pixelated.support.markov import MarkovGenerator
import re
from collections import Counter
import time


def filter_two_line_on_wrote(lines):
    skip_next = False
    if len(lines) > 0:
        for i in xrange(len(lines) - 1):
            if skip_next:
                skip_next = False
                continue

            if lines[i].startswith('On') and lines[i + 1].endswith('wrote:'):
                skip_next = True
            else:
                yield lines[i].strip()

        yield lines[-1]


def filter_lines(text):
    pattern = re.compile('\s*[>-].*')
    wrote_pattern = re.compile('\s*On.*wrote.*')

    lines = text.splitlines()

    lines = filter(lambda line: not pattern.match(line), lines)
    lines = filter(lambda line: not len(line.strip()) == 0, lines)
    lines = filter(lambda line: not wrote_pattern.match(line), lines)
    lines = filter(lambda line: not line.endswith('writes:'), lines)
    lines = filter(lambda line: ' ' in line.strip(), lines)

    lines = filter_two_line_on_wrote(lines)

    return ' '.join(lines)


def decode_multipart_mail_text(mail):
    for payload in mail.get_payload():
        if payload.get_content_type() == 'text/plain':
            return payload.get_payload(decode=True)
    return ''


def search_for_tags(content):
    words = content.split()

    only_alnum = filter(lambda word: word.isalnum(), words)
    only_longer = filter(lambda word: len(word) > 5, only_alnum)
    lower_case = map(lambda word: word.lower(), only_longer)

    counter = Counter(lower_case)
    potential_tags = counter.most_common(10)

    return map(lambda tag: tag[0], potential_tags)


def filter_too_short_texts(texts):
    return [text for text in texts if text is not None and len(text.split()) >= 3]


def load_all_mails(mail_list):
    subjects = set()
    mail_bodies = []

    for mail in mail_list:
        subjects.add(mail['Subject'])
        if mail.is_multipart():
            mail_bodies.append(filter_lines(decode_multipart_mail_text(mail)))
        else:
            if mail.get_content_type() == 'text/plain':
                mail_bodies.append(filter_lines(mail.get_payload(decode=True)))
            else:
                raise Exception(mail.get_content_type())

    return filter_too_short_texts(subjects), filter_too_short_texts(mail_bodies)


class MailGenerator(object):

    NAMES = ['alice', 'bob', 'eve']

    def __init__(self, receiver, domain_name, sample_mail_list, random=None):
        self._random = random if random else Random()
        self._receiver = receiver
        self._domain_name = domain_name
        self._subjects, self._bodies = load_all_mails(sample_mail_list)

        self._potential_tags = search_for_tags(' '.join(self._bodies))
        self._subject_markov = MarkovGenerator(
            self._subjects, random=self._random)
        self._body_markov = MarkovGenerator(
            self._bodies, random=self._random, add_paragraph_on_empty_chain=True)

    def generate_mail(self):
        body = self._body_markov.generate(150)
        mail = MIMEText(body)

        mail['Subject'] = self._subject_markov.generate(8)
        mail['To'] = '%s@%s' % (self._receiver, self._domain_name)
        mail['From'] = self._random_from()
        mail['Date'] = self._random_date()
        mail['X-Tags'] = self._random_tags()
        mail['X-Leap-Encryption'] = self._random_encryption_state()
        mail['X-Leap-Signature'] = self._random_signature_state()

        return mail

    def _random_date(self):
        now = int(time.time())
        ten_days = 60 * 60 * 24 * 10
        mail_time = self._random.randint(now - ten_days, now)

        return formatdate(mail_time)

    def _random_encryption_state(self):
        return self._random.choice(['true', 'decrypted'])

    def _random_signature_state(self):
        return self._random.choice(['could not verify', 'valid'])

    def _random_from(self):
        name = self._random.choice(
            filter(lambda name: name != self._receiver, MailGenerator.NAMES))

        return '%s@%s' % (name, self._domain_name)

    def _random_tags(self):
        barrier = 0.5
        tags = set()
        while self._random.random() > barrier:
            tags.add(self._random.choice(self._potential_tags))
            barrier += 0.15

        return ' '.join(tags)
