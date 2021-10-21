import React from 'react';

const DashboardTitle = ({ user, userData }) => {
  if (user) {
    return (
      <header className="text-center my-5">
        <h1 style={{ lineHeight: 1, marginBottom: '1rem' }}>{`Hello ${userData.firstName} 👋`}</h1>
        <p style={{ lineHeight: 1, marginBottom: '1rem' }}>Welcome to your learning circle dashboard.</p>
        <p style={{ lineHeight: 1, marginBottom: '1rem' }}>Questions? See the <a href="https://docs.p2pu.org/" target="_blank" rel="noopener noreferrer">Knowledge Base</a> or email us at <a href="mailto:thepeople@p2pu.org">thepeople@p2pu.org</a>.</p>
      </header>
    )
  } else {
    return (
      <header className="text-center my-5">
        <h1>Learning Circle Dashboard</h1>
      </header>
    )
  }
}


export default DashboardTitle
