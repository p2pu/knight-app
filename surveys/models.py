# coding=utf-8
from django.db import models
from django.conf import settings
from studygroups.models import StudyGroup
from studygroups.models import Application

import json

MAX_STAR_RATING = 5

class TypeformSurveyResponse(models.Model):
    typeform_key = models.CharField(max_length=64, unique=True) #Called token in the JSON response
    form_id = models.CharField(max_length=12)
    survey = models.TextField()
    response = models.TextField() #This will be a JSON value
    responded_at = models.DateTimeField()

    class Meta:
        abstract = True

    def get_response_field(self, question_id):
        response = json.loads(self.response)
        answers = response.get('answers') or []
        return next((answer for answer in answers if answer["field"]["id"] == question_id), None)

    def get_value_by_ref(self, ref):
        response = json.loads(self.response)
        answers = response.get('answers') or []
        answer = next((answer for answer in answers if answer["field"]["ref"] == ref), None)
        if not answer:
            return None
        type_ = answer.get('type')
        value = answer.get(type_)
        if type_ == 'choice':
            value = value.get('label')
        return value

    def get_survey_field(self, field_id):
        survey = json.loads(self.survey)
        survey_fields = survey['fields']
        return next((field for field in survey_fields if field["id"] == field_id), None)


class FacilitatorSurveyResponse(TypeformSurveyResponse):
    study_group = models.ForeignKey(StudyGroup, blank=True, null=True, on_delete=models.SET_NULL)


class LearnerSurveyResponse(TypeformSurveyResponse):
    study_group = models.ForeignKey(StudyGroup, blank=True, null=True, on_delete=models.SET_NULL)
    learner = models.ForeignKey(Application, blank=True, null=True, on_delete=models.SET_NULL)


def find_field(field_id, typeform_survey):
    """ look up field_id in survey """
    survey = typeform_survey
    fields = [ field for field in survey.get('fields') if field.get('id') == field_id ]
    field = None
    if len(fields) == 1:
        return fields[0]

    # check if field is part of a group?
    group_fields = [
        field.get('properties', {}).get('fields') for field in survey.get('fields') if field.get('type') == 'group'
    ]
    # group_fields = [ [field, field, field], [field, field]]
    # flatten list
    group_fields =  [item for sublist in group_fields for item in sublist]
    fields = [ field for field in group_fields if field.get('id') == field_id ]
    if len(fields) == 1:
        return fields[0]
    return None


def normalize_data(typeform_response):
    """
    Turn disjoint reponse and survey data from TypeForm into an dict with
    field id as key and an object with field title and answer as value
    """
    survey = json.loads(typeform_response.survey)
    response = json.loads(typeform_response.response)
    answers = {}
    response_set = response.get('answers') or []
    for answer in response_set:
        field_id = answer.get('field').get('id')
        value_key = answer.get('type')
        value = json.dumps(answer.get(value_key))

        field = find_field(field_id, survey)
        field_title = field.get('title') if field else '??'

        answers[field_id] = {
            'field_title': field_title,
            'answer': value,
        }

    if typeform_response.study_group:
        answers['study_group_id'] = {
            'field_title': 'Learning circle ID',
            'answer': typeform_response.study_group.id,
        }
        answers['study_group_name'] = {
            'field_title': 'Learning circle name',
            'answer': typeform_response.study_group.name
        }
        answers['course'] = {
            'field_title': 'Course',
            'answer': typeform_response.study_group.course.title,
        }
        answers['facilitator'] = {
            'field_title': 'Facilitator',
            'answer': typeform_response.study_group.created_by.email,
        }
        if typeform_response.study_group.team:
            answers['team'] = {
                'field_title': 'Team',
                'answer': typeform_response.study_group.team.name
            }

    return answers


def get_all_results(query_set):
    """ de-normalize all results into a single table structure """
    fields = {} # dict of all fields
    for response in query_set:
        data = normalize_data(response)
        # update headings
        for field_id, value in data.items():
            fields[field_id] = value.get('field_title')

    field_ids = fields.keys()
    heading = [fields[field_id] for field_id in field_ids]
    data = []
    for db in query_set:
        response = normalize_data(db)
        data += [
            [response.get(field_id, {}).get('answer', '') for field_id in field_ids]
        ]
    return {
        'heading': heading,
        'data': data
    }


def _old_learner_survey_summary(response):
    data = {
        "learned_extra": None,
        "confidence": None,
        "recommendation_rating": None,
        "recommendation_rating_reason": None,
        "course_rating_reason": None,
    }

    # goal = signup goal OR survey goal OR None
    if response.learner and response.learner.get_goal():
        data['goal'] = response.learner.get_goal()
    elif response.get_value_by_ref('1929769b-dc20-4cd6-a849-c07ddd780456'):
        data['goal'] = response.get_value_by_ref('1929769b-dc20-4cd6-a849-c07ddd780456')

    # goal_rating = application.goal_met or survey goal met x2
    if response.learner and response.learner.goal_met:
        data['goal_rating'] = response.learner.goal_met
    else:
        goal_rating = response.get_value_by_ref('06677105-57d8-4b18-99d7-02f77165cca8')
        if not goal_rating:
            goal_rating = response.get_value_by_ref('47b94cfa-13fe-430d-b1d0-2414beedd865')
        if goal_rating:
            data['goal_rating'] = goal_rating

    # next_steps = survey next steps
    data['next_steps'] = response.get_value_by_ref('3fa8908a-665d-4dfe-9d77-26a76294a253')

    # course rating = survey course rating
    data['course_rating'] = response.get_value_by_ref('d8915ce4-0116-4469-b240-80e11fb4e362')
    return data


def _new_learner_survey_summary(response):
    summary = {}
    if response.learner and response.learner.get_goal():
        summary['goal'] = response.learner.get_goal()
    else:
        summary['goal'] = response.get_value_by_ref('goal')

    if response.learner and response.learner.goal_met:
        summary['goal_rating'] = response.learner.goal_met
    else:
        summary['goal_rating'] = response.get_value_by_ref('goal_rating_alt')

    survey_fields = [
        "goal_extra",
        "subject_confidence",
        "next_steps",
        "course_rating",
        "course_rating_reason",
        "recommendation_rating",
        "recommendation_rating_reason",
    ]
    for field in survey_fields:
        summary[field] = response.get_value_by_ref(field)
    return summary


def learner_survey_summary(survey_response):
    """
    Take a survey response, and return the following summary:
    {
        "goal": "blah",
        "goal_rating": 1,
        "goal_extra": "nah",
        "subject_confidence": 1,
        "next_steps": "none",
        "course_rating": 4,
        "course_rating_reason": "blah",
        "recommendation_rating": 1,
        "recommendation_rating_reason": "blah",
    }
    """
    # decide based on form ID how to get the data
    if survey_response.form_id == settings.TYPEFORM_LEARNER_SURVEY_FORM:
        return _new_learner_survey_summary(survey_response)
    return _old_learner_survey_summary(survey_response)


def _new_facilitator_survey_summary(response):
    summary = {}
    study_group = response.study_group

    # goal - precedence: study_group.goal > response.goal_alt
    if study_group and study_group.facilitator_goal:
        summary['goal'] = study_group.facilitator_goal
    elif response.get_value_by_ref('goal_alt'):
        summary['goal'] = response.get_value_by_ref('goal_alt')

    # goal_rating - precedence: study_group.facilitator_goal_rating > response.goal_rating_alt > repsonse.goal_rating_alt_2
    if study_group and study_group.facilitator_goal_rating:
        summary['goal_rating']: study_group.facilitator_goal_rating
    elif response.get_value_by_ref('goal_rating_alt'):
        summary['goal_rating'] = response.get_value_by_ref('goal_rating_alt')
    else:
        summary['goal_rating'] = response.get_value_by_ref('goal_rating_alt_2')

    # grab remaining fields directly from the survey
    survey_fields = [
        "surprise",
        "stories",
        "course_rating",
        "course_rating_reason",
        "recommendation_rating",
        "recommendation_rating_reason",
    ]
    for field in survey_fields:
        summary[field] = response.get_value_by_ref(field)

    # study_group.course_rating  > response.course_rating
    if study_group and study_group.course_rating:
        summary['course_rating'] = study_group.course_rating

    # course_rating_reason
    if study_group and study_group.course_rating_reason:
        summary['course_rating_reason'] = study_group.course_rating_reason

    return summary


def _old_facilitator_survey_summary(response):
    summary = {}

    # TODO does it make sense to use facilitator goal and rating here?

    if response.study_group and response.study_group.course_rating:
        summary['course_rating'] = response.study_group.course_rating
        summary['course_rating_reason'] = response.study_group.course_rating_reason
    else:
        # course_rating
        # TODO rework this logic
        # 1. Get rating + max rating
        # 1. if max rating is different, scale answer
        # 1. if rating is > max rating and quesion is missing, discard

        # Zm9XlzKGKC66 = "How well did the online course {{hidden:course}} work as a learning circle?"
        rating_question = response.get_survey_field("Zm9XlzKGKC66")
        rating_answer = response.get_response_field("Zm9XlzKGKC66")
        if rating_answer and 'number' in rating_answer:
            facilitator_rating = rating_answer['number']
            if rating_question and 'properties' in rating_question:
                facilitator_steps = rating_question['properties']['steps']
                # Normalize the rating if it doesn't match MAX_STAR_RATING
                if facilitator_steps != MAX_STAR_RATING:
                    facilitator_rating = round(facilitator_rating/facilitator_steps * MAX_STAR_RATING)
                summary['course_rating'] = facilitator_rating
            elif facilitator_rating > MAX_STAR_RATING:
                # if we don't know how many steps the rating has and it exceeds MAX_STAR_RATING
                # ignore this rating
                pass
            else:
                summary['course_rating'] = facilitator_rating
    
    return summary


def facilitator_survey_summary(survey_response):
    """
    {
        "goal": "",
        "goal_rating": 1,
        "surprise": "",
        "stories": "",
        "course_rating": 2,
        "course_rating_reason": "",
        "recommendation_score": 4,
        "recommendation_reason": "",
    }
    """
    summary = {'response_date': survey_response.responded_at}
    if survey_response.form_id == settings.TYPEFORM_FACILITATOR_SURVEY_FORM:
        summary.update(_new_facilitator_survey_summary(survey_response))
    else:
        summary.update(_old_facilitator_survey_summary(survey_response))
    return summary
