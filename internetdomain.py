#This file is part account_invoice_cancel module for Tryton.
#The COPYRIGHT file at the top level of this repository contains 
#the full copyright notices and license terms.

from trytond.model import ModelView, ModelSQL, fields
from trytond.transaction import Transaction
from trytond.pool import Pool
from trytond.pyson import If, Eval, Bool
from trytond.wizard import Wizard, StateAction, StateView, StateTransition, \
    Button

from decimal import Decimal
import datetime

class Renewal(ModelSQL, ModelView):
    'Renewal'
    _name = 'internetdomain.renewal'
    _description = __doc__

    invoice = fields.Many2One('account.invoice', 'Invoice', readonly=True)

    def __init__(self):
        super(Renewal, self).__init__()
        self._error_messages.update({
            'missing_payment_term': 'Not available Payment Type!',
            'missing_account_receivable': 'Party not available Account Receivable!',
            'missing_account_revenue': 'Product not available Account Revenue!',
            })

    def _get_invoice_description(self, renewal):
        '''
        Return description renewal
        :param renewal: the BrowseRecord of the renewal
        :return: str
        '''
        description = renewal.domain.name+' ('+str(renewal.date_renewal)+' / '+str(renewal.date_expire)+')'
        return description

    def _get_invoice_renewal(self, renewal):
        '''
        Return invoice values for renewal
        :param renewal: the BrowseRecord of the renewal
        :return: a dictionary with renewal fields as key and renewal values as value
        '''
        party_obj = Pool().get('party.party')
        journal_obj = Pool().get('account.journal')
        payment_term_obj = Pool().get('account.invoice.payment_term')
    
        journal_id = journal_obj.search([
            ('type', '=', 'expense'),
            ], limit=1)
        if journal_id:
            journal_id = journal_id[0]

        payment_term_ids = payment_term_obj.search([('active','=',True)])
        if not len(payment_term_ids) > 0:
            self.raise_user_error('missing_payment_term')

        if not renewal.domain.party.account_receivable:
            self.raise_user_error('missing_account_receivable')

        invoice_address = party_obj.address_get(renewal.domain.party.id, type='invoice')

        res = {
            'company': renewal.domain.company.id,
            'type': 'out_invoice',
            'journal': journal_id,
            'party': renewal.domain.party.id,
            'invoice_address': invoice_address and invoice_address or renewal.domain.party_address,
            'currency': renewal.domain.company.currency.id,
            'account': renewal.domain.party.account_receivable.id,
            'payment_term': renewal.domain.party.customer_payment_term and renewal.domain.party.customer_payment_term.id or payment_term_ids[0],
            'description': self._get_invoice_description(renewal),
        }
        return res

    def _get_invoice_line_renewal(self, renewal, product, price=None):
        '''
        Return invoice line values for renewal
        :param product: the BrowseRecord of the product
        :param price: float
        :param analytic_invoice: the BrowseRecord of the analytic_invoice
        :return: a dictionary with renewal fields as key and renewal values as value
        '''
        invoice_line_obj = Pool().get('account.invoice.line')
        analytic_account_obj = Pool().get('analytic_account.account')

        if not product.account_revenue:
            self.raise_user_error('missing_account_revenue')

        vals = invoice_line_obj.on_change_product({
            'product':product.id,
            'party':renewal.domain.party.id,
            })

        res = {
            'type': 'line',
            'quantity': 1,
            'unit': vals['unit'],
            'product': product.id,
            'product_uom_category': product.category.id,
            'account': product.account_revenue.id,
            'unit_price': vals['unit_price'],
            'taxes': [('add', vals['taxes'])],
            'description': '%s - %s' % (product.name, self._get_invoice_description(renewal)),
            'sequence': 1,
        }

        if price:
            res['unit_price'] = Decimal(price)

        return res 

Renewal()

class InvoiceAsk(ModelView):
    'Invoice Ask'
    _name = 'internetdomain.invoice.ask'
    _description = __doc__

    product = fields.Many2One('product.product', 'Product', required=True)
    price = fields.Numeric('Price', digits=(16, 4), help='Force price registration. If not, get product price')

InvoiceAsk()

class Invoice(Wizard):
    'Invoice'
    _name = 'internetdomain.invoice'
    start_state = 'ask'
    ask = StateView('internetdomain.invoice.ask',
        'internetdomain_invoice.invoice_view_form', [
            Button('Cancel', 'end', 'tryton-cancel'),
            Button('Ok', 'handle', 'tryton-ok', default=True),
            ])
    handle = StateTransition()

    def transition_handle(self, session):
        renewal_obj = Pool().get('internetdomain.renewal')
        invoice_obj = Pool().get('account.invoice')
        invoice_line_obj = Pool().get('account.invoice.line')

        renewal = renewal_obj.browse(Transaction().context['active_id'])

        vals = renewal_obj._get_invoice_renewal(renewal)

        with Transaction().set_user(0, set_context=True):
            invoice_id = invoice_obj.create(vals)

        product = session.ask.product
        price = session.ask.price

        vals = renewal_obj._get_invoice_line_renewal(renewal, product, price)
        vals['invoice'] = invoice_id
        with Transaction().set_user(0, set_context=True):
            invoice_line_id = invoice_line_obj.create(vals)

        with Transaction().set_user(0, set_context=True):
            invoice_obj.update_taxes([invoice_id])

        renewal_obj.write(renewal.id, {
            'invoice': invoice_id,
        })

        return 'end'

Invoice()
