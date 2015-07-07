# -*- coding: utf-8 -*-

#########################################################################
## This scaffolding model makes your app work on Google App Engine too
## File is released under public domain and you can use without limitations
#########################################################################

## if SSL/HTTPS is properly configured and you want all HTTP requests to
## be redirected to HTTPS, uncomment the line below:
# request.requires_https()

## app configuration made easy. Look inside private/appconfig.ini
from gluon.contrib.appconfig import AppConfig
## once in production, remove reload=True to gain full speed
myconf = AppConfig(reload=True)


if not request.env.web2py_runtime_gae:
    ## if NOT running on Google App Engine use SQLite or other DB
    db = DAL(myconf.take('db.uri'), pool_size=myconf.take('db.pool_size', cast=int), check_reserved=['all'])
else:
    ## connect to Google BigTable (optional 'google:datastore://namespace')
    db = DAL('google:datastore+ndb')
    ## store sessions and tickets there
    session.connect(request, response, db=db)
    ## or store session in Memcache, Redis, etc.
    ## from gluon.contrib.memdb import MEMDB
    ## from google.appengine.api.memcache import Client
    ## session.connect(request, response, db = MEMDB(Client()))

## by default give a view/generic.extension to all actions from localhost
## none otherwise. a pattern can be 'controller/function.extension'
response.generic_patterns = ['*'] if request.is_local else []
## choose a style for forms
response.formstyle = myconf.take('forms.formstyle')  # or 'bootstrap3_stacked' or 'bootstrap2' or other
response.form_label_separator = myconf.take('forms.separator')


## (optional) optimize handling of static files
# response.optimize_css = 'concat,minify,inline'
# response.optimize_js = 'concat,minify,inline'
## (optional) static assets folder versioning
# response.static_version = '0.0.0'
#########################################################################
## Here is sample code if you need for
## - email capabilities
## - authentication (registration, login, logout, ... )
## - authorization (role based authorization)
## - services (xml, csv, json, xmlrpc, jsonrpc, amf, rss)
## - old style crud actions
## (more options discussed in gluon/tools.py)
#########################################################################

from gluon.tools import Auth, Service, PluginManager

auth = Auth(db)
service = Service()
plugins = PluginManager()

## create all tables needed by auth if not custom tables
auth.define_tables(username=False, signature=False)

## configure email
mail = auth.settings.mailer
mail.settings.server = 'logging' if request.is_local else myconf.take('smtp.server')
mail.settings.sender = myconf.take('smtp.sender')
mail.settings.login = myconf.take('smtp.login')

## configure auth policy
auth.settings.registration_requires_verification = False
auth.settings.registration_requires_approval = False
auth.settings.reset_password_requires_verification = True

#########################################################################
## Define your tables below (or better in another model file) for example
##
## >>> db.define_table('mytable',Field('myfield','string'))
##
## Fields can be 'string','text','password','integer','double','boolean'
##       'date','time','datetime','blob','upload', 'reference TABLENAME'
## There is an implicit 'id integer autoincrement' field
## Consult manual for more options, validators, etc.
##
## More API examples for controllers:
##
## >>> db.mytable.insert(myfield='value')
## >>> rows=db(db.mytable.myfield=='value').select(db.mytable.ALL)
## >>> for row in rows: print row.id, row.myfield
#########################################################################

## after defining tables, uncomment below to enable auditing
# auth.enable_record_versioning(db)

db.define_table('t_mailinglist',
    Field('f_email', 'string', label=T('e-Mail address'), requires=IS_EMAIL()),
)

db.define_table('t_locations',
    Field('f_location', 'string', label=T('Location')),
    Field('f_in_NL', 'boolean', label=T('Is in NL')),
)

db.define_table('t_home_types',
    Field('f_home_type', 'string', label=T('Home type'))
)

db.define_table('t_preference', 'string', label=T('Preference'))
db.define_table('t_members',
    Field('f_location', 'string', label=T('Location (province, EU or not EU'), 
          requires=IS_IN_DB(db, db.t_locations.id, '%(f_location)s', zero=None)),
    Field('f_dkars_member', 'boolean', label=T('DKARS member')),
    Field('f_sex', 'string', label=T('Sex'), requires=IS_IN_SET(('male','female'))),
    Field('f_age_group', 'string', label=T('Age group'), requires=IS_IN_SET((
        '< 16',
        '16-25',
        '26-50',
        '51-65',
        '> 65'
    ))),
    Field('f_type_of_home', 'string', label=T('Type of home'),
          requires=IS_IN_DB(db, db.t_home_types.id, '%(f_home_type)s', zero=None)),
    Field('f_registration_type', 'string', label=T('Registration type'), requires=IS_IN_SET((
        'F',
        'N',
        'None',
    ))),
    Field('f_hours_active', 'string', label=T('Hours active'), requires=IS_IN_SET((
        '0',
        '< 1',
        '1-8',
        '> 8'
    ))),
    # vereniging
    Field('f_club_member', 'string', label=T('Member of club'), requires=IS_IN_set((
        'Yes, of one dutch club',
        'Yes, of two or more dutch clubs',
        'Yes, of a dutch club and DKARS donator',
        'No, but DKARS donator',
        'No, none',
    ))),
)

db.define_table('f_member_preferences',
    Field('f_member_id', 'integer'),
    Field('f_preference_id', 'integer'),
)
