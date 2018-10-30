# coding=utf-8
from django.db import models
from django.utils import timezone
from django.utils.translation import ugettext_lazy as _
from django.utils.text import slugify
from django.core.serializers.json import DjangoJSONEncoder
from django.conf import settings
from django.contrib.auth.models import User
from django.urls import reverse  # TODO ideally this shouldn't be in the model
from django.http import HttpResponse

from studygroups import rsvp

from studygroups.utils import gen_unsubscribe_querystring

import calendar
import datetime
import pytz
import re
import json
import urllib.request, urllib.parse, urllib.error
import uuid
import requests


# TODO - remove this
STUDY_GROUP_NAMES = [
    "The Riders",
    "The Master Minds of Mars",
    "The Efficiency Experts",
    "The Red Hawks",
    "The Bandits of Hell's Bend",
    "Apache Devils",
    "The Wizards of Venus",
    "Swords of Mars",
    "The Beasts of Tarzan",
    "Tarzan and the Castaways",
    "Pirates of Venus",
    "The People that Time Forgot",
    "The Eternal Lovers"
]


def _study_group_name():
    idx = 1 + StudyGroup.objects.count()
    num_names = len(STUDY_GROUP_NAMES)
    return ' '.join([STUDY_GROUP_NAMES[idx % num_names], "I"*(idx//num_names)])


class SoftDeleteQuerySet(models.QuerySet):

    def active(self):
        return self.filter(deleted_at__isnull=True)

    def delete(self, *args, **kwargs):
        # Stop bulk deletes
        self.update(deleted_at=timezone.now())
        #TODO: check if we need to set any flags on the query set after the delete


class LifeTimeTrackingModel(models.Model):
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    deleted_at = models.DateTimeField(null=True, blank=True)

    objects = SoftDeleteQuerySet.as_manager()

    def delete(self, *args, **kwargs):
        # Don't actually delete the object, affects django admin also
        self.deleted_at = timezone.now()
        self.save()

    class Meta:
        abstract = True


class Course(LifeTimeTrackingModel):
    title = models.CharField(max_length=128)
    provider = models.CharField(max_length=256)
    link = models.URLField()
    caption = models.CharField(max_length=200)
    on_demand = models.BooleanField()
    topics = models.CharField(max_length=500)
    language = models.CharField(max_length=6)
    created_by = models.ForeignKey(User, blank=True, null=True, on_delete=models.CASCADE)
    unlisted = models.BooleanField(default=False)
    license = models.CharField(max_length=128, blank=True)


    def __str__(self):
        return self.title


# TODO move to custom_registration/models.py
class Profile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    mailing_list_signup = models.BooleanField(default=False)
    email_confirmed_at = models.DateTimeField(null=True, blank=True)
    interested_in_learning = models.CharField(max_length=500, blank=True, null=True)
    communication_opt_in = models.BooleanField(default=False)

    def __str__(self):
        return self.user.__str__()


# TODO remove organizer model - only use Facilitator model + Team Membership
class Organizer(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)

    def __str__(self):
        return self.user.__str__()


class Team(models.Model):
    name = models.CharField(max_length=128)
    page_slug = models.SlugField(max_length=256, blank=True)
    page_image = models.ImageField(blank=True)

    def __str__(self):
        return self.name


class TeamMembership(models.Model):
    ORGANIZER = 'ORGANIZER'
    MEMBER = 'MEMBER'
    ROLES = (
        (ORGANIZER, _('Organizer')),
        (MEMBER, _('Member')),
    )
    team = models.ForeignKey('studygroups.Team', on_delete=models.CASCADE)
    user = models.OneToOneField(User, on_delete=models.CASCADE) # TODO should this be a OneToOneField?
    role = models.CharField(max_length=256, choices=ROLES)

    def __str__(self):
        return 'Team membership: {}'.format(self.user.__str__())


class TeamInvitation(models.Model):
    """ invittion for users to join a team """
    team = models.ForeignKey('studygroups.Team', on_delete=models.CASCADE)
    organizer = models.ForeignKey(User, on_delete=models.CASCADE) # organizer who invited the user
    email = models.EmailField()
    role = models.CharField(max_length=256, choices=TeamMembership.ROLES)
    created_at = models.DateTimeField(auto_now_add=True)
    responded_at = models.DateTimeField(null=True, blank=True)
    joined = models.NullBooleanField(null=True)

    def __str__(self):
        return 'Invatation <{} to join {}>'.format(self.email, self.team.name)


class StudyGroupQuerySet(SoftDeleteQuerySet):

    def published(self):
        """ exclude drafts from public learning circles """
        return self.active().filter(draft=False)


class StudyGroup(LifeTimeTrackingModel):
    name = models.CharField(max_length=128, default=_study_group_name)
    course = models.ForeignKey('studygroups.Course', on_delete=models.CASCADE)
    description = models.CharField(max_length=500)
    venue_name = models.CharField(max_length=256)
    venue_address = models.CharField(max_length=256)
    venue_details = models.CharField(max_length=128)
    venue_website = models.URLField(blank=True)
    city = models.CharField(max_length=256)
    region = models.CharField(max_length=256, blank=True) # schema.org. Algolia => administrative
    country = models.CharField(max_length=256, blank=True)
    latitude = models.DecimalField(max_digits=8, decimal_places=6, null=True, blank=True)
    longitude = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    place_id = models.CharField(max_length=256, blank=True) # Algolia place_id
    facilitator = models.ForeignKey(User, on_delete=models.CASCADE)
    start_date = models.DateField()
    meeting_time = models.TimeField()
    end_date = models.DateField() # TODO consider storing number of weeks/meetings instead of end_date
    duration = models.IntegerField(default=90) # meeting duration in minutes
    timezone = models.CharField(max_length=128)
    signup_open = models.BooleanField(default=True)
    draft = models.BooleanField(default=True)
    image = models.ImageField(blank=True)
    signup_question = models.CharField(max_length=256, blank=True)
    facilitator_goal = models.CharField(max_length=256, blank=True)
    facilitator_concerns = models.CharField(max_length=256, blank=True)
    uuid = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)
    facilitator_rating = models.IntegerField(blank=True, null=True)
    attach_ics = models.BooleanField(default=True)

    objects = StudyGroupQuerySet.as_manager()

    def day(self):
        return calendar.day_name[self.start_date.weekday()]

    def end_time(self):
        q = datetime.datetime.combine(self.start_date, self.meeting_time) + datetime.timedelta(minutes=self.duration)
        return q.time()

    def next_meeting(self):
        now = timezone.now()
        meeting_list = self.meeting_set.active().order_by('meeting_date', 'meeting_time')
        return next((m for m in meeting_list if m.meeting_datetime() > now), None)

    def local_start_date(self):
        tz = pytz.timezone(self.timezone)
        date = datetime.datetime.combine(self.start_date, self.meeting_time)
        return tz.localize(date)

    def timezone_display(self):
        return self.local_start_date().strftime("%Z")

    def last_meeting(self):
        return self.meeting_set.active().order_by('-meeting_date', '-meeting_time').first()

    def first_meeting(self):
        return self.meeting_set.active().order_by('meeting_date', 'meeting_time').first()

    def report_url(self):
        domain = 'https://{0}'.format(settings.DOMAIN)
        path = reverse('studygroups_final_report', kwargs={'study_group_id': self.id})

        return domain + path

    @property
    def weeks(self):
        return (self.end_date - self.start_date).days//7 + 1


    def to_dict(self):
        sg = self  # TODO - this logic is repeated in the API class
        data = {
            "id": sg.pk,
            "course": sg.course.id,
            "course_title": sg.course.title,
            "description": sg.description,
            "venue_name": sg.venue_name,
            "venue_details": sg.venue_details,
            "venue_address": sg.venue_address,
            "venue_website": sg.venue_website,
            "city": sg.city,
            "region": sg.region,
            "country": sg.country,
            "latitude": sg.latitude,
            "longitude": sg.longitude,
            "place_id": sg.place_id,
            "start_date": sg.start_date,
            "weeks": sg.weeks,
            "meeting_time": sg.meeting_time.strftime('%H:%M'),
            "duration": sg.duration,
            "timezone": sg.timezone,
            "timezone_display": sg.timezone_display(),
            "signup_question": sg.signup_question,
            "facilitator_goal": sg.facilitator_goal,
            "facilitator_concerns": sg.facilitator_concerns,
            "day": sg.day(),
            "end_time": sg.end_time(),
            "facilitator": sg.facilitator.first_name + " " + sg.facilitator.last_name,
            "signup_count": sg.application_set.count(),
            "draft": sg.draft,
            "url": reverse('studygroups_view_study_group', args=(sg.id,)),
            "signup_url": reverse('studygroups_signup', args=(slugify(sg.venue_name, allow_unicode=True), sg.id,)),
        }
        next_meeting = self.next_meeting()
        if next_meeting:
            data['next_meeting_date'] = next_meeting.meeting_date
        if sg.image:
            data["image_url"] = sg.image.url
        return data

    def to_json(self):
        return json.dumps(self.to_dict(), cls=DjangoJSONEncoder)


    def __str__(self):
        return '{0} - {1}s {2} at the {3}'.format(self.course.title, self.day(), self.meeting_time, self.venue_name)


class Application(LifeTimeTrackingModel):
    study_group = models.ForeignKey('studygroups.StudyGroup', on_delete=models.CASCADE)
    name = models.CharField(max_length=128)
    email = models.EmailField(verbose_name='Email address', blank=True)
    mobile = models.CharField(max_length=20, blank=True)
    mobile_opt_out_at = models.DateTimeField(blank=True, null=True)
    signup_questions = models.TextField(default='{}')
    goal_met = models.SmallIntegerField(null=True)
    accepted_at = models.DateTimeField(blank=True, null=True)
    uuid = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)

    def __str__(self):
        return "{0} <{1}>".format(self.name, self.email if self.email else self.mobile)

    def unapply_link(self):
        domain = 'https://{0}'.format(settings.DOMAIN)
        url = reverse('studygroups_leave')
        qs = gen_unsubscribe_querystring(self.pk)
        return '{0}{1}?{2}'.format(domain, url, qs)

    def get_signup_questions(self):
        return json.loads(self.signup_questions)

    DIGITAL_LITERACY_QUESTIONS = {
        'use_internet': _('How comfortable are you using the internet?'),
        'send_email': _('Send an email'),
        'delete_spam': _('Delete spam email'),
        'search_online': _('Find stuff online using Google'),
        'browse_video': _('Watch a video on Youtube'),
        'online_shopping': _('Fill out an application form or buy something online'),
        'mobile_apps': _('Use a mobile app'),
        'web_safety': _('Evaluate whether a website is safe/can be trusted')
    }

    DIGITAL_LITERACY_CHOICES = (
        ('0', _('Can\'t do')),
        ('1', _('Need help doing')),
        ('2', _('Can do with difficulty')),
        ('3', _('Can do')),
        ('4', _('Expert (can teach others)')),
    )

    def digital_literacy_for_display(self):
        answers = json.loads(self.signup_questions)
        return { q: {'question_text': text, 'answer': answers.get(q), 'answer_text': dict(self.DIGITAL_LITERACY_CHOICES).get(answers.get(q)) if q in answers else ''} for q, text in list(self.DIGITAL_LITERACY_QUESTIONS.items()) if answers.get(q) }


class Meeting(LifeTimeTrackingModel):
    study_group = models.ForeignKey('studygroups.StudyGroup', on_delete=models.CASCADE)
    meeting_date = models.DateField()
    meeting_time = models.TimeField()

    def meeting_number(self):
        # TODO this will break for two meetings on the same day
        return Meeting.objects.active().filter(meeting_date__lte=self.meeting_date, study_group=self.study_group).count()

    def meeting_datetime(self):
        tz = pytz.timezone(self.study_group.timezone)
        return tz.localize(datetime.datetime.combine(self.meeting_date, self.meeting_time))

    def meeting_datetime_end(self):
        tz = pytz.timezone(self.study_group.timezone)
        start = tz.localize(datetime.datetime.combine(self.meeting_date, self.meeting_time))
        return start + datetime.timedelta(minutes=self.study_group.duration)

    def rsvps(self):
        return {
            'yes': self.rsvp_set.all().filter(attending=True),
            'no': self.rsvp_set.all().filter(attending=False)
        }

    def rsvp_yes_link(self, email):
        domain = 'https://{0}'.format(settings.DOMAIN)
        url = reverse('studygroups_rsvp')
        yes_qs = rsvp.gen_rsvp_querystring(
            email,
            self.study_group.pk,
            self.meeting_datetime(),
            'yes'
        )
        return '{0}{1}?{2}'.format(domain, url, yes_qs)

    def rsvp_no_link(self, email):
        domain = 'https://{0}'.format(settings.DOMAIN)
        url = reverse('studygroups_rsvp')
        no_qs = rsvp.gen_rsvp_querystring(
            email,
            self.study_group.pk,
            self.meeting_datetime(),
            'no'
        )
        return '{0}{1}?{2}'.format(domain,url,no_qs)

    def __str__(self):
        # TODO i18n
        tz = pytz.timezone(self.study_group.timezone)
        return '{0}, {1} at {2}'.format(self.study_group.course.title, self.meeting_datetime(), self.study_group.venue_name)

    def to_json(self):
        data = {
            'study_group': self.study_group.pk,
            'meeting_date': self.meeting_date,
            'meeting_time': self.meeting_time
        }
        return json.dumps(data, cls=DjangoJSONEncoder)


class Reminder(models.Model):
    study_group = models.ForeignKey('studygroups.StudyGroup', on_delete=models.CASCADE)
    study_group_meeting = models.ForeignKey('studygroups.Meeting', blank=True, null=True, on_delete=models.CASCADE) #TODO check this makes sense
    email_subject = models.CharField(max_length=256)
    email_body = models.TextField()
    sms_body = models.CharField(verbose_name=_('SMS (Text)'), max_length=160, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    sent_at = models.DateTimeField(blank=True, null=True)


class Rsvp(models.Model):
    study_group_meeting = models.ForeignKey('studygroups.Meeting', on_delete=models.CASCADE)
    application = models.ForeignKey('studygroups.Application', on_delete=models.CASCADE)
    attending = models.BooleanField()

    def __str__(self):
        return '{0} ({1})'.format(self.application, 'yes' if self.attending else 'no')


class Feedback(LifeTimeTrackingModel):

    BAD = '1'
    NOT_SO_GOOD = '2'
    GOOD = '3'
    WELL = '4'
    GREAT = '5'

    RATING = [
        (GREAT, _('Great')),
        (WELL, _('Pretty well')),
        (GOOD, _('Good')),
        (NOT_SO_GOOD, _('Not so great')),
        (BAD, _('I need some help')),
    ]

    study_group_meeting = models.ForeignKey('studygroups.Meeting', on_delete=models.CASCADE) # TODO should this be a OneToOneField?
    feedback = models.TextField() # Shared with learners
    attendance = models.PositiveIntegerField()
    reflection = models.TextField() # Not shared
    rating = models.CharField(choices=RATING, max_length=16)


def accept_application(application):
    # add a study group application to a study group
    application.accepted_at = timezone.now()
    application.save()


def application_mobile_opt_out(mobile):
    """ Opt-out user with given mobile number """
    applications = Application.objects.active().filter(
        mobile=mobile, mobile_opt_out_at__isnull=True
    )
    applications.update(mobile_opt_out_at=timezone.now())
    # TODO smarter handling for multiple applications


def application_mobile_opt_out_revert(mobile):
    """ Cancel opt-out for applications with given mobile number """
    applications = Application.objects.active().filter(
        mobile=mobile, mobile_opt_out_at__isnull=False
    )
    applications.update(mobile_opt_out_at=None)


def create_rsvp(contact, study_group, meeting_datetime, attending):
    # expect meeting_date as python datetime
    # contact is an email address of mobile number
    # study_group is the study group id
    study_group_meeting = Meeting.objects.get(study_group__id=study_group, meeting_date=meeting_datetime.date(), meeting_time=meeting_datetime.time())
    application = None
    if '@' in contact:
        application = Application.objects.active().get(study_group__id=study_group, email__iexact=contact)
    else:
        application = Application.objects.active().get(study_group__id=study_group, mobile=contact)
    rsvp = Rsvp.objects.all().filter(study_group_meeting=study_group_meeting, application=application).first()
    if not rsvp:
        rsvp = Rsvp(study_group_meeting=study_group_meeting, application=application, attending=attending=='yes')
    else:
        rsvp.attending = attending=='yes'
    rsvp.save()
    return rsvp


def generate_all_meetings(study_group):
    if Meeting.objects.filter(study_group=study_group).exists():
        raise Exception(_('Meetings already exist for this study group'))

    meeting_date = study_group.start_date
    while meeting_date <= study_group.end_date:
        meeting = Meeting(
            study_group=study_group,
            meeting_date=meeting_date,
            meeting_time=study_group.meeting_time
        )
        meeting.save()
        meeting_date += datetime.timedelta(days=7)


def get_all_meeting_times(study_group):
    # sorted ascending according to date
    # times are in the study group timezone
    # meeting time stays constant, eg 18:00 stays 18:00 even when daylight savings changes
    tz = pytz.timezone(study_group.timezone)
    meeting_date = study_group.start_date
    meetings = []
    while meeting_date <= study_group.end_date:
        next_meeting = tz.localize(datetime.datetime.combine(meeting_date, study_group.meeting_time))
        meetings += [next_meeting]
        meeting_date += datetime.timedelta(days=7)
    return meetings


def get_study_group_organizers(study_group):
    """ Return the organizers for the study group """
    team_membership = TeamMembership.objects.filter(user=study_group.facilitator)
    if team_membership.count() == 1:
        organizers = team_membership.first().team.teammembership_set.filter(role=TeamMembership.ORGANIZER).values('user')
        return User.objects.filter(pk__in=organizers)
    return []


def get_team_users(user):
    """ Return the team members for a user """
    # TODO this function doesn't make sense - only applies for logged in users
    # change functionality or rename to get_team_mates
    team_membership = TeamMembership.objects.filter(user=user)
    if team_membership.count() == 1:
        members = team_membership.first().team.teammembership_set.values('user')
        return User.objects.filter(pk__in=members)
    return []


""" Return the team a user belongs to """
def get_user_team(user):
    team_membership = TeamMembership.objects.filter(user=user).get()
    return team_membership.team


def report_data(start_time, end_time, team=None):
    """ Return data for the indicated time period

    If team is given, study groups will be filtered by team
    """
    study_groups = StudyGroup.objects.published()
    meetings = Meeting.objects.active()\
            .filter(meeting_date__gte=start_time, meeting_date__lt=end_time)\
            .filter(study_group__in=study_groups)

    new_study_groups = StudyGroup.objects.published()\
            .filter(created_at__gte=start_time, created_at__lt=end_time)
    new_facilitators = User.objects.filter(date_joined__gte=start_time, date_joined__lt=end_time)
    logins = User.objects.filter(last_login__gte=start_time, last_login__lt=end_time)
    signups = Application.objects.active().filter(created_at__gte=start_time, created_at__lt=end_time)
    new_courses = Course.objects.active().filter(created_at__gte=start_time, created_at__lt=end_time)

    if team:
        members = team.teammembership_set.all().values('user')
        logins = logins.filter(pk__in=members)
        new_courses = new_courses.filter(created_by__in=members)
        new_study_groups = new_study_groups.filter(facilitator__in=members)
        signups = signups.filter(study_group__facilitator__in=members)
        meetings = meetings.filter(study_group__facilitator__in=members)
        study_groups = study_groups.filter(facilitator__in=members)


    meeting_check = lambda mtg: mtg and mtg.meeting_date >= start_time.date() and mtg.meeting_date < end_time.date()

    finished_study_groups = [sg for sg in study_groups if meeting_check(sg.meeting_set.active().order_by('-meeting_date').first())]

    feedback = Feedback.objects.filter(study_group_meeting__in=meetings)

    active = any([
        len(meetings) > 0,
        len(feedback) > 0,
        len(new_study_groups) > 0,
        len(finished_study_groups) > 0,
        len(new_facilitators) > 0,
        len(new_courses) > 0,
        len(signups) > 0,
    ])

    report = {
        'active': active,
        'meetings': meetings,
        'feedback': feedback,
        'study_groups': new_study_groups,
        'finished_study_groups': finished_study_groups,
        'facilitators': new_facilitators,
        'courses': new_courses,
        'logins': logins,
        'signups': signups,
    }
    if team:
        report['team'] = team
    return report


