# -*- coding: utf-8 -*-
# this file is released under public domain and you can use without limitations

from datetime import datetime
import logging

logger = logging.getLogger('panel.controller')

#########################################################################
## This is a sample controller
## - index is the default action of any application
## - user is required for authentication and authorization
## - download is for downloading files uploaded in the db (does streaming)
#########################################################################

# TODO apply website template

def index():
    """
    This is the landing page.
    When the user is not logged in, present sign-in and sign-up links.
    When the user is logged in, give the user a list of open questionnaires.
    When the user is an admin, present the administrate and results links
    """
    links = []
    list_questionnaires = []
    
    if not auth.is_logged_in():
        links.extend([
            {
                'name': 'Registratie e-mail adres zodat wij u kunnen waarschuwen wanneer er een nieuwe vraag voor het panel is (éénmalig)',
                'link': URL('mailinglist')
            },
            {
                'name': 'Afmelden emailadres (u krijgt dan geen ‘panel meldingen’ meer van ons).',
                'link': URL('mailinglist_remove')
            },
            {
                'name': T('Inloggen'),
                'link': URL('user/login')
            },
            {
                'name': T('Aanmelden als nieuwe gebruiker'),
                'link': URL('user/register')
            }
        ])
    else:
        query = (db.t_questionnaire.f_start <= datetime.now()) & (db.t_questionnaire.f_end >= datetime.now())
        for questionnaire in db(query).select():
            logger.debug('selected: {id} {start} {end}'.format(id=questionnaire.id, start=questionnaire.f_start, end=questionnaire.f_end))
            list_questionnaires.append({
                'name': questionnaire.f_title,
                'link': URL('questionnaires', args=(questionnaire.id))
            })
    if auth.has_membership('admin'):
        links.extend([
            {
                'name': T('Administratie'),
                'link': URL('administrate')
            },
            {
                'name': T('Resultaten'),
                'link': URL('results')
            }
        ])

    return dict(links=links, list_questionnaires=list_questionnaires)


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
        title = 'Mailinglijst administratie'
        form = SQLFORM.smartgrid(db.t_mailinglist)
    else:
        title = 'Aanmelden voor de mailinglijst voor nieuwe onderzoeken'
        form = FORM('e-mailaddress:', INPUT(_name='email', requires=IS_EMAIL()), INPUT(_type='submit'))
        if form.accepts(request, session):
            db.t_mailinglist.insert(f_email=form.vars['email'])
            response.flash = T('Je bent toegevoegd')
    return dict(form=form, title=title)


def mailinglist_remove():
    """
    Allows to remove an address from the list
    """
    title = 'Afmelden voor de mailinglijst'
    form = FORM('e-mailaddress:', INPUT(_name='email', requires=IS_EMAIL()), INPUT(_type='submit'))
    if form.accepts(request, session):
        result = db(db.t_mailinglist.f_email == form.vars['email']).delete()
        if result:
            response.flash = 'e-Mail address vewijderd'
    return dict(form=form, title=title) 

@auth.requires_membership('admin')
def administrate():
    """
    Administrate the questionnaires
    """
    logger.debug('admin: \n{}\n{}'.format(request.args, response.vars))
    form = SQLFORM.smartgrid(db.t_questionnaire)
    #logger.debug('admin: form: {}'.format(form))
    return dict(form=form)


@auth.requires_login()
def questionnaires():
    """
    Fill a questionnaire
    """
    logger.debug('questionnaire.args: {}'.format(request.args))
    if len(request.args) < 1:
        raise HTTP(404)
    # get the questionnaire
    questionnaire = db(db.t_questionnaire.id == request.args[0]).select()
    if not questionnaire:
        raise HTTP(404)
    questionnaire = questionnaire[0]
    if questionnaire.f_start < datetime.now().date() > questionnaire.f_end:
        raise HTTP(404, 'Dit onderzoek is be&iuml;ndigd')
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
            description='Bedankt voor het meedoen aan dit onderzoek',
            question='',
            answer='',
        )
    given_answer = db((db.t_member_answer.f_member == auth.user_id) &
                      (db.t_member_answer.f_question == question)).select()
    logger.debug('questionnaire: user_id: {}, question ID:{}'.format(auth.user_id, question.id))
    if given_answer:
        given_answer_record = given_answer[0]
        logger.debug('questionnaire: given_answer: {}'.format(given_answer_record))
        try:
            given_answers = [row.f_answer for row in db(db.t_answer.id.belongs(given_answer_record.f_answer)).select()]
        except KeyError:
            logger.debug('questionnaire: got key error while getting given answers')
            given_answers = []
        if len(given_answers) == 1:
            given_answers = given_answers[0]
    else:
        logger.debug('questionnaire: no given answer found')
        given_answers = []
        given_answer_record = None
    logger.debug('questionnaire: given_answers: {}'.format(given_answers))

    #FIXME map to ID, as value is broken
    answer_form = SQLFORM.factory(
        Field('Antwoord', 'list:string',
              requires=IS_EMPTY_OR(
                  IS_IN_SET(
                      [row.f_answer for row in db(db.t_answer.f_question == question.id).select()], multiple=question.f_multiple
                  )
              ),
              default=given_answers)
    )

    logger.debug('questionnaire.form.answer: {}'.format(answer_form.vars.keys()))
    if answer_form.accepts(request, session):
        answer = answer_form.vars['Antwoord']
        if not isinstance(answer, list):
            answer = [answer,]
        logger.debug('questionnaire.submit got answer: {}'.format(answer))
        answers = db(db.t_answer.f_answer.belongs(answer)).select()
        if not given_answer_record:
            logger.debug('questionnaire.submit: insert record with answer:{}'.format([row.id for row in answers]))
            db.t_member_answer.insert(
                f_question=question,
                f_answer=[row.id for row in answers],
                f_member=auth.user_id
            )
        else:
            logger.debug('questionnaire.submit: update record with answer:{}'.format([row.id for row in answers]))
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
        field = db.t_questionnaire.id.min()
        first = db(db.t_questionnaire).select(field)
        redirect(URL('results', args=(first[0][field],)))
    # get the questionnaire
    questionnaire = db(db.t_questionnaire.id == request.args[0]).select()
    if not questionnaire:
        raise HTTP(404)
    questionnaire = questionnaire[0]
    title = '{} ({} - {})'.format(
        questionnaire.f_title,
        questionnaire.f_start,
        questionnaire.f_end,
    )

    questionnaires = [row.id for row in db(db.t_questionnaire).select()]
    questionnaire_index = int(request.args[0])
    if questionnaire_index <= 1:
        questionnaire_left = 1
    else:
        questionnaire_left = questionnaire_index - 1
    if questionnaire_index >= questionnaires[-1]:
        questionnaire_right = questionnaires[-1]
    else:
        questionnaire_right = questionnaires[questionnaires.index(questionnaire_index) + 1]

    # get the question
    if len(request.args) == 1:
        redirect(URL('results', args=(request.args[0], 0)))
    else:
        question_index = int(request.args[1])

    questions = db(db.t_question.f_questionnaire == questionnaire).select()
    if question_index <= 0:
        question_left = 0
    else:
        question_left = question_index - 1

    if question_index >= len(questions) - 1:
        question_right = question_index
    else:
        question_right = question_index + 1
    try:
        question = questions[question_index]
    except IndexError:
        question = questions[0]

    answers_list = []
    answers = db(db.t_answer.f_question == question).select()

    for answer in answers:
        logger.debug('results: getting member ids for question:{} and answer:{}'.format(question.id, answer.id))
        member_ids = [row.f_member for row in db(db.t_member_answer.f_question == question).select() if answer.id in row.f_answer]
        logger.debug('results: getting member ids result: {}'.format(member_ids))

        # get demographics
        # TODO: make the questionnaire selectable instead of hard coded '1'
        dg_question_list = []
        dg_questions = db(db.t_question.f_questionnaire == 1).select()
        for dg_question in dg_questions:
            dg_answers = db(db.t_answer.f_question == dg_question).select()
            dg_answers_list = []
            for dg_answer in dg_answers:
                amount = len([row.f_member for row in db(db.t_member_answer.f_question == dg_question).select() if dg_answer.id in row.f_answer and row.f_member in member_ids])
                dg_answers_list.append({
                    'answer': dg_answer.f_answer,
                    'amount': amount
                })
            dg_question_list.append({
                'question': dg_question.f_question,
                'answers': dg_answers_list
            })

        answers_list.append(
            {
                'id': answer.id,
                'answer': answer.f_answer,
                'amount': len(member_ids),
                'demographics': dg_question_list,
            }
        )

    return dict(title=title, introduction=questionnaire.f_description,
                question=question.f_question, answers=answers_list,
                question_left=question_left, question_right=question_right,
                questionnaire_left=questionnaire_left, questionnaire_right=questionnaire_right,
                )
