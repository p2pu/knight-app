from celery import shared_task

from django.contrib.auth.models import User
from django.conf import settings
from django.urls import reverse
from studygroups.utils import render_to_string_ctx
from django.utils.translation import gettext_lazy as _

import requests
from requests.auth import HTTPBasicAuth
import re
import json
import logging

from . import mailchimp

logger = logging.getLogger(__name__)


@shared_task
def send_announcement(sender, subject, body_text, body_html):
    """ Send message to all users that opted-in for the community email list """

    # Check that account settings link is present in message
    account_settings_url = settings.PROTOCOL + '://' + settings.DOMAIN + reverse('account_settings')

    # check if account settings URL is in HTML body
    if not re.search(account_settings_url, body_html):
        settings_link = render_to_string_ctx('announce/account_settings_email_link.html')
        # if there is a body tag, add link before the closing body tag
        if re.search('</body>', body_html):
            settings_link = settings_link + '</body>'
            body_html = re.sub(r'</body>', settings_link, body_html)
        else:
            settings_link = settings_link
            body_html = body_html + settings_link

    # check if account settings URL is in text body
    if not re.search(account_settings_url, body_text):
        settings_link = _('If you would no longer like to receive announcements from P2PU, you can update your account preferences at {url}').format(url=account_settings_url)
        body_text = '\n'.join([body_text, settings_link])

    # Get list of users who opted-in to communications
    users = User.objects.filter(is_active=True, profile__communication_opt_in=True)
    batch_size = 500

    # send in batches of batch_size
    url = 'https://api.mailgun.net/v3/{}/messages'.format(settings.MAILGUN_DOMAIN)
    auth = HTTPBasicAuth('api', settings.MAILGUN_API_KEY)

    for index in range(0, len(users), batch_size):
        to = users[index:index+batch_size]

        post_data = [
            ('from', sender),
            ('subject', subject),
            ('text', body_text),
            ('html', body_html),
            ('o:tracking', 'yes'),
            ('o:tracking-clicks', 'htmlonly'),
            ('o:tracking-opens', 'yes'),
            ('o:tag', 'announce'),
        ]

        post_data += [ ('to', u.email) for u in to ]
        # Add recipient variables to ensure mailgun sends messages individually and
        # not with everyone in the to field.
        post_data += [ ('recipient-variables', json.dumps({ u.email:{} for u in to })) ]
        resp = requests.post(url, auth=auth, data=post_data)
        if resp.status_code != 200:
            logger.error('Could not send mailgun batch email')


@shared_task
def update_mailchimp_subscription(user_id):
    user = User.objects.get(pk=user_id)
    if user.profile.communication_opt_in:
        mailchimp.add_member(user)
    else:
        mailchimp.archive_member(user)


@shared_task
def hard_delete_mailchimp_user(email):
    mailchimp.delete_member(email)
