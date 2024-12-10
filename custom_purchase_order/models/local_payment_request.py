from odoo import models, fields, api, _
from odoo.exceptions import UserError
from num2words import num2words


class LocalPaymentRequest(models.Model):
    _name = 'local.payment.request'
    _description = 'Local Payment Request'
    _inherit = ["mail.thread", "mail.activity.mixin", "analytic.mixin"]
    _rec_name = 'payment_reference'

    # Fields and status definitions
    payment_reference = fields.Char(string='REFERENCE', required=True, copy=False, readonly=True, default=lambda self: _("New"))
    name = fields.Char(string='Payment Request')
    cost_center = fields.Many2one('account.analytic.account', string="Cost Center", help="Select the cost center associated with this RFQ")   
    request_date = fields.Date(string="Request Date")
    request_department = fields.Many2one('hr.department', string='Department')
    requested_by = fields.Many2one('res.users', string="Requested By")
    approved_by = fields.Many2one('res.users', string="Approved By")   
    vendor_id = fields.Many2one('res.partner', string='Pay To', required=True)    
    purpose = fields.Char(string="Purpose")    
    payment_due_date = fields.Date(string="Payment Due Date")
    total_amount = fields.Float(string='Total Amount', required=True)
    total_amount_etb = fields.Float(string='Total Amount ETB', required=True, compute='_compute_total_amount_etb' ,readonly=True)  # Compute field for ETB
    amount_in_word = fields.Char(string="Amount In Words", compute='_compute_amount_in_words',readonly=True)   
    budgetary_position = fields.Many2one('account.budget.post', string="Budget Position")
    budget_account = fields.Many2one('account.account', string="Budget Account")
    budget_rem_balance = fields.Char(string="Remaining Balance", readonly=True) 
    purchase_order_id = fields.Many2one('purchase.order', string="Purchase Order", readonly=True)
    purchase_order_reference = fields.Char(related='purchase_order_id.name', string="Purchase Order Reference", readonly=True)
    amount = fields.Float(string='Amount')
    partner_id = fields.Many2one('res.partner', string='Partner')
    communication = fields.Char(string='Communication')
    
    payment_count = fields.Integer(string="Payments Created", compute='_compute_payment_count')
    button_clicked = fields.Boolean(default=False)
    # currency_id = fields.Many2one('res.currency', string="Currency", default=lambda self: self.env.user.company_id.currency_id, required=True)

    state = fields.Selection([
        ('draft', 'Draft'),
        ('submitted', 'Submitted'), 
        ('approved', 'Approved'),  
        ('done', 'Ceo Approved'),
        ('budget', 'Budget Approved'),  
        ('pmapproved', 'Payment requested'),        
        ('cancelled', 'Cancelled'),
    ], default='draft', string='Status',tracking=True)
    
    payment_status = fields.Selection([
        ('paid', 'Request Approve'),
        ('payed', 'Payment Requested'),
    ], string="Payment Status", default='paid')
    
    payment_type = fields.Selection([
        ('partial', 'Partial'),
        ('full', 'Full'),
    ], string="Payment Type", default='full')
    
    
    currency_id = fields.Many2one('res.currency', string="Currency", required=True, default=lambda self: self.env.ref('base.ETB', raise_if_not_found=False))
    exchange_rate = fields.Float(string="Exchange Rate", compute='_compute_exchange_rate', store=True)
    show_exchange_rate = fields.Boolean(string="Show Exchange Rate", compute='_compute_show_exchange_rate')

    @api.onchange('currency_id')
    def _onchange_currency_id(self):
        # Only display exchange rate field if the currency is not ETB
        if self.currency_id:
            self.show_exchange_rate = self.currency_id.name != 'ETB'

    @api.depends('currency_id')
    def _compute_exchange_rate(self):
        """Compute exchange rate based on the selected currency."""
        for record in self:
            if record.currency_id and record.currency_id.name != 'ETB':
                exchange_rate_rec = self.env['exchange.rate'].search([('name', '=', record.currency_id.id)], limit=1)
                if exchange_rate_rec:
                    record.exchange_rate = exchange_rate_rec.exchange_rate
                else:
                    # Set a default value if no exchange rate is found and log a warning
                    record.exchange_rate = 0.0
                    _logger.warning(_("No exchange rate defined for the currency %s in the 'Exchange Rate' model."), record.currency_id.name)
            else:
                record.exchange_rate = 1.0 

    
    @api.depends('currency_id')
    def _compute_show_exchange_rate(self):
        """Compute if exchange rate should be shown based on currency."""
        for record in self:
            record.show_exchange_rate = record.currency_id.name != 'ETB'
    
    @api.depends('total_amount', 'exchange_rate')
    def _compute_total_amount_etb(self):
        for record in self:
            record.total_amount_etb = record.total_amount * record.exchange_rate if record.exchange_rate else record.total_amount

    @api.depends('total_amount_etb')
    def _compute_amount_in_words(self):
        for record in self:
            if record.total_amount_etb:
                record.amount_in_word = num2words(record.total_amount_etb, lang='en').capitalize()
            else:
                record.amount_in_word = ""

    @api.model
    def create(self, vals):
        if vals.get('payment_reference', _('New')) == _('New'):
            vals['payment_reference'] = self.env['ir.sequence'].next_by_code('local.payment.request') or _('New')
        return super(LocalPaymentRequest, self).create(vals)

    # Actions for workflow
    def action_submit(self):
        self.ensure_one()
        self.write({'state': 'submitted'})
        
    def action_approve(self):
        self.ensure_one()

        # Fetch the threshold amount from the approval.threshold model
        threshold = self.env['payment_approval.threshold'].search([], limit=1)
        
        # If no threshold record is found, raise an error
        if not threshold:
            raise UserError("Approval threshold not set. Please configure the threshold in the settings.")
        
        # Determine the new state based on the threshold comparison
        amount_exceeds = self.total_amount_etb < threshold.amount_limit
        new_state = 'approved' if not amount_exceeds else 'done'

        # Update the state and approved_by fields
        self.write({
            'state': new_state,
            'approved_by': self.env.user.id if not self.approved_by else self.approved_by.id,
        })
        
        # Prepare notification message
        if amount_exceeds:
            message = f"Successfully Approved. Payment Reference: {self.payment_reference or 'N/A'}"
        else:
            message = f"Amount exceeds the approval limit; sent to CEO for approval: {self.payment_reference or 'N/A'}"
        
        # Return a notification for clarity
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': 'Approval Process',
                'message': message,
                'type': 'info',
                'sticky': False,
            }
        }

    def action_done(self):
        self.ensure_one()
        self.write({'state': 'done'})

    def action_budget_approve(self):
        self.ensure_one()
        self.write({'state': 'budget'})  

        
     
    def action_pm_approve(self):
        self.ensure_one()
        self.write({'state': 'pmapproved'})

    def action_cancel(self):
        self.ensure_one()
        self.write({'state': 'cancelled'})

    def action_reset_to_draft(self):
        """ Resets the Payment back to draft state. """
        self.ensure_one()
        self.write({'state': 'draft'})
        
    def action_create_payment(self):
        """ Create a payment record based on the current payment request. """
        payment_method_xml_id = 'account.account_payment_method_manual_out'
        try:
            payment_method = self.env.ref(payment_method_xml_id)
        except Exception:
            raise UserError(f"The payment method '{payment_method_xml_id}' does not exist in the system.")

        # Create the payment record
        payment_vals = {
            'amount': self.total_amount_etb,
            'payment_method_id': payment_method.id,
            'payment_type': 'outbound',  # Vendor payment
            'partner_id': self.vendor_id.id,
            'partner_type': 'supplier',
            'payment_request_reference': self.payment_reference,  # Set the payment request reference
        }

        # Create the payment
        payment = self.env['account.payment'].create(payment_vals)

        return payment

    @api.depends('partner_id')
    def _compute_payment_count(self):
        for record in self:
            record.payment_count = self.env['account.payment'].search_count([('partner_id', '=', record.partner_id.id)])

    def action_paid(self):
        """ Opens the payment confirmation wizard and sets payment state to 'Paid'. """
        return {
            'type': 'ir.actions.act_window',
            'name': 'Confirm Payment',
            'res_model': 'payment.confirmation.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {'active_id': self.id},
        }

class PaymentConfirmationWizard(models.TransientModel):
    _name = 'payment.confirmation.wizard'
    _description = 'Payment Confirmation Wizard'

    def action_confirm_payment(self):
        """ Confirm the payment for the active payment request and update state to 'pmapproved'. """
        payment_request_id = self.env.context.get('active_id')
        if payment_request_id:
            payment_request = self.env['local.payment.request'].browse(payment_request_id)
            
            # Perform payment creation logic
            payment_request.action_create_payment()

            # Set payment status and update the state to 'pmapproved'
            payment_request.write({
                'payment_status': 'payed',
                'state': 'pmapproved'  # Update to the appropriate state after confirmation
            })
        else:
            raise UserError("No payment request found.")
        


class AccountPayment(models.Model):
    _inherit = 'account.payment'

    payment_request_reference = fields.Char(string='Payment Request Reference', readonly=True)
    
    



class ApprovalThreshold(models.Model):
    _name = 'payment_approval.threshold'
    _description = 'Approval Threshold for Amounts'

    name = fields.Char(string="name")
    amount_limit = fields.Float(string="Approval Limit", required=True, help="The maximum amount allowed for automatic approval.")






















# from odoo import models, fields, api, _
# from odoo.exceptions import ValidationError, UserError

# class LocalPaymentRequest(models.Model):
#     _name = 'local.payment.request'
#     _description = 'Local Payment Request'
#     _inherit = ["mail.thread", "mail.activity.mixin", "analytic.mixin"]
#     _rec_name = 'payment_reference'

#     payment_reference = fields.Char(string='REFERENCE', required=True, copy=False, readonly=True, default=lambda self: _("New"))
#     name = fields.Char(string='Payment Request')
#     cost_center = fields.Many2one('account.analytic.account', string="Cost Center", help="Select the cost center associated with this RFQ")   
#     request_date = fields.Date(string="Request Date")
#     request_department = fields.Many2one('hr.department', string='Department')
#     requested_by = fields.Many2one('res.users', string="Requested By")
#     approved_by = fields.Many2one('res.users', string="Approved By")   
#     vendor_id = fields.Many2one('res.partner', string='Pay To')    
#     purpose = fields.Char(string="Purpose")    
#     payment_due_date = fields.Date(string="Payment Due Date")
#     exchange_rate = fields.Float(string="Exchange Rate")
#     total_amount = fields.Float(string='Total Amount')
#     amount_in_word = fields.Float(string="Amount In Word")   
#     budgetary_position = fields.Many2one('account.budget.post', string="Budget Position")
#     budget_account = fields.Many2one('account.account', string="Budget Account")
#     budget_rem_balance = fields.Char(string="Remaining Balance", readonly=True) 
#     purchase_order_id = fields.Many2one('purchase.order', string="Purchase Order", readonly=True)
#     purchase_order_reference = fields.Char(related='purchase_order_id.name', string="Purchase Order Reference", readonly=True)
#     amount = fields.Float(string='Amount')
#     partner_id = fields.Many2one('res.partner', string='Partner')
#     communication = fields.Char(string='Communication')
    
#     payment_count = fields.Integer(string="Payments Created", compute='_compute_payment_count')
#     is_in_payment = fields.Boolean(string="In Payment", default=False)
#     is_payed = fields.Boolean(default=False, string="Is Payed")
    
#     state = fields.Selection([
#         ('draft', 'Draft'),
#         ('submitted', 'Submitted'),  
#         ('budget', 'Budget Approved'),      
#         ('approved', 'Approved'),        
#         ('done', 'Done'),
#         ('cancelled', 'Cancelled'),
#     ], default='draft', string='Status')
    
#     payment_status = fields.Selection([
#         ('draft', 'Draft'),
#         ('in_payment', 'In Payment'),
#         ('paid', 'Paid'),
#         ('failed', 'Failed')
#     ], string="Payment Status", default='draft')
    
#     @api.model
#     def create(self, vals):
#         if vals.get('payment_reference', _('New')) == _('New'):
#             vals['payment_reference'] = self.env['ir.sequence'].next_by_code('local.payment.request') or _('New')
#         return super(LocalPaymentRequest, self).create(vals)
    
#     def action_submit(self):
#         self.ensure_one()
#         self.write({'state': 'submitted'})
        
#     def action_budget_approve(self):
#         self.ensure_one()
#         self.write({'state': 'budget'})

#     def action_approve(self):
#         self.ensure_one()
#         if not self.approved_by:
#             self.write({'approved_by': self.env.user.id})
#         self.write({'state': 'approved'})

#     def action_done(self):
#         self.ensure_one()
#         self.write({'state': 'done'})

#     def action_cancel(self):
#         self.ensure_one()
#         self.write({'state': 'cancelled'})
        
#     def action_reset_to_draft(self):
#         """ Resets the Payment back to draft state. """
#         self.ensure_one()
#         self.write({'state': 'draft'})
        
#     def action_create_payment(self):
#         # Verify if the payment method exists
#         payment_method_xml_id = 'account.account_payment_method_manual_out'  # Adjust to your existing XML ID
#         try:
#             payment_method = self.env.ref(payment_method_xml_id)
#         except Exception:
#             raise UserError(f"The payment method '{payment_method_xml_id}' does not exist in the system.")

#         # Create the payment record
#         payment_vals = {
#             'amount': self.amount,
#             'payment_method_id': payment_method.id,
#             'payment_type': 'outbound',  # Vendor payment
#             'partner_id': self.partner_id.id, 
#             'partner_type': 'supplier',
#         }

#         # Create the payment
#         payment = self.env['account.payment'].create(payment_vals)

#         return payment

#     @api.depends('partner_id')  # Trigger recompute when partner changes
#     def _compute_payment_count(self):
#         for record in self:
#             record.payment_count = self.env['account.payment'].search_count([('partner_id', '=', record.partner_id.id)])
    
#     def action_paid(self):
#         """ Open the payment confirmation wizard. """
#         return {
#             'type': 'ir.actions.act_window',
#             'name': 'Confirm Payment',
#             'res_model': 'payment.confirmation.wizard',
#             'view_mode': 'form',
#             'target': 'new',  # Open in a modal window
#             'context': {'active_id': self.id},  # Pass the current record ID to the wizard
#         }


# class PaymentConfirmationWizard(models.TransientModel):
#     _name = 'payment.confirmation.wizard'
#     _description = 'Payment Confirmation Wizard'

#     def action_confirm_payment(self):
#         """ Confirm the payment for the active payment request. """
#         payment_request_id = self.env.context.get('active_id')
#         if payment_request_id:
#             payment_request = self.env['local.payment.request'].browse(payment_request_id)
#             payment_request.action_create_payment()  # Call method to create payment
            
#             # Set is_payed to True to change button label
#             payment_request.is_payed = True
#         else:
#             raise UserError("No payment request found.")

