from email.utils import parseaddr


def generate_recipients(sender, to, ccs, current_user):
    result = {'single': None, 'all': {'to-field': [], 'cc-field': []}}

    to.append(sender)
    to = remove_duplicates(to)
    ccs = remove_duplicates(ccs)

    result['single'] = swap_recipient_if_needed(
        sender, remove_address(to, current_user), current_user)
    result['all'][
        'to-field'] = remove_address(to, current_user) if len(to) > 1 else to
    result['all'][
        'cc-field'] = remove_address(ccs, current_user) if len(ccs) > 1 else ccs
    return result


def remove_duplicates(recipients):
    return list(set(recipients))


def remove_address(recipients, current_user):
    return [recipient for recipient in recipients if not parsed_mail_matches(recipient, current_user)]


def parsed_mail_matches(to_parse, expected):
    return parseaddr(to_parse)[1] == expected


def swap_recipient_if_needed(sender, recipients, current_user):
    if len(recipients) == 1 and parsed_mail_matches(sender, current_user):
        return recipients[0]
    return sender
