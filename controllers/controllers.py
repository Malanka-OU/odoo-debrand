import base64
import functools
import io
import json

from odoo.http import request
from odoo.modules import get_resource_path
from odoo.tools.mimetypes import guess_mimetype

import jinja2
import odoo
import os
import sys
from odoo import http
from odoo.addons.web.controllers import main
from odoo.addons.web.controllers.main import Binary
from odoo.addons.web.controllers.main import Database

if hasattr(sys, 'frozen'):
    # When running on compiled windows binary, we don't have access to
	# package loader.
    path = os.path.realpath(
        os.path.join(os.path.dirname(__file__), '..', 'views'))
    loader = jinja2.FileSystemLoader(path)
else:
    loader = jinja2.PackageLoader('odoo.addons.odoo-debrand', "views")
env = main.jinja2.Environment(loader=loader, autoescape=True)
env.filters["json"] = json.dumps
db_monodb = http.db_monodb
DBNAME_PATTERN = '^[a-zA-Z0-9][a-zA-Z0-9_.-]+$'


class BinaryCustom(Binary):
    @http.route([
        '/web/binary/company_logo',
        '/logo',
        '/logo.png',
    ], type='http', auth="none")
    def company_logo(self, dbname=None, **kw):
        imgname = 'logo'
        imgext = '.png'
        placeholder = functools.partial(get_resource_path, 'web', 'static',
                                        'src', 'img')
        uid = None
        if request.session.db:
            dbname = request.session.db
            uid = request.session.uid
        elif dbname is None:
            dbname = db_monodb()

        if not uid:
            uid = odoo.SUPERUSER_ID

        if not dbname:
            response = http.send_file(placeholder(imgname + imgext))
        else:
            try:
                # create an empty registry
                registry = odoo.modules.registry.Registry(dbname)
                with registry.cursor() as cr:
                    company = int(kw['company']) if kw and kw.get(
                        'company') else False
                    if company:
                        cr.execute("""SELECT logo_web, write_date
	                                    FROM res_company
	                                   WHERE id = %s
	                               """, (company,))
                    else:
                        cr.execute("""SELECT c.logo_web, c.write_date
	                                    FROM res_users u
	                               LEFT JOIN res_company c
	                                      ON c.id = u.company_id
	                                   WHERE u.id = %s
	                               """, (uid,))
                    row = cr.fetchone()
                    if row and row[0]:
                        image_base64 = base64.b64decode(row[0])
                        image_data = io.BytesIO(image_base64)
                        mimetype = guess_mimetype(image_base64,
                                                  default='image/png')
                        imgext = '.' + mimetype.split('/')[1]
                        if imgext == '.svg+xml':
                            imgext = '.svg'

                        response = http.send_file(image_data,
                                                  filename=imgname + imgext,
                                                  mimetype=mimetype,
                                                  mtime=row[1])
                    else:
                        response = http.send_file(placeholder('nologo.png'))
            except Exception:
                response = http.send_file(placeholder(imgname + imgext))

        return response
