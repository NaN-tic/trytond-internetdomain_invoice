#This file is part account_invoice_cancel module for Tryton.
#The COPYRIGHT file at the top level of this repository contains 
#the full copyright notices and license terms.
{
    'name': 'Internet Domain Invoice',
    'name_ca_ES': 'Facturació dominis internet',
    'name_es_ES': 'Facturación dominios internet',
    'version': '2.4.0',
    'author': 'Zikzakmedia',
    'email': 'zikzak@zikzakmedia.com',
    'website': 'http://www.zikzakmedia.com/',
    'description': '''Internet Domain Invoice''',
    'description_ca_ES': '''Facturació de dominis internet''',
    'description_es_ES': '''Facturación de dominios de internet''',
    'depends': [
        'ir',
        'res',
        'internetdomain',
        'account_invoice',
        'analytic_account',
    ],
    'xml': [
        'internetdomain.xml',
    ],
    'translation': [
        'locale/ca_ES.po',
        'locale/es_ES.po',
    ]
}
