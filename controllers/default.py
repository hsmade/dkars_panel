# -*- coding: utf-8 -*-
# this file is released under public domain and you can use without limitations

from datetime import datetime

#########################################################################
## This is a sample controller
## - index is the default action of any application
## - user is required for authentication and authorization
## - download is for downloading files uploaded in the db (does streaming)
#########################################################################

def index():
    """
    example action using the internationalization operator T and flash
    rendered by views/default/index.html or views/generic.html

    if you need a simple wiki simply replace the two lines below with:
    return auth.wiki()
    """
    response.flash = T("Hello World")
    return dict(message=T('Welcome to web2py!'))


def user():
    """
    exposes:
    http://..../[app]/default/user/login
    http://..../[app]/default/user/logout
    http://..../[app]/default/user/register
    http://..../[app]/default/user/profile
    http://..../[app]/default/user/retrieve_password
    http://..../[app]/default/user/change_password
    http://..../[app]/default/user/manage_users (requires membership in
    use @auth.requires_login()
        @auth.requires_membership('group name')
        @auth.requires_permission('read','table name',record_id)
    to decorate functions that need access control
    """
    return dict(form=auth())


def mailinglist():
    """
    When not logged in, allows the user to add themselves to the mailing list.
    When logged in, allows for maintenance and download on the mailing list.
    """
    if auth.has_membership('admin'):
        title = 'Mailing list maintenance'
        form = SQLFORM.smartgrid(db.t_mailinglist)
    else:
        title = 'Subscribe to our panel mailing list'
        form = FORM('Your e-mail address:', INPUT(_name='email', requires=IS_EMAIL()), INPUT(_type='submit'))
        if form.accepts(request, session):
            db.t_mailinglist.insert(f_email=form.vars['email'])
            response.flash = 'form accepted'
    return dict(form=form, title=title)


@auth.requires_membership('admin')
def administrate():
    """
    Administrate the questionnaires
    """
    if auth.has_membership('admin'):
        return dict(form=SQLFORM.smartgrid(db.t_questionnaire))
    else:
        raise HTTP(404)


@auth.requires_login()
def questionnaires():
    """
    Fill a questionnaire
    # FIXME: what should this do when the user already filled this one in?
    """
    if len(request.args) < 1:
        raise HTTP(404)
    # get the questionnaire
    questionnaire = db(db.t_questionnaire.id == request.args[0]).select()
    if not questionnaire:
        raise HTTP(404)
    questionnaire = questionnaire[0]
    # if int(questionnaire.f_start.replace('-', '')) < int(datetime.now().strftime('%Y%m%d')) > int(questionnaire.f_end.replace('-', '')):
    #     raise HTTP(404, T('This questionnaire has ended'))
    if len(request.args) == 1:
        question_index = 0
    else:
        question_index = int(request.args[1])
    questions = db(db.t_question.f_questionnaire == questionnaire).select()
    try:
        question = questions[question_index]
    except IndexError:
        return dict(
            title=questionnaire.f_title,
            description=T('Thanks for submitting your answers'),
            question=None,
            answer=None,
        )
    given_answer = db((db.t_member_answer.f_member == auth.user_id) &
                      (db.t_member_answer.f_question == question)).select()
    if given_answer:
        given_answer_record = given_answer[0]
        try:
            given_answers = [row.f_answer for row in db(db.t_answer.id.belongs(given_answer_record.f_answer)).select()]
        except KeyError:
            given_answers = []
        if len(given_answers) == 1:
            given_answers = given_answers[0]
    else:
        given_answers = []
        given_answer_record = None

    answer_form = SQLFORM.factory(
        Field('Answer', 'list:string',
              requires=IS_EMPTY_OR(
                  IS_IN_SET(
                      [row.f_answer for row in db(db.t_answer.f_question == question.id).select()], multiple=question.f_multiple
                  )
              ),
              default=given_answers)
    )

    if answer_form.accepts(request, session):
        answer = answer_form.vars['Answer']
        if not isinstance(answer, list):
            answer = [answer,]
        answers = db(db.t_answer.f_answer.belongs(answer)).select()
        if not given_answer_record:
            db.t_member_answer.insert(
                f_question=question,
                f_answer=[row.id for row in answers],
                f_member=auth.user_id
            )
        else:
            given_answer_record.update_record(f_answer=[row.id for row in answers])
        redirect(URL('questionnaires', args=(request.args[0], question_index + 1)))
    return dict(title=questionnaire.f_title,
                description=questionnaire.f_description,
                question=question.f_question,
                answer=answer_form,
                )


@auth.requires_membership('admin')
def results():
    """
    Returns the results for a questionnaire
    """
    if len(request.args) < 1:
        raise HTTP(404)
    # get the questionnaire
    questionnaire = db(db.t_questionnaire.id == request.args[0]).select()
    if not questionnaire:
        raise HTTP(404)
    questionnaire = questionnaire[0]
    title = 'Results of questionnaire number {} ({} - {})'.format(
        questionnaire.id,
        questionnaire.f_start,
        questionnaire.f_end,
    )

    # get the question
    if len(request.args) == 1:
        question_index = 0
    else:
        question_index = int(request.args[1])
    questions = db(db.t_question.f_questionnaire == questionnaire).select()
    try:
        question = questions[question_index]
    except IndexError:
        question = questions[0]

    # get the answers for that question
    if len(request.args) == 3:
        answer_index = int(request.args[2])
    else:
        answer_index = 0

    answers = db(db.t_answer.f_question == question).select()
    try:
        answer = answers[answer_index]
    except IndexError:
        answer = answers[0]
    answer_text = answer.f_answer
    # get the members on this answer
    member_ids = [row.f_member for row in db(db.t_member_answer.f_question == question).select() if answer.id in row.f_answer]

    dg_question_list = []
    if 'detail' in request.vars:
        # get demographics
        dg_questions = db(db.t_question.f_questionnaire == 1).select()
        for dg_question in dg_questions:
            dg_answers = db(db.t_answer.f_question == dg_question).select()
            dg_answers_list = []
            for dg_answer in dg_answers:
                amount = len([row.f_member for row in db(db.t_member_answer.f_question == dg_question).select() if dg_answer.id in row.f_answer])
                dg_answers_list.append({
                    'answer': dg_answer.f_answer,
                    'amount': amount
                })
            dg_question_list.append({
                'question': dg_question.f_question,
                'answers': dg_answers_list
            })
    return dict(title=title, question=question.f_question, answer=answer_text,
                amount=len(member_ids), demographics=dg_question_list)
