#This file is part account_invoice_cancel module for Tryton.
#The COPYRIGHT file at the top level of this repository contains
#the full copyright notices and license terms.
from trytond.model import ModelView, fields
from trytond.transaction import Transaction
from trytond.pool import Pool, PoolMeta
from trytond.pyson import Eval
from trytond.wizard import Wizard, StateView, StateTransition, Button
from decimal import Decimal

__all__ = ['Renewal', 'CreateInvoice', 'Invoice']
__metaclass__ = PoolMeta


class Domain:
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
    __name__ = 'internetdomain.renewal'
    invoice = fields.Many2One('account.invoice', 'Invoice', readonly=True)

    @classmethod
    def __setup__(cls):
        super(Renewal, cls).__setup__()
        cls._error_messages.update({
                'missing_payment_term': 'A payment term has not been defined.',
                'missing_account_receivable': 'Party "%s" (%s) must have a '
                    'receivable account.',
                })
        cls._buttons.update({
                'create_invoice': {
                    'invisible': Eval('invoice', False),
                },
                })

    @classmethod
    def copy(cls, renewals, default=None):
        if default is None:
            default = {}
        default = default.copy()
        default.setdefault('invoice', None)
        return super(Renewal, cls).copy(renewals, default=default)

    @classmethod
    @ModelView.button_action('internetdomain_invoice.wizard_invoice')
    def create_invoice(cls, renewals):
        pass

    def _get_invoice_description(self):
        '''
        Return the renewal description
        :param renewal: the BrowseRecord of the renewal
        :return: str
        '''
        description = (self.domain.name +
            ' (' + str(self.date_renewal) +
            ' / ' + str(self.date_expire) + ')')
        return description


class CreateInvoice(ModelView):
    'Create Invoice'
    __name__ = 'internetdomain.invoice.ask'
    product = fields.Many2One('product.product', 'Product', required=True)
    price = fields.Numeric('Price', digits=(16, 4),
        help=('It will be used as the invoice line price. If is not filled, '
            'the sale price of the product will be used instead.'))


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

        product = self.ask.product
        price = self.ask.price

        #Create Invoice
        party = renewal.domain.party
        description = renewal._get_invoice_description()
        invoice_type = 'out_invoice'
        invoice = Invoice.get_invoice_data(party, description, invoice_type)
        with Transaction().set_user(0, set_context=True):
            invoice.save()

        #Create Invoice line
        quantity = 1
        line = InvoiceLine.get_invoice_line_data(invoice, product, quantity)
        if price:
            line.unit_price = price
        with Transaction().set_user(0, set_context=True):
            line.save()

        #Update taxes
        with Transaction().set_user(0, set_context=True):
            Invoice.update_taxes([invoice])

        Renewal.write([renewal], {
            'invoice': invoice.id,
        })
        return 'end'
