# coding=utf-8
from django import forms
from django.conf import settings
from django.conf.global_settings import LANGUAGES
from django.utils.translation import ugettext as _
from django.utils import timezone
from django.contrib.auth.models import User
from django.template.loader import render_to_string
from studygroups.email_helper import render_html_with_css
from django.core.mail import EmailMultiAlternatives

from phonenumber_field.formfields import PhoneNumberField

from crispy_forms.helper import FormHelper
from crispy_forms.layout import Submit, Layout, Fieldset, HTML

import pytz, datetime, json

import twilio

from studygroups.models import Application
from studygroups.models import Reminder
from studygroups.models import StudyGroup
from studygroups.models import Meeting
from studygroups.models import Feedback
from studygroups.models import Course
from studygroups.sms import send_message

import logging

logger = logging.getLogger(__name__)


class ApplicationForm(forms.ModelForm):

    COMPUTER_ACCESS = (
        ('', _('Select one of the following')),
        ('Both', _('Both')),
        ('Just a laptop', _('Just a laptop')),
        ('Just headphones', _('Just headphones')),
        ('Neither', _('Neither')),
    )

    DIGITAL_LITERACY_CHOICES = (
        ('', _('Select one of the following')),
    ) + Application.DIGITAL_LITERACY_CHOICES

    GOAL_CHOICES = [
        ('', _('Select one of the following')),
        ('To increase my employability', _('To increase my employability')),
        ('Professional development for my current job', _('Professional development for my current job')),
        ('To accompany other educational programs', _('To accompany other educational programs')),
        ('Personal interest', _('Personal interest')),
        ('Social reasons', _('Social reasons')),
        ('For fun / to try something new', _('For fun / to try something new')),
        ('Other', _('Other')),
    ]
    mobile = PhoneNumberField(
        required=False,
        label=_('If you’d like to receive weekly text messages reminding you of upcoming learning circle meetings, put your phone number here:'),
        help_text=_('Your number won\'t be shared with other participants.')
    )
    computer_access = forms.ChoiceField(
        choices=COMPUTER_ACCESS,
        label=_('Can you bring a laptop and headphones to the learning circle each week?')
    )
    goals = forms.ChoiceField(
        label=_('What is your goal for taking this learning circle?'),
        choices=GOAL_CHOICES
    )
    goals_other = forms.CharField(
        label=_('If you selected other, could you specify?'),
        required=False
    )
    support = forms.CharField(
        label=_('A successful study group requires the support of all of its members. How will you help your peers achieve their goals?')
    )
    use_internet = forms.ChoiceField(
        label=Application.DIGITAL_LITERACY_QUESTIONS['use_internet'],
        choices=DIGITAL_LITERACY_CHOICES
    )


    def __init__(self, *args, **kwargs):
        self.helper = FormHelper()
        self.helper.layout = Layout(
            'study_group',
            'name',
            'email',
            'goals',
            'goals_other',
            'support',
            'computer_access',
            'use_internet',
            'mobile',
        )
        self.helper.add_input(Submit('submit', 'Submit'))
        super(ApplicationForm, self).__init__(*args, **kwargs)
        self.fields['email'].required = True
        study_group = kwargs.get('initial', {}).get('study_group')
        if study_group and study_group.country == 'United States of America':
            self.fields['mobile'].help_text += ' Ex. +1 281-234-5678'

        # add custom signup question if the facilitator specified one
        if study_group.signup_question:
            self.fields['custom_question'] = forms.CharField(label=study_group.signup_question)
            self.helper.layout.insert(len(self.helper.layout),'custom_question')


    def clean(self):
        cleaned_data = super(ApplicationForm, self).clean()
        # TODO - if mobile format is wrong, show error with example format for region
        if self.cleaned_data['goals'] == 'Other':
            if not self.cleaned_data.get('goals_other'):
                msg = _('This field is required.')
                self.add_error('goals_other', msg)

    def save(self, commit=True):
        signup_questions = {}
        questions = ['computer_access', 'goals', 'support', 'use_internet']
        for question in questions:
            signup_questions[question] = self.cleaned_data[question]

        if self.cleaned_data.get('goals') == 'Other':
            signup_questions['goals'] = 'Other: {}'.format(self.cleaned_data.get('goals_other'))

        # add custom signup question to signup_questions if the facilitator specified one
        if self.instance.study_group.signup_question:
            signup_questions['custom_question'] = self.cleaned_data['custom_question']
        self.instance.signup_questions = json.dumps(signup_questions)
        return super(ApplicationForm, self).save(commit)


    class Meta:
        model = Application
        fields = ['study_group', 'name', 'email', 'mobile']
        widgets = {'study_group': forms.HiddenInput}


class OptOutForm(forms.Form):
    email = forms.EmailField(help_text=_('Email address used to sign up.'), required=False)
    mobile = PhoneNumberField(required=False, label=_('Phone Number for SMS'), help_text=_('Phone number used to sign up.'))

    def clean(self):
        cleaned_data = super(OptOutForm, self).clean()
        email = cleaned_data.get('email')
        mobile = cleaned_data.get('mobile')

        if not email and not mobile:
            self.add_error('email', _('Please provide either the email address or the phone number used to sign up.'))

        conditions = [
            email and Application.objects.active().filter(email__iexact=email).count() > 0,
            mobile and Application.objects.active().filter(mobile=mobile).count() > 0
        ]

        if not any(conditions):
            raise forms.ValidationError(_('Could not find any signup matching your email address or phone number. Please make sure to enter the email or phone number you used to sign up.'))

    def send_optout_message(self):
        email = self.cleaned_data.get('email')
        mobile = self.cleaned_data.get('mobile')
        if email:
            for application in Application.objects.active().filter(email__iexact=email):
                # send opt-out email
                context = { 'application': application }
                subject = render_to_string('studygroups/email/optout_confirm-subject.txt', context).strip('\n')
                html_body = render_html_with_css('studygroups/email/optout_confirm.html', context)
                text_body = render_to_string('studygroups/email/optout_confirm.txt', context)
                notification = EmailMultiAlternatives(subject, text_body, settings.DEFAULT_FROM_EMAIL, [application.email])
                notification.attach_alternative(html_body, 'text/html')
                notification.send()


        # Find all signups with mobile with email and delete
        if mobile:
            applications = Application.objects.active().filter(mobile=mobile)
            if email:
                # don't send text to applications with a valid email in opt out form
                applications = applications.exclude(email__iexact=email)
            for application in applications:
                # This remains for old signups without email address
                context = { 'application': application }
                message = render_to_string('studygroups/email/optout_confirm_text.txt', context)
                try:
                    send_message(application.mobile, message)
                except twilio.TwilioRestException as e:
                    logger.exception("Could not send text message to %s", to, exc_info=e)
                application.delete()


class CourseForm(forms.ModelForm):
    LANGUAGES = (
        ('en', _('English')),
        ('es', _('Spanish')),
        ('fr', _('French')),
        ('other', [ (code, name) for code, name in LANGUAGES if code not in ['en', 'es', 'fr']]),
    )
    language = forms.ChoiceField(choices=LANGUAGES, initial='en')

    LICENSES = (
        ('', _('Not set')),
        ('All rights reserved', _('All rights reserved')),
        ('CC-BY', _('CC-BY')),
        ('CC-BY-SA', _('CC-BY-SA')),
        ('CC-BY-NC', _('CC-BY-NC')),
        ('CC-BY-NC-SA', _('CC-BY-NC-SA')),
        ('Public Domain', _('Public Domain')),
        ('Other', _('Other')),
        ('Not sure', _('Not sure')),
    )
    license = forms.ChoiceField(choices=LICENSES, initial='', required=False)


    def __init__(self, *args, **kwargs):
        super(CourseForm, self).__init__(*args, **kwargs)
        self.helper = FormHelper(self)
        if self.instance:
            self.helper.add_input(Submit('submit', 'Save'))
        else:
            self.helper.add_input(Submit('submit', 'Create course'))
        self.helper.layout.insert(4, HTML("""
            <p><label class="from-control requiredField">
                Availability<span class="asteriskField">*</span>
            </label></p>
        """))

    class Meta:
        model = Course
        fields = [
            'title',
            'provider',
            'link',
            'caption',
            'on_demand',
            'topics',
            'language',
            'license',
        ]
        labels = {
            'title': _('Course title'),
            'provider': _('Course creator'),
            'link': _('Course website'),
            'caption': _('Course description (200 character limit)'),
            'topic': _('Course topics'),
            'on_demand': _('Always available'),
            'license': _('Course license'),
        }
        help_texts = {
             'provider': _('e.g. MIT, University of Michigan, Khan Academy.'),
             'link': _('Paste full URL above.'),
             'caption': _('Write 1-2 sentences that describe what people will accomplish if they take this course. This description is what learners will see when signing up for learning circles, and what facilitators will see when selecting a course.'),
             'topics': _('Select or create a few topics that will help learners and future facilitators find this course.'),
             'on_demand': _('Select “always available” if the course is openly licensed or on-demand, meaning that there are no start and end dates for course availability.')
        }


class StudyGroupForm(forms.ModelForm):
    TIMEZONES = [('', _('Select one of the following')),] + list(zip(pytz.common_timezones, pytz.common_timezones))

    meeting_time = forms.TimeField(input_formats=['%I:%M %p'], label=_('What time will your learning circle meet each week?'), help_text=_('We recommend establishing a consistent weekly meeting time. You can always change individual meeting times from your Dashboard later.'), initial=datetime.time(16))
    weeks = forms.IntegerField(min_value=1, label=_('How many weeks will your learning circle run for?'), help_text=_('If you\'re not sure, six weeks is generally a good bet!'))
    timezone = forms.ChoiceField(choices=TIMEZONES, label=_('What timezone is your learning circle happening in?'))

    latitude = forms.DecimalField(required=False, widget=forms.HiddenInput)
    longitude = forms.DecimalField(required=False, widget=forms.HiddenInput)

    def __init__(self, *args, **kwargs):
        super(StudyGroupForm, self).__init__(*args, **kwargs)
        self.helper = FormHelper(self)
        if self.instance and self.instance.pk:
            self.helper.add_input(Submit('submit', 'Save'))
        else:
            self.helper.add_input(Submit('submit', 'Save draft'))
        self.helper.layout.insert(
            len(self.helper.layout),
            HTML("""<p>For inspiration, check out <a href="https://www.flickr.com/search/?license=2%2C3%2C4%2C5%2C6%2C9" target="_blank">openly licensed images on Flickr</a>.</p>""")
        )
        self.helper.layout.insert(1, HTML("""
            <p>You can learn more about each course and explore what other people are facilitating on the <a href="https://www.p2pu.org/en/courses/">courses page</a>.</p>
            <p>Or add an online course that isn&#39;t already listed.</p>
            <p><a class="btn btn-default" href="{% url 'studygroups_course_create' %}">Add a new course</a></p>
        """))

        if self.instance.pk:
            self.fields['weeks'].initial = self.instance.meeting_set.active().count()

    def save(self, commit=True):
        self.instance.end_date = self.cleaned_data['start_date'] + datetime.timedelta(weeks=self.cleaned_data['weeks'] - 1)
        return super(StudyGroupForm, self).save(commit)

    class Meta:
        model = StudyGroup
        fields = [
            'course',
            'city',
            'region',
            'country',
            'place_id',
            'latitude',
            'longitude',
            'venue_name',
            'venue_details',
            'venue_address',
            'start_date',
            'weeks',
            'meeting_time',
            'timezone',
            'duration',
            'description',
            'signup_question',
            'venue_website',
            'image',
            'facilitator_goal',
            'facilitator_concerns',
        ]
        labels = {
            'course': _('Choose the course that your learning circle will study.'),
            'description': _('Share a welcome message with potential learners.'),
            'venue_name': _('Where will you meet?'),
            'venue_details': _('Where is the specific meeting spot?'),
            'venue_address': _('What is the address of the venue?'),
            'city': _('In which city is this happening?'),
            'venue_website': _('Do you have a website you want to link to?'),
            'start_date': _('What is the date of the first learning circle?'),
            'duration': _('How long will each learning circle last (in minutes)?'),
            'image': _('Care to add an image?'),
            'signup_question': _('Is there another question that you want people to answer when they sign up for your learning circle? If so, write that here: '),
            'facilitator_goal': _('What are your personal goals as you facilitate this learning circle? '),
            'facilitator_concerns': _('What questions or concerns do you have about the learning circle? Is there anything that you want feedback on before you get started?'),

        }
        help_texts = {
            'course': '',
            'description': _('You can include a bit about yourself, why you’re facilitating this course, and anything else you want people to know before they sign up.'),
            'venue_name': _('Name of the venue, e.g. Pretoria Library or Bekka\'s house'),
            'venue_details': _('e.g. second floor kitchen or Room 409 (third floor)'),
            'venue_address': _('Write it out like you were mailing a letter.'),
            'city': _('This will be used for learners looking for learning circles by city.'),
            'venue_website': _('Link to any website that has more info about the venue or learning circle.'),
            'start_date': _('Give yourself at least 4 weeks to advertise, if possible.'),
            'duration': _('We recommend 90 - 120 minutes.'),
            'image': _('Make your learning circle stand out with a picture or .gif. It could be related to location, subject matter, or anything else you want to identify with!'),
        }
        widgets = {
            'latitude': forms.HiddenInput,
            'longitude': forms.HiddenInput,
            'place_id': forms.HiddenInput,
            'country': forms.HiddenInput,
            'region': forms.HiddenInput,
        }


class MeetingForm(forms.ModelForm):
    meeting_time = forms.TimeField(input_formats=['%I:%M %p'], initial=datetime.time(16))
    class Meta:
        model = Meeting
        fields = ['meeting_date', 'meeting_time', 'study_group']
        widgets = {'study_group': forms.HiddenInput}


class FeedbackForm(forms.ModelForm):
    class Meta:
        model = Feedback
        fields = ['study_group_meeting', 'feedback', 'reflection', 'attendance', 'rating']
        labels = {
            'feedback': _('For learners: Write a brief summary of this week\'s learning circle.'),
            'attendance': _('How many people attended?'),
            'reflection': _('For the rest of us: Anything you want to share?'),
            'rating': _('Overall, how would you say this week went?')
        }
        help_texts = {
            'feedback': _('You may want to include your impressions of how it went, plus/delta feedback, and anything the group agreed on having completed before the next meeting. This will be automatically sent to learners two days before next week\'s meeting.'),
            'reflection': _('What went well this week? What surprised you? Any funny stories? We\'ll pull what you write here into our community newsletters and updates.'),
        }
        widgets = {'study_group_meeting': forms.HiddenInput}
