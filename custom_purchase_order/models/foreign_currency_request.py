from odoo import models, fields, api, _
from odoo.exceptions import UserError
from num2words import num2words

class ForeignCurrencyRequest(models.Model):
    _name = 'foreign.currency.request'
    _description = 'Foreign Currency Request'
    _inherit = ["mail.thread", "mail.activity.mixin", "analytic.mixin"]
    _rec_name = 'foreign_currency_request_reference'

    # Fields and status definitions
    foreign_rfq_reference = fields.Many2one('foreign.create.rfq', string="Foreign RFQ", readonly=True)    
    foreign_rfq_id = fields.Char(related='foreign_rfq_reference.foreign_reference', string="Foreign RFQ Reference", readonly=True, store=True)
    
    foreign_currency_request_reference = fields.Char(string='REFERENCE', required=True, copy=False, readonly=True, default=lambda self: _("New"))
    
    name = fields.Char(string='Payment Request')
    proforma_invoice = fields.Many2one('account.analytic.account', string="Cost Center", help="Select the cost center associated with this RFQ")   
    requested_by = fields.Many2one('res.users', string="Requested By",tracking=True)
    request_department = fields.Many2one('hr.department', string='Department')
    request_date = fields.Date(string="Request Date",tracking=True)
    currency_id = fields.Many2one('res.currency', string="Currency", required=True, default=lambda self: self.env.ref('base.USD', raise_if_not_found=False),tracking=True)
    purpose = fields.Char(string="Purpose",tracking=True)
    nbe_number = fields.Float(string="NBE", default=1.00)
    vendor_id = fields.Many2one('res.partner', string='Supplier', required=True,tracking=True)  
    payment_due_date = fields.Date(string="Payment Due Date",tracking=True)
    price_amount = fields.Float(string='Total Amount USD', required=True,tracking=True)
    exchange_rate = fields.Float(string="Exchange Rate", readonly=True)
    total_amount_etb = fields.Float(string='Total Amount ETB', required=True, compute='_compute_total_amount_etb', readonly=True)
    amount_in_word = fields.Char(string="Amount In Words", compute='_compute_amount_in_words', readonly=True)
    approved_date = fields.Date(string="Approved Date")
    bank = fields.Many2one('res.bank', string="Bank",tracking=True)
    branch = fields.Char(string="Branch",tracking=True)
    
    state = fields.Selection([
        ('draft', 'Draft'),
        ('queued', 'Queued'),  
        ('on_progress', 'On Progress'),      
        ('approved', 'Approved'),       
        ('cancelled', 'Cancelled'),
    ], default='draft', string='Status',tracking=True)

    @api.onchange('currency_id')
    def _onchange_currency_id(self):
        if self.currency_id:
            # Search for the exchange rate in 'exchange.rate' model for the selected currency
            exchange_rate_rec = self.env['exchange.rate'].search([('name', '=', self.currency_id.id)], limit=1)
            if exchange_rate_rec:
                self.exchange_rate = exchange_rate_rec.exchange_rate
            else:
                raise UserError(_("No exchange rate defined for the selected currency in 'Exchange Rate' model."))
    
    @api.depends('price_amount', 'exchange_rate')
    def _compute_total_amount_etb(self):
        for record in self:
            record.total_amount_etb = record.price_amount * record.exchange_rate if record.exchange_rate else record.price_amount

    @api.depends('total_amount_etb')
    def _compute_amount_in_words(self):
        for record in self:
            if record.total_amount_etb:
                record.amount_in_word = num2words(record.total_amount_etb, lang='en').capitalize()
            else:
                record.amount_in_word = ""

    @api.model
    def create(self, vals):
        if vals.get('foreign_currency_request_reference', _('New')) == _('New'):
            vals['foreign_currency_request_reference'] = self.env['ir.sequence'].next_by_code('foreign.currency.request') or _('New')
        return super(ForeignCurrencyRequest, self).create(vals)

    def action_submit(self):
        self.ensure_one()
        self.write({'state': 'queued'})
        

    # def action_queue(self):
    #     self.ensure_one()
    #     self.write({'state': 'approved'})

    def action_approve(self):
        self.ensure_one()
        
        self.write({'state': 'approved'})

    def action_cancel(self):
        self.ensure_one()
        self.write({'state': 'cancelled'})

    def action_reset_to_draft(self):
        """ Resets the Payment back to draft state. """
        self.ensure_one()
        self.write({'state': 'draft'})
        
    def create_foreign_currency_from_foreign_rfq(self, foreign_rfq_id):
        """ Creates a foreign currency request from the given Foreign RFQ. """
        request = self.env['foreign.create.rfq'].browse(foreign_rfq_id)
        if not request:
            return

        # Prepare the values to create a Foreign Currency Request
        vals = {
            'rfq_foreign_request_id': request.id,  # Link to the Foreign RFQ
            'foreign_rfq_reference': request.foreign_reference,
            'vendor_id': request.vendor_id.id,  # Vendor from RFQ
            'price_amount': request.price_total,  # Total Amount from RFQ
            'currency_id': self.env.company.currency_id.id,  # Default currency of the company
            'requested_by': self.env.user.id,  # Requestor is the current user
            'request_date': fields.Date.today(),
        }

        # Create the Foreign Currency Request
        foreign_currency_request = self.create(vals)

        # Return the created record's action
        return {
            'type': 'ir.actions.act_window',
            'name': 'Foreign Currency Request',
            'view_mode': 'form',
            'res_model': 'foreign.currency.request',
            'res_id': foreign_currency_request.id,  # Open the created record
            'target': 'new',  # Opens in a new modal window
        }
