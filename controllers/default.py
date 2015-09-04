# -*- coding: utf-8 -*-
# this file is released under public domain and you can use without limitations

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
    given_answer = db((db.t_answer.f_member == auth.user_id) &
                      (db.t_answer.f_question == question)).select()
    if given_answer:
        given_answer_record = given_answer[0]
        given_answer = given_answer_record.f_answer
    else:
        given_answer = ''
        given_answer_record = None
    # if question.f_open:
    #     answer = SQLFORM.factory(
    #         Field('Answer', 'text', default=given_answer)
    #     )
    # else:
    answer = SQLFORM.factory(
        Field('Answer', 'list:string',
              requires=IS_EMPTY_OR(IS_IN_SET(question.f_answers, multiple=question.f_multiple)),
              default=given_answer)
    )

    if answer.accepts(request, session):
        if not given_answer_record:
            db.t_answer.insert(
                f_question=question,
                f_answer=answer.vars['Answer'],
                f_member=auth.user_id
            )
        else:
            given_answer_record.update_record(f_answer=answer.vars['Answer'])
        redirect(URL('questionnaires', args=(request.args[0],question_index + 1)))
    return dict(title=questionnaire.f_title,
                description=questionnaire.f_description,
                question=question.f_question,
                answer=answer,
                )
