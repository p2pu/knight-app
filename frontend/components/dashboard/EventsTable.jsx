import React from "react";
import {datetime} from "../../helpers/i18n";

const path = '/api/community_calendar/events/?user=self';

const EventRow = ({event, classes, index}) => (
  <tr key={index} className={`${classes}`}>
    <td>{event.title}</td>
    <td>{event.description}</td>
    <td>{datetime(event.datetime)}</td>
    <td>
      <a href={event.edit_url} className="p2pu-btn btn-sm dark">edit</a>
    </td>
    <td>
      <a href={event.delete_url} className="p2pu-btn btn-sm dark">delete</a>
    </td>
  </tr>
);

export default class EventsTable extends React.Component {
  constructor(props){
    super(props);
    this.state = {
      events: [],
    };
  }

  componentDidMount() {
    let apiUrl = 'http://localhost:8000/api/community_calendar/events/?format=json&user=self'
    fetch(apiUrl).then( resp => resp.json()).then( data => {
      this.setState({events: data.results});
    });
  }

  render() {
    return (
      <div className="community-events-table">
        <div className="table-responsive d-none d-md-block" data-aos='fade'>
          <table className="table">
            <thead>
              <tr>
                <td>Title</td>
                <td>Description</td>
                <td>Date</td>
                <td></td>
                <td></td>
              </tr>
            </thead>
            <tbody>
              {this.state.events.map( event => <EventRow event={event} />)}
            </tbody>
          </table>
        </div>
      </div>
    );
  }
};
