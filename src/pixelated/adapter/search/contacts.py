#
# Copyright (c) 2014 ThoughtWorks, Inc.
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
from email.utils import parseaddr
from pixelated.support.functional import flatten
from whoosh.qparser import QueryParser
from whoosh import sorting
from whoosh.query import Term


def address_duplication_filter(contacts):
    contacts_by_mail = dict()

    for contact in contacts:
        mail_address = extract_mail_address(contact)
        current = contacts_by_mail.get(mail_address, '')
        current = contact if len(contact) > len(current) else current
        contacts_by_mail[mail_address] = current
    return contacts_by_mail.values()


def extract_mail_address(text):
    return parseaddr(text)[1]


def contacts_suggestions(query, searcher):
    return address_duplication_filter(search_addresses(searcher, query)) if query else []


def search_addresses(searcher, query):
    restrict_q = Term("tag", "drafts") | Term("tag", "trash")
    results = []
    for field in ['to', 'cc', 'bcc', 'sender']:
        query_parser = QueryParser(field, searcher.schema)
        results.append(
            searcher.search(
                query_parser.parse("*%s* OR *%s*" % (query.title(), query)),
                limit=None,
                mask=restrict_q,
                groupedby=sorting.FieldFacet(
                    field,
                    allow_overlap=True),
                terms=True).matched_terms())
    return [address[1] for address in flatten(results)]
