#This file is part internetdomain_invoice module for Tryton.
#The COPYRIGHT file at the top level of this repository contains 
#the full copyright notices and license terms.

from trytond.pool import Pool
from .internetdomain import *
from .invoice import *


def register():
    Pool.register(
        Renewal,
        CreateInvoice,
        InvoiceLine,
        module='internetdomain_invoice', type_='model')
    Pool.register(
        Invoice,
        module='internetdomain_invoice', type_='wizard')
