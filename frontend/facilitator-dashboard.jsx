import React from 'react'
import ReactDOM from 'react-dom'
import FacilitatorDashboard from './components/dashboard/FacilitatorDashboard'


const element = document.getElementById('facilitator-dashboard')

const user = element.dataset.user === "AnonymousUser" ? null : element.dataset.user;
const teamName = element.dataset.teamName === "None" ? null : element.dataset.teamName;
const teamOrganizerName = element.dataset.teamOrganizerName === "None" ? null : element.dataset.teamOrganizerName;
const teamInvitationConfirmationUrl = element.dataset.teamInvitationConfirmationUrl === "None" ? null : element.dataset.teamInvitationConfirmationUrl;
const emailConfirmationUrl = element.dataset.emailConfirmationUrl === "None" ? null : element.dataset.emailConfirmationUrl;
const userIsOrganizer = element.dataset.userIsOrganizer === "None" ? null : element.dataset.userIsOrganizer;
const teamInvitationUrl = element.dataset.teamInvitationUrl === "None" ? null : element.dataset.teamInvitationUrl;
const createTeamInvitationUrl = element.dataset.createTeamInvitationUrl === "None" ? null : element.dataset.createTeamInvitationUrl;
const deleteTeamInvitationUrl = element.dataset.deleteTeamInvitationUrl === "None" ? null : element.dataset.deleteTeamInvitationUrl;
const teamMemberInvitationUrl = element.dataset.teamMemberInvitationUrl === "None" ? null : element.dataset.teamMemberInvitationUrl;

ReactDOM.render(
  <FacilitatorDashboard
    user={user}
    teamName={teamName}
    teamOrganizerName={teamOrganizerName}
    teamInvitationConfirmationUrl={teamInvitationConfirmationUrl}
    emailConfirmationUrl={emailConfirmationUrl}
    userIsOrganizer={userIsOrganizer}
    teamInvitationUrl={teamInvitationUrl}
    createTeamInvitationUrl={createTeamInvitationUrl}
    deleteTeamInvitationUrl={deleteTeamInvitationUrl}
    teamMemberInvitationUrl={teamMemberInvitationUrl}
  />, element)