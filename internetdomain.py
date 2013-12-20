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

    @classmethod
    def _get_invoice_renewal(self, renewal):
        '''
        Return invoice values for renewal
        :param renewal: the BrowseRecord of the renewal
        :return: a dict with renewal fields as key and renewal values as value
        '''
        Journal = Pool().get('account.journal')
        PaymentTerm = Pool().get('account.invoice.payment_term')

        journal_id = Journal.search([
            ('type', '=', 'expense'),
            ], limit=1)
        if journal_id:
            journal_id = journal_id[0]

        payment_term_ids = PaymentTerm.search([('active', '=', True)])
        if not len(payment_term_ids) > 0:
            self.raise_user_error('missing_payment_term')

        party = renewal.domain.party
        if not party.account_receivable:
            self.raise_user_error('missing_account_receivable',
                error_args=(party.name, party))

        invoice_address = party.address_get(type='invoice')

        res = {
            'company': renewal.domain.company.id,
            'type': 'out_invoice',
            'journal': journal_id,
            'party': party.id,
            'invoice_address': invoice_address and invoice_address or
                renewal.domain.party_address,
            'currency': renewal.domain.company.currency.id,
            'account': party.account_receivable.id,
            'payment_term': party.customer_payment_term and
                party.customer_payment_term.id or payment_term_ids[0],
            'description': renewal._get_invoice_description(),
        }
        return res

    @classmethod
    def _get_invoice_line_renewal(self, invoice, renewal, product, price=None):
        '''
        Return invoice line values for renewal
        :param renewal: the BrowseRecord of the renewal
        :param product: the BrowseRecord of the product
        :param price: float
        :return: a dict with renewal fields as key and renewal values as value
        '''
        InvoiceLine = Pool().get('account.invoice.line')

        # Test if a revenue account exists for the product
        product.account_revenue_used

        line = InvoiceLine()
        line.unit = 1
        line.quantity = 1
        line.product = product
        line.invoice = invoice
        line.description = None
        line.party = renewal.domain.party
        values = line.on_change_product()

        res = {
            'type': 'line',
            'quantity': 1,
            'unit': 1,
            'product': product.id,
            'product_uom_category': product.category and
                product.category.id or None,
            'account': values['account'],
            'unit_price': values['unit_price'],
            'taxes': [('add', product.customer_taxes_used)],
            'description': '%s - %s' % (
                    product.name,
                    renewal._get_invoice_description(),
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

        vals = Renewal._get_invoice_renewal(renewal)

        with Transaction().set_user(0, set_context=True):
            invoice = Invoice.create([vals])[0]

        product = self.ask.product
        price = self.ask.price

        vals = Renewal._get_invoice_line_renewal(invoice, renewal, product, price)
        vals['invoice'] = invoice.id
        with Transaction().set_user(0, set_context=True):
            InvoiceLine.create([vals])

        with Transaction().set_user(0, set_context=True):
            Invoice.update_taxes([invoice])

        Renewal.write([renewal], {
            'invoice': invoice.id,
        })
        return 'end'
