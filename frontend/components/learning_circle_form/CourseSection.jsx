import React from 'react'
import { Search, BrowseCourses, CourseCard } from 'p2pu-search-cards';

import 'p2pu-search-cards/dist/build.css';


const CourseSection = (props) => {
  const removeCourseSelection = () => {
    props.updateFormData({ course: {} });
    const cleanUrl = window.location.origin + window.location.pathname;
    window.history.replaceState({}, document.title, cleanUrl)
  }

  const scrollToTop = () => document.querySelector('body').scrollTop = 0;

  const handleSelectResult = selected => {
    props.updateFormData({ course: selected })
    scrollToTop()
  }

  return (
    <div>
      {
        props.errors.course &&
        <div className="error-message minicaps">{props.errors.course}</div>
      }
      {
          props.learningCircle.course.id &&
          <div className="search-results">
            <p className="bold">Selected course:</p>
            <CourseCard
              course={props.learningCircle.course}
            />
            <a style={{cursor: 'pointer'}} onClick={removeCourseSelection}>Remove selection</a>
          </div>
        }
        {
          !props.learningCircle.course.id &&
          <Search
            searchSubject={'courses'}
            Browse={BrowseCourses}
            onSelectResult={handleSelectResult}
          />
        }
    </div>
  );
}


export default CourseSection