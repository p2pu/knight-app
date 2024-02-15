import React from 'react'
import ReactDOM from 'react-dom'
import FacilitatorDashboard from './components/dashboard/FacilitatorDashboard'
import ErrorBoundary from './components/error-boundary'

const element = document.getElementById('facilitator-dashboard')

const user = element.dataset.user === "AnonymousUser" ? null : element.dataset.user;
const userProfile = element.dataset.userProfile === "None" ? null : element.dataset.userProfile;
const teamId = element.dataset.teamId === "None" ? null : element.dataset.teamId;
const teamName = element.dataset.teamName === "None" ? null : element.dataset.teamName;
const teamOrganizerName = element.dataset.teamOrganizerName === "None" ? null : element.dataset.teamOrganizerName;
const teamInvitationConfirmationUrl = element.dataset.teamInvitationConfirmationUrl === "None" ? null : element.dataset.teamInvitationConfirmationUrl;
const emailConfirmationUrl = element.dataset.emailConfirmationUrl === "None" ? null : element.dataset.emailConfirmationUrl;
const userIsOrganizer = element.dataset.userIsOrganizer === "None" ? null : element.dataset.userIsOrganizer;
const teamInvitationLink = element.dataset.teamInvitationLink === "None" ? null : element.dataset.teamInvitationLink;
const createTeamInvitationLink = element.dataset.createTeamInvitationLink === "None" ? null : element.dataset.createTeamInvitationLink;
const deleteTeamInvitationLink = element.dataset.deleteTeamInvitationLink === "None" ? null : element.dataset.deleteTeamInvitationLink;
const teamMemberInvitationUrl = element.dataset.teamMemberInvitationUrl === "None" ? null : element.dataset.teamMemberInvitationUrl;
const editTeamUrl = element.dataset.editTeamUrl === "None" ? null : element.dataset.editTeamUrl;
const editTeamCourseListUrl = element.dataset.editTeamCourseListUrl === "None" ? null : element.dataset.editTeamCourseListUrl;


ReactDOM.render(
  <ErrorBoundary scope="facilitator-dashboard">
    <FacilitatorDashboard
      userData={element.dataset}
      user={user}
      teamId={teamId}
      teamName={teamName}
      teamOrganizerName={teamOrganizerName}
      teamInvitationConfirmationUrl={teamInvitationConfirmationUrl}
      emailConfirmationUrl={emailConfirmationUrl}
      userIsOrganizer={userIsOrganizer}
      teamInvitationLink={teamInvitationLink}
      createTeamInvitationLink={createTeamInvitationLink}
      deleteTeamInvitationLink={deleteTeamInvitationLink}
      teamMemberInvitationUrl={teamMemberInvitationUrl}
      deleteTeamMembershipApiUrl={element.dataset.deleteTeamMembershipApiUrl}
      deleteTeamInvitationApiUrl={element.dataset.deleteTeamInvitationApiUrl}
      editTeamUrl={editTeamUrl}
      editTeamCourseListUrl={editTeamCourseListUrl}
      isMemberTeam={element.dataset.isMemberTeam}
      isStaff={element.dataset.isStaff}
      memberSupportUrl={element.dataset.memberSupportUrl}
    />
  </ErrorBoundary>,
  element
)
