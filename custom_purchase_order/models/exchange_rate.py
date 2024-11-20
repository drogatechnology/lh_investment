from odoo import models, fields, api
from odoo.exceptions import ValidationError

class ExchangeRate(models.Model):
    _name = 'exchange.rate'
    _description = 'Exchange Rate'

    # Use res.currency as a Many2one field
    name = fields.Many2one('res.currency', string="Currency", required=True)
    exchange_rate = fields.Float(string="Exchange Rate", required=True)

    _sql_constraints = [
        ('unique_currency', 'unique(name)', 'This currency already has an exchange rate.'),
    ]

    @api.constrains('name')
    def _check_unique_currency(self):
        for record in self:
            # Check if another record with the same currency exists
            existing_rate = self.search([
                ('name', '=', record.name.id),
                ('id', '!=', record.id)
            ])
            if existing_rate:
                raise ValidationError("An exchange rate for this currency already exists.")
    
    @api.constrains('name', 'exchange_rate')
    def _check_unique_currency_and_positive_rate(self):
        for record in self:
            # Check if another record with the same currency exists
            existing_rate = self.search([
                ('name', '=', record.name.id),
                ('id', '!=', record.id)
            ])
            if existing_rate:
                raise ValidationError("An exchange rate for this currency already exists.")

            # Ensure that the exchange rate is greater than 0.00
            if record.exchange_rate <= 0.00:
                raise ValidationError("Exchange rate must be greater than 0.00.")