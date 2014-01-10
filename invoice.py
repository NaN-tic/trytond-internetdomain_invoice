#This file is part account_invoice_cancel module for Tryton.
#The COPYRIGHT file at the top level of this repository contains
#the full copyright notices and license terms.
from trytond.pool import Pool, PoolMeta

__all__ = ['InvoiceLine']
__metaclass__ = PoolMeta


class InvoiceLine:
    __name__ = 'account.invoice.line'

    @property
    def origin_name(self):
        pool = Pool()
        Renewal = pool.get('internetdomain.renewal')
        name = super(InvoiceLine, self).origin_name
        if isinstance(self.origin, Renewal):
            name = self.origin.renewal.rec_name
        return name

    @classmethod
    def _get_origin(cls):
        models = super(InvoiceLine, cls)._get_origin()
        models.append('internetdomain.renewal')
        return models
