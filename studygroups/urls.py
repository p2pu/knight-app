from django.conf.urls import url
from django.views.generic import TemplateView
from django.views.generic.base import RedirectView

from studygroups.views import MeetingCreate
from studygroups.views import MeetingUpdate
from studygroups.views import MeetingDelete
from studygroups.views import ApplicationCreateMultiple
from studygroups.views import ApplicationDelete
from studygroups.views import ApplicationUpdate
from studygroups.views import SignupSuccess
from studygroups.views import CoursePage
from studygroups.views import CourseReviewsPage
from studygroups.views import CourseCreate
from studygroups.views import CourseUpdate
from studygroups.views import CourseDelete
from studygroups.views import StudyGroupCreate
from studygroups.views import StudyGroupCreateLegacy
from studygroups.views import StudyGroupUpdate
from studygroups.views import StudyGroupUpdateLegacy
from studygroups.views import StudyGroupDelete
from studygroups.views import StudyGroupToggleSignup
from studygroups.views import StudyGroupPublish
from studygroups.views import StudyGroupList
from studygroups.views import StudyGroupLearnerSurvey
from studygroups.views import StudyGroupFacilitatorSurvey
from studygroups.views import StudyGroupDidNotHappen
from studygroups.views import LeaveTeam
from studygroups.views import TeamMembershipDelete
from studygroups.views import TeamInvitationCreate
from studygroups.views import InvitationConfirm
from studygroups.views import OptOutView
from studygroups.views import TeamPage
from studygroups.views import ExportSignupsView
from studygroups.views import ExportFacilitatorsView
from studygroups.views import ExportStudyGroupsView
from studygroups.views import ExportCoursesView
from studygroups.views import StaffDashView
from studygroups.views import StatsDashView
from studygroups.views import StudyGroupFinalReport
from studygroups.views import CommunityDigestView
from studygroups.views import DigestGenerateView
from studygroups.views import FacilitatorDashboard
from studygroups.views import OrganizerGuideForm
from studygroups.views import TeamUpdate
from studygroups.views import MessageView
from studygroups.views import MeetingRecap
from studygroups.views import MeetingRecapDismiss

from . import views

urlpatterns = [
    url(r'^$', FacilitatorDashboard.as_view(), name='studygroups_facilitator'),

    url(r'^courses/$', RedirectView.as_view(url='https://www.p2pu.org/en/courses/'), name='studygroups_courses'),

    url(r'^city/(?P<city_name>[\w\W\ ,]+)/$', views.city, name='studygroups_city'),

    url(r'^studygroups/$', views.studygroups, name='studygroups_search'),

    url(r'^login_redirect/$', views.login_redirect, name='studygroups_login_redirect'),

    url(r'^signup/(?P<location>[\w-]+)-(?P<study_group_id>[\d]+)/$', views.signup, name='studygroups_signup'),
    url(r'^signup/(?P<study_group_id>[\d]+)/success/$', SignupSuccess.as_view(), name='studygroups_signup_success'),

    url(r'^studygroup/create/$', StudyGroupCreate.as_view(), name='studygroups_facilitator_studygroup_create'),
    url(r'^studygroup/create/legacy/$', StudyGroupCreateLegacy.as_view(), name='studygroups_studygroup_create_legacy'),
    url(r'^studygroup/(?P<study_group_id>[\d]+)/$', views.view_study_group, name='studygroups_view_study_group'),
    url(r'^studygroup/(?P<study_group_id>[\d]+)/learn/$', views.StudyGroupParticipantView.as_view(), name='studygroups_view_learning_circle_participant'),
    url(r'^studygroup/(?P<study_group_id>[\d]+)/edit/$', StudyGroupUpdate.as_view(), name='studygroups_edit_study_group'),
    url(r'^studygroup/(?P<study_group_id>[\d]+)/edit/legacy/$', StudyGroupUpdateLegacy.as_view(), name='studygroups_studygroup_edit_legacy'),
    url(r'^studygroup/(?P<study_group_id>[\d]+)/delete/$', StudyGroupDelete.as_view(), name='studygroups_studygroup_delete'),
    url(r'^studygroup/(?P<study_group_id>[\d]+)/toggle_signup/$', StudyGroupToggleSignup.as_view(), name='studygroups_studygroup_toggle_signup'),

    url(r'^studygroup/(?P<study_group_id>[\d]+)/publish/$', StudyGroupPublish.as_view(), name='studygroups_studygroup_publish'),
    url(r'^studygroup/(?P<study_group_id>[\d]+)/did_not_happen/$', StudyGroupDidNotHappen.as_view(), name='studygroups_studygroup_did_not_happen'),

    url(r'^studygroup/(?P<study_group_id>[\d]+)/message/compose/$', views.message_send, name='studygroups_message_send'),
    url(r'^studygroup/(?P<study_group_id>[\d]+)/message/edit/(?P<message_id>[\d]+)/$', views.message_edit, name='studygroups_message_edit'),

    url(r'^studygroup/(?P<study_group_id>[\d]+)/message/(?P<pk>[\d]+)/$', MessageView.as_view(), name='studygroups_message_view'),

    url(r'^studygroup/(?P<study_group_id>[\d]+)/learner/add/$', views.add_learner, name='studygroups_add_learner'),
    url(r'^studygroup/(?P<study_group_id>[\d]+)/learner/add-multiple/$', ApplicationCreateMultiple.as_view(), name='studygroups_add_learners'),
    url(r'^studygroup/(?P<study_group_id>[\d]+)/learner/(?P<pk>[0-9]+)/edit/$', ApplicationUpdate.as_view(), name='studygroups_application_edit'),
    url(r'^studygroup/(?P<study_group_id>[\d]+)/learner/(?P<pk>[0-9]+)/delete/$', ApplicationDelete.as_view(), name='studygroups_application_delete'),

    url(r'^studygroup/(?P<study_group_uuid>[\w-]+)/survey/$', StudyGroupLearnerSurvey.as_view(), name='studygroups_learner_survey'),
    url(r'^studygroup/(?P<study_group_uuid>[\w-]+)/survey/done/$', TemplateView.as_view(template_name='studygroups/learner_survey_done.html'), name='studygroups_learnear_survey_done'),
    url(r'^studygroup/(?P<study_group_uuid>[\w-]+)/facilitator_survey/$', StudyGroupFacilitatorSurvey.as_view(), name='studygroups_facilitator_survey'),
    url(r'^facilitator_survey/$', TemplateView.as_view(template_name='studygroups/anonymous_facilitator_survey.html'), name='anonymous_facilitator_survey'),
    url(r'^facilitator_survey/done/$', TemplateView.as_view(template_name='studygroups/facilitator_survey_done.html'), name='studygroups_facilitator_survey_done'),

    url(r'^studygroup/(?P<study_group_id>[\w-]+)/report/$', StudyGroupFinalReport.as_view(), name='studygroups_final_report'),

    # views regarding study group meetings
    url(r'^studygroup/(?P<study_group_id>[\d]+)/meeting/(?P<pk>[\d]+)/edit/$', MeetingUpdate.as_view(), name='studygroups_meeting_edit'),
    url(r'^studygroup/(?P<study_group_id>[\d]+)/meeting/create/$', MeetingCreate.as_view(), name='studygroups_meeting_create'),
    url(r'^studygroup/(?P<study_group_id>[\d]+)/meeting/(?P<pk>[0-9]+)/delete/$', MeetingDelete.as_view(), name='studygroups_meeting_delete'),


    url(r'^studygroup/(?P<study_group_id>[\d]+)/meeting/(?P<pk>[\d]+)/recap/$', MeetingRecap.as_view(), name='studygroups_meeting_recap'),
    url(r'^studygroup/(?P<study_group_id>[\d]+)/meeting/(?P<pk>[\d]+)/recap/dismiss/$', MeetingRecapDismiss.as_view(), name='studygroups_meeting_recap_dismiss'),

    url(r'^course/create/$', CourseCreate.as_view(), name='studygroups_course_create'),
    url(r'^course/(?P<pk>[\d]+)/$', CoursePage.as_view(), name='studygroups_course_page'),
    url(r'^course/(?P<pk>[\d]+)/reviews/$', CourseReviewsPage.as_view(), name='studygroups_course_reviews_page'),
    url(r'^course/(?P<pk>[\d]+)/edit/$', CourseUpdate.as_view(), name='studygroups_course_edit'),
    url(r'^course/(?P<pk>[\d]+)/delete/$', CourseDelete.as_view(), name='studygroups_course_delete'),

    url(r'^facilitator/$', RedirectView.as_view(url='/'), name='studygroups_facilitator_deprecated'),
    url(r'^facilitator/team-invitation/$', InvitationConfirm.as_view(), name='studygroups_facilitator_invitation_confirm'),
    url(r'^facilitator/team-invitation/(?P<invitation_id>[\d]+)/$', InvitationConfirm.as_view(), name='studygroups_facilitator_invitation_confirm'),
    url(r'^facilitator/team-invitation/(?P<token>[\w-]+)/$', InvitationConfirm.as_view(), name='studygroups_facilitator_invitation_confirm_token'),
    url(r'^facilitator/teammembership/(?P<pk>[\d]+)/delete/$', LeaveTeam.as_view(), name='studygroups_facilitator_leave_team'),


    url(r'^optout/$', OptOutView.as_view(), name='studygroups_optout'),
    url(r'^optout/confirm/$', views.optout_confirm, name='studygroups_leave'),

    url(r'^rsvp/$', views.rsvp, name='studygroups_rsvp'),
    url(r'^rsvp/success/$', TemplateView.as_view(template_name='studygroups/rsvp_success.html'), name='studygroups_rsvp_success'),

    url(r'^organize/$', views.organize, name='studygroups_organize'),
    url(r'^organize/(?P<team_id>[\d]+)/$', views.organize_team, name='studygroups_organize_team'),
    url(r'^organize/studygroups/$', StudyGroupList.as_view(), name='studygroups_organizer_studygroup_list'),
    url(r'^organize/teammembership/(?P<team_id>[\d]+)/(?P<user_id>[\d]+)/delete/$', TeamMembershipDelete.as_view(), name='studygroups_teammembership_delete'),
    url(r'^organize/team/(?P<team_id>[\d]+)/member/invite/$', TeamInvitationCreate.as_view(), name='studygroups_team_member_invite'),
    url(r'^organize/team/(?P<team_id>[\d]+)/edit/$', TeamUpdate.as_view(), name='studygroups_team_edit'),

    url(r'^get-organizer-guide/$', OrganizerGuideForm.as_view(), name='studygroups_organizer_guide_form'),

    # These two URLs are deprecated, but kept for historic purposes
    url(r'^report/weekly/$', RedirectView.as_view(pattern_name='studygroups_weekly_update') ),
    url(r'^report/weekly/(?P<year>[\d]+)-(?P<month>[\d]+)-(?P<day>[\d]+)/$', RedirectView.as_view(pattern_name='studygroups_weekly_update_date')),

    url(r'^weekly-update/$', views.weekly_update, name='studygroups_weekly_update'),
    url(r'^weekly-update/(?P<year>[\d]+)-(?P<month>[\d]+)-(?P<day>[\d]+)/$', views.weekly_update, name='studygroups_weekly_update_date'),
    url(r'^weekly-update/(?P<team_id>[\d]+)/$', views.weekly_update, name='studygroups_weekly_update_team'),
    url(r'^weekly-update/(?P<team_id>[\d]+)/(?P<year>[\d]+)-(?P<month>[\d]+)-(?P<day>[\d]+)/$', views.weekly_update, name='studygroups_weekly_update_team_date'),

    url(r'^receive_sms/$', views.receive_sms, name='studygroups_receive_sms'),

    url(r'^staff/dash/$', StaffDashView.as_view(), name='studygroups_staff_dash'),
    url(r'^digest/generate/$', DigestGenerateView.as_view(), name='studygroups_digest_generate'),
    url(r'^staff/dash/stats/$', StatsDashView.as_view(), name='studygroups_staff_dash_stats'),

    url(r'^export/signups/$', ExportSignupsView.as_view(), name='studygroups_export_signups'),
    url(r'^export/facilitators/$', ExportFacilitatorsView.as_view(), name='studygroups_export_facilitators'),
    url(r'^export/studygroups/$', ExportStudyGroupsView.as_view(), name='studygroups_export_studygroups'),
    url(r'^export/courses/$', ExportCoursesView.as_view(), name='studygroups_export_courses'),

    url(r'^community_digest/(?P<start_date>[\w-]+)/(?P<end_date>[\w-]+)/$', CommunityDigestView.as_view(), name='studygroups_community_digest'),
]

