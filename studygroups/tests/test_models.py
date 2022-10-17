from django.test import TestCase
from django.core import mail
from django.contrib.auth.models import User
from django.utils import timezone
from django.utils.translation import get_language

from studygroups.models import Course
from studygroups.models import StudyGroup
from studygroups.models import Meeting
from studygroups.models import Application
from studygroups.models import Reminder
from studygroups.models import Rsvp
from studygroups.models import accept_application
from studygroups.models import create_rsvp
from studygroups.models import generate_all_meetings
from studygroups.models import generate_meetings_from_dates
from studygroups.utils import gen_rsvp_querystring
from studygroups.utils import check_rsvp_signature
from studygroups.utils import check_unsubscribe_signature
from studygroups.tasks import send_meeting_change_notification

from custom_registration.models import create_user

from unittest.mock import patch
from freezegun import freeze_time

import datetime
import pytz
import urllib.request
import urllib.parse
import urllib.error
import json


class MockChart():
    def generate():
        return "image"


# Create your tests here.
class TestSignupModels(TestCase):

    fixtures = ['test_courses.json', 'test_studygroups.json']

    APPLICATION_DATA = {
        'name': 'Test User',
        'email': 'test@mail.com',
        'signup_questions': json.dumps({
            'computer_access': 'Yes',
            'goals': 'try hard',
            'support': 'thinking how to?',
        }),
        'study_group': '1',
    }

    def setUp(self):
        user = create_user('admin@test.com', 'admin', 'b', 'password')
        user.is_staff = True
        user.save()
        mail.outbox = []

    def test_accept_application(self):
        # TODO remove this test
        self.assertEqual(Application.objects.active().count(), 0)
        data = self.APPLICATION_DATA
        data['study_group'] = StudyGroup.objects.get(pk=1)
        application = Application(**data)
        application.save()
        accept_application(application)
        self.assertEqual(Application.objects.active().count(), 1)

    def test_get_all_meeting_datetimes(self):
        # TODO
        return
        # setup test accross daylight savings time
        sg = StudyGroup.objects.get(pk=1)
        sg.timezone = 'US/Central'
        sg.meeting_time = datetime.time(16, 0)
        tz = pytz.timezone(sg.timezone)

        for i in range(56):
            start_date = datetime.date(2015, 1, 1) + datetime.timedelta(weeks=i)
            end_date = start_date + datetime.timedelta(weeks=5)
            sg.start_date = start_date
            sg.end_date = end_date
            meeting_times = get_all_meeting_times(sg)
            self.assertEqual(len(meeting_times), 6)
            self.assertEqual(meeting_times[0].date(), sg.start_date)
            self.assertEqual(meeting_times[-1].date(), sg.end_date)
            for meeting_time in meeting_times:
                self.assertEqual(datetime.time(16,0), meeting_time.time())

    def test_generate_all_meetings(self):
        now = timezone.now()
        self.assertEqual(Reminder.objects.all().count(), 0)
        sg = StudyGroup.objects.get(pk=1)
        sg.timezone = 'US/Central'
        sg.start_date = now.date() + datetime.timedelta(days=3)
        sg.meeting_time = datetime.time(16,0)
        sg.end_date = sg.start_date + datetime.timedelta(weeks=5)
        sg.save()
        sg = StudyGroup.objects.get(pk=1)
        self.assertEqual(Meeting.objects.all().count(),0)
        generate_all_meetings(sg)
        self.assertEqual(Meeting.objects.all().count(),6)
        self.assertEqual(sg.next_meeting().meeting_datetime().tzinfo.zone, 'US/Central')
        for meeting in Meeting.objects.all():
            self.assertEqual(meeting.meeting_datetime().time(), datetime.time(16,0))


    @freeze_time('2020-09-20')
    def test_generate_meetings_from_dates(self):
        sg = StudyGroup.objects.get(pk=1)
        sg.timezone = 'US/Central'
        meeting_dates = [
            { "meeting_date": datetime.date(2020, 9, 30), "meeting_time": datetime.time(16, 0)},
            { "meeting_date": datetime.date(2020, 10, 7), "meeting_time": datetime.time(16, 0)},
            { "meeting_date": datetime.date(2020, 10, 14), "meeting_time": datetime.time(16, 0)},
            { "meeting_date": datetime.date(2020, 10, 21), "meeting_time": datetime.time(16, 0)},
            { "meeting_date": datetime.date(2020, 10, 28), "meeting_time": datetime.time(16, 0)},
            { "meeting_date": datetime.date(2020, 11, 4), "meeting_time": datetime.time(16, 0)},
        ]
        sg_meetings_count = Meeting.objects.active().filter(study_group=sg).count()
        self.assertEqual(sg_meetings_count, 0)

        generate_meetings_from_dates(sg, meeting_dates)

        self.assertEqual(sg.meeting_set.count(), 6)
        self.assertEqual(sg.next_meeting().meeting_datetime().tzinfo.zone, 'US/Central')

        for date in meeting_dates:
            meeting_date = date['meeting_date']
            self.assertTrue(Meeting.objects.active().filter(study_group=sg, meeting_date=meeting_date).exists())

        # update meetings
        new_meeting_dates = [
            { "meeting_date": datetime.date(2020, 10, 7), "meeting_time": datetime.time(16, 0)},
            { "meeting_date": datetime.date(2020, 10, 14), "meeting_time": datetime.time(16, 0)},
            { "meeting_date": datetime.date(2020, 10, 21), "meeting_time": datetime.time(16, 0)},
            { "meeting_date": datetime.date(2020, 10, 28), "meeting_time": datetime.time(16, 0)},
            { "meeting_date": datetime.date(2020, 11, 4), "meeting_time": datetime.time(16, 0)},
            { "meeting_date": datetime.date(2020, 11, 5), "meeting_time": datetime.time(16, 0)},
        ]
        generate_meetings_from_dates(sg, new_meeting_dates)

        sg = StudyGroup.objects.get(pk=1)
        self.assertEqual(sg.meeting_set.active().count(), 6)
        self.assertEqual(sg.reminder_set.count(), 6)
        self.assertFalse(Meeting.objects.active().filter(study_group=sg, meeting_date="2020-09-30").exists())
        self.assertTrue(Meeting.objects.active().filter(study_group=sg, meeting_date="2020-11-05").exists())


    def test_unapply_signing(self):
        data = self.APPLICATION_DATA
        data['study_group'] = StudyGroup.objects.all().first()
        application = Application(**data)
        application.save()
        qs = application.unapply_link()
        qs = qs[qs.index('?')+1:]
        sig = urllib.parse.parse_qs(qs).get('sig')[0]
        self.assertTrue(check_unsubscribe_signature(application.pk, sig))
        self.assertFalse(check_unsubscribe_signature(application.pk+1, sig))

    def test_rsvp_signing(self):
        meeting_date = timezone.datetime(2015,9,17,17,0, tzinfo=timezone.utc)
        qs = gen_rsvp_querystring('test@mail.com', '1', meeting_date, 'yes')
        sig = urllib.parse.parse_qs(qs).get('sig')[0]
        self.assertTrue(check_rsvp_signature('test@mail.com', '1', meeting_date, 'yes', sig))
        self.assertFalse(check_rsvp_signature('tes@mail.com', '1', meeting_date, 'yes', sig))
        self.assertFalse(check_rsvp_signature('test@mail.com', '2', meeting_date, 'yes', sig))
        self.assertFalse(check_rsvp_signature('test@mail.com', '1', meeting_date, 'no', sig))
        meeting_date = timezone.datetime(2015,9,18,17,0, tzinfo=timezone.utc)
        self.assertFalse(check_rsvp_signature('test@mail.com', '1', meeting_date, 'yes', sig))

    def test_create_rsvp(self):
        data = self.APPLICATION_DATA
        data['study_group'] = StudyGroup.objects.get(pk=1)
        application = Application(**data)
        application.save()
        sg = StudyGroup.objects.get(pk=1)
        meeting_date = timezone.now()
        sgm = Meeting(
            study_group=sg,
            meeting_time=meeting_date.time(),
            meeting_date=meeting_date.date()
        )
        sgm.save()
        sgm = Meeting(
            study_group=sg,
            meeting_time=meeting_date.time(),
            meeting_date=meeting_date.date() + datetime.timedelta(weeks=1)
        )
        sgm.save()

        # Test creating an RSVP
        self.assertEqual(Rsvp.objects.all().count(), 0)
        create_rsvp('test@mail.com', sg.id, meeting_date, 'yes')
        self.assertEqual(Rsvp.objects.all().count(), 1)
        self.assertTrue(Rsvp.objects.all().first().attending)

        # Test updating an RSVP
        create_rsvp('test@mail.com', sg.id, meeting_date, 'no')
        self.assertEqual(Rsvp.objects.all().count(), 1)
        self.assertFalse(Rsvp.objects.all().first().attending)

    def test_new_study_group_email(self):
        facilitator = create_user('facil@test.com', 'facil', 'itate', 'password')
        mail.outbox = []
        sg = StudyGroup(
            course=Course.objects.first(),
            created_by=facilitator,
            description='blah',
            venue_name='ACME publich library',
            venue_address='ACME rd 1',
            venue_details='venue_details',
            city='city',
            latitude=0,
            longitude=0,
            start_date=datetime.date(2010,1,1),
            end_date=datetime.date(2010,1,1) + datetime.timedelta(weeks=6),
            meeting_time=datetime.time(12,0),
            duration=90,
            timezone='SAST',
            facilitator_goal='the_facilitator_goal',
            facilitator_concerns='the_facilitators_concerns'
        )
        sg.save()
        self.assertEqual(len(mail.outbox), 1)
        self.assertIn('the_facilitator_goal', mail.outbox[0].body)
        self.assertIn('the_facilitators_concerns', mail.outbox[0].body)

    @patch('studygroups.tasks.send_message')
    def test_meeting_change_notification(self, send_message):
        sg = StudyGroup.objects.first()
        data = self.APPLICATION_DATA
        data['study_group'] = sg
        Application(**{**data, "email": "signup1@mail.com"}).save()
        Application(**{**data, "email": "signup2@mail.com"}).save()
        Application(**{**data, "email": "", "mobile": "+27713213213"}).save()
        list(map(lambda app: accept_application(app), Application.objects.all()))
        self.assertEqual(Application.objects.all().count(), 3)
        generate_all_meetings(sg)
        meeting = sg.meeting_set.first()
        old_meeting_datetime = meeting.meeting_datetime()
        meeting.meeting_date = datetime.date(2019, 4, 1)
        meeting.save()
        old_meeting = sg.meeting_set.first()
        mail.outbox = []
        send_meeting_change_notification(meeting.pk, str(old_meeting_datetime))
        self.assertEqual(len(mail.outbox), 1)
        self.assertEqual(len(mail.outbox[0].bcc), 2)
        self.assertIn('signup1@mail.com', mail.outbox[0].bcc)
        self.assertIn('signup2@mail.com', mail.outbox[0].bcc)
        self.assertEqual(meeting.meeting_time, datetime.time(18, 30))
        self.assertEqual(mail.outbox[0].subject, 'Your learning circle on Monday, 23 March, 6:30PM has been rescheduled')
        send_message.assert_called_with('+27713213213', 'Your learning circle on Monday, 23 March, 6:30PM is now on Monday, 1 April, 6:30PM. Reply STOP to unsubscribe.')

