#This file is part account_invoice_cancel module for Tryton.
#The COPYRIGHT file at the top level of this repository contains 
#the full copyright notices and license terms.

from trytond.model import ModelView, ModelSQL, fields
from trytond.transaction import Transaction
from trytond.pool import Pool, PoolMeta
from trytond.pyson import If, Eval, Bool
from trytond.wizard import Wizard, StateAction, StateView, StateTransition, \
    Button

from decimal import Decimal
import datetime

__all__ = ['Renewal', 'CreateInvoice', 'Invoice']
__metaclass__ = PoolMeta

class Domain:
    'Domain'
    __name__ = 'internetdomain.domain'

    def on_change_party(self):
        address = None
        changes = {}
        if self.party:
            address = self.party.address_get(type='invoice')
        if address:
            changes['party_address'] = address.id
        return changes

class Renewal:
    'Renewal'
    __name__ = 'internetdomain.renewal'

    invoice = fields.Many2One('account.invoice', 'Invoice', readonly=True)

    @classmethod
    def __setup__(cls):
        super(Renewal, cls).__setup__()
        cls._error_messages.update({
            'missing_payment_term': 'Not available Payment Type!',
            'missing_account_receivable': 'Party not available Account Receivable!',
            'missing_account_revenue': 'Product not available Account Revenue!',
            })
        cls._buttons.update({
            'create_invoice': {
                'invisible': Eval('invoice', False),
            },
            })

    @classmethod
    @ModelView.button_action('internetdomain_invoice.wizard_invoice')
    def create_invoice(cls, renewals):
        pass

    @classmethod
    def _get_invoice_description(self, renewal):
        '''
        Return description renewal
        :param renewal: the BrowseRecord of the renewal
        :return: str
        '''
        description = renewal.domain.name+' ('+str(renewal.date_renewal)+' / '+str(renewal.date_expire)+')'
        return description

    @classmethod
    def _get_invoice_renewal(self, renewal):
        '''
        Return invoice values for renewal
        :param renewal: the BrowseRecord of the renewal
        :return: a dictionary with renewal fields as key and renewal values as value
        '''
        Party = Pool().get('party.party')
        Journal = Pool().get('account.journal')
        PaymentTerm = Pool().get('account.invoice.payment_term')
    
        journal_id = Journal.search([
            ('type', '=', 'expense'),
            ], limit=1)
        if journal_id:
            journal_id = journal_id[0]

        payment_term_ids = PaymentTerm.search([('active','=',True)])
        if not len(payment_term_ids) > 0:
            self.raise_user_error('missing_payment_term')

        if not renewal.domain.party.account_receivable:
            self.raise_user_error('missing_account_receivable')

        invoice_address = renewal.domain.party.address_get(type='invoice')

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

    @classmethod
    def _get_invoice_line_renewal(self, invoice, renewal, product, price=None):
        '''
        Return invoice line values for renewal
        :param renewal: the BrowseRecord of the renewal
        :param product: the BrowseRecord of the product
        :param price: float
        :return: a dictionary with renewal fields as key and renewal values as value
        '''
        InvoiceLine = Pool().get('account.invoice.line')
        Product = Pool().get('product.product')

        if not product.account_revenue and not (product.category and product.category.account_revenue):
            self.raise_user_error('missing_account_revenue')

        res = {
            'type': 'line',
            'quantity': 1,
            'unit': 1,
            'product': product.id,
            'product_uom_category': product.category and product.category.id or None,
            'account': product.account_revenue and product.account_revenue.id \
                or product.category.account_revenue.id,
            'unit_price': product.list_price,
            'taxes': [('add', product.customer_taxes)],
            'description': '%s - %s' % (
                    product.name, 
                    self._get_invoice_description(renewal),
                    ),
            'sequence': 1,
        }
        if price:
            res['unit_price'] = Decimal(price)
        return res


class CreateInvoice(ModelView):
    'Create Invoice'
    __name__ = 'internetdomain.invoice.ask'

    product = fields.Many2One('product.product', 'Product', required=True)
    price = fields.Numeric('Price', digits=(16, 4), help='Force price registration. If not, get product price')


class Invoice(Wizard):
    'Invoice'
    __name__ = 'internetdomain.invoice'
    start_state = 'ask'
    ask = StateView('internetdomain.invoice.ask',
        'internetdomain_invoice.invoice_view_form', [
            Button('Cancel', 'end', 'tryton-cancel'),
            Button('Ok', 'handle', 'tryton-ok', default=True),
            ])
    handle = StateTransition()

    def transition_handle(self):
        Renewal = Pool().get('internetdomain.renewal')
        Invoice = Pool().get('account.invoice')
        InvoiceLine = Pool().get('account.invoice.line')

        renewal = Renewal(Transaction().context['active_id'])

        vals = Renewal._get_invoice_renewal(renewal)

        with Transaction().set_user(0, set_context=True):
            invoice = Invoice.create(vals)

        product = self.ask.product
        price = self.ask.price

        vals = Renewal._get_invoice_line_renewal(invoice, renewal, product, price)
        vals['invoice'] = invoice.id
        with Transaction().set_user(0, set_context=True):
            invoice_line_id = InvoiceLine.create(vals)

        with Transaction().set_user(0, set_context=True):
            Invoice.update_taxes([invoice])

        Renewal.write([renewal], {
            'invoice': invoice.id,
        })
        return 'end'
