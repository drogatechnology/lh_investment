from odoo import models, fields, api, _
import logging

_logger = logging.getLogger(__name__)

class PurchaseOrder(models.Model):
    _inherit = 'purchase.order'

    rfq_request_id = fields.Many2one('local.create.rfq', string="Local RFQ", readonly=True)
    rfq_reference = fields.Char(related='rfq_request_id.name', string="RFQ Reference", readonly=True, store=True)
    
    rfq_foreign_request_id = fields.Many2one('foreign.create.rfq', string="Foreign RFQ", readonly=True)
    foreign_rfq_reference = fields.Char(related='rfq_foreign_request_id.foreign_reference', string="Foreign RFQ Reference", readonly=True, store=True)
    
    without_rfq_request_ids = fields.Many2one('without.rfq.local.purchase', string="Direct Purchase Request", readonly=True)
    without_rfq_reference = fields.Char(related='without_rfq_request_ids.reference_wrfq', string='Direct Purchase Reference', readonly=True, store=True)
    
    payment_request_id = fields.Many2one('local.payment.request', string="Payment Request")
    payment_created = fields.Boolean(string="Payment Created", default=False)
    custom_count = fields.Integer(string="Payment Request", compute='_compute_custom_count')
    
    purchase_type = fields.Selection([
        ('local', 'Local Purchase'),
        ('foreign', 'Foreign Purchase'),
        ('direct', 'Direct Purchase')
        
    ], string='Purchase Type',default = 'local')

    reference = fields.Char(string='REFERENCE', required=True, copy=False, readonly=True, default=lambda self: _("New"))

    
    @api.model
    def create(self, vals):
        """Override create method to set unique reference for purchase order and purchase type based on context."""
        # Set default reference if it's 'New'
        if vals.get('reference', _('New')) == _('New'):
            vals['reference'] = self.env['ir.sequence'].next_by_code('purchase.order') or _('New')

        # Set the purchase type based on context
        context_purchase_type = self.env.context.get('purchase_type')
        if context_purchase_type == 'local':
            vals['purchase_type'] = 'local'
        elif context_purchase_type == 'foreign':
            vals['purchase_type'] = 'foreign'
        elif context_purchase_type == 'direct':
            vals['purchase_type'] = 'direct'
        # else:
        #     # Default value for purchase_type if no valid context is provided
        #     vals['purchase_type'] = 'local'

        # Create the purchase order
        order = super(PurchaseOrder, self).create(vals)

        # Generate the sequence based on purchase type
        if order.purchase_type == 'local':
            order.name = self.env['ir.sequence'].next_by_code('local.purchase.order.sequence') or '/'
        elif order.purchase_type == 'foreign':
            order.name = self.env['ir.sequence'].next_by_code('foreign.purchase.order.sequence') or '/'
        elif order.purchase_type == 'direct':
            order.name = self.env['ir.sequence'].next_by_code('direct.purchase.order.sequence') or '/'

        return order
    
    
    
   


    
    def create_po_from_rfq(self, rfq_id):
        """Creates a Purchase Order from the given RFQ."""
        rfq = self.env['local.create.rfq'].browse(rfq_id)
        if not rfq:
            return

        po_vals = {
            'rfq_request_id': rfq.id,
            'purchase_type': 'local',  # Assuming it’s meant to be a local PO
            'partner_id': rfq.vendor_id.id,  # Vendor from the RFQ
            # Add other required fields for purchase.order, e.g., 'company_id'
        }

        # Create the purchase order in the correct model
        po = self.env['purchase.order'].with_context(purchase_type='local').create(po_vals)

        # Copy RFQ lines to the PO lines
        for rfq_line in rfq.line_ids:
            po_line_vals = {
                'order_id': po.id,
                'product_id': rfq_line.product_id.id,
                'product_qty': rfq_line.quantity,
                'price_unit': rfq_line.price_unit,
                # 'vendor_id': rfq_line.vendor_id.id,  # Only if vendor_id exists in purchase.order.line
                'date_planned': fields.Datetime.now(),  # Adjust as needed
            }
            self.env['purchase.order.line'].create(po_line_vals)

        return po

    
   

    def create_po_from_without_rfq(self, request_id):
        """Creates a Purchase Order from the given Direct Purchase Request."""
        request = self.env['without.rfq.local.purchase'].browse(request_id)
        if not request:
            return

        po_vals = {
            'without_rfq_request_ids': request.id,
            'purchase_type': 'direct',
            'partner_id': request.vendor_id.id,
        }

        # Create the purchase order
        po = self.create(po_vals)

        # Copy lines to the PO lines
        for line in request.line_ids:
            line_vals = {
                'order_id': po.id,
                'product_id': line.product_id.id,
                'product_qty': line.quantity,
                'price_unit': line.price_unit,
                'date_planned': fields.Datetime.now(),
            }
            self.env['purchase.order.line'].create(line_vals)

        return po

    def create_po_from_foreign_rfq(self, foreign_rfq_id):
        """Creates a Purchase Order from the given Foreign RFQ."""
        request = self.env['foreign.create.rfq'].browse(foreign_rfq_id)
        if not request:
            return

        po_vals = {
            'rfq_foreign_request_id': request.id,
            'purchase_type': 'foreign',
            'partner_id': request.vendor_id.id,
        }

        # Create the purchase order
        po = self.create(po_vals)

        # Copy lines to the PO lines
        for line in request.line_ids:
            line_vals = {
                'order_id': po.id,
                'product_id': line.product_id.id,
                'product_qty': line.quantity,
                'price_unit': line.price_unit,
                'date_planned': fields.Datetime.now(),
            }
            self.env['purchase.order.line'].create(line_vals)

        return po
    
    
    @api.depends('payment_request_id')  # Use the correct field that links to your payment requests
    def _compute_custom_count(self):
        """ Compute the count of related Payment Requests. """
        for record in self:
            record.custom_count = len(self.env['local.payment.request'].search([
                ('purchase_order_id', '=', record.id)
            ]))
    
    def custom_create_function(self):
        """ Create a payment request for the purchase order each time the button is clicked. """
        for rec in self:
            # Ensure that the partner_id is correctly referenced from the purchase order
            if not rec.partner_id:
                raise UserError(_("The partner (Vendor) must be set before creating a payment request."))

            # Use the amount_total field directly
            total_amount = rec.amount_total

            # Create the payment request
            payment_request_details = self.env['local.payment.request'].create({
                'name': 'Payment Request %s' % rec.name,
                'purchase_order_id': rec.id,  # Set the purchase order reference
                'vendor_id': rec.partner_id.id,  # Use partner_id as vendor_id
                'partner_id': rec.partner_id.id,  # Assuming partner_id is also the same
                'total_amount': total_amount,  # Set the total amount calculated
            })
            
            # Update the payment request ID and increment the count
            rec.payment_request_id = payment_request_details.id
            
            # Increment custom_count each time a payment request is created
            rec.custom_count += 1









    def action_view_create_payment(self):
        """ Opens the list of related Payment Requests for the Purchase Order. """
        self.ensure_one()
        
        # Fetch the payment requests related to this purchase order
        payment_requests = self.env['local.payment.request'].search([
            ('purchase_order_id', '=', self.id)
            
        ])
        
        # Return the action to open the list of payment requests
        return {
            'type': 'ir.actions.act_window',
            'name': _('Payment Requests (%d)' % len(payment_requests)),  # Display count in the title
            'res_model': 'local.payment.request',
            'view_mode': 'tree,form',
            'domain': [('purchase_order_id', '=', self.id)],
            'target': 'current',
        }

    
    
    
    
    
    
    
    
    
    
    # #######################################################################################################
    
    ordering_notes = fields.Text(string='Ordering Notes')
    import_permit_number = fields.Char(string="Import Permit Number")
    insurance_policy_number = fields.Char(string="Insurance Policy Number")
    insurance_company = fields.Char(string="Insurance Company Name")
    lc_number = fields.Char(string="Letter of Credit Number")
    lc_amount = fields.Float(string="Letter of Credit Amount")
    lc_expiry_date = fields.Date(string="Letter of Credit Expiry Date")
    margin_percentage = fields.Float(string="Margin Percentage")
    margin_amount = fields.Float(string="Margin Amount")
    notes = fields.Text(string="Notes")
    insurance_date = fields.Date(string="")
    insurance_premium_cost = fields.Float(string="Insurance Premium Cost")
    import_permit_date = fields.Date(string="Import Permit Date")
    import_permit_approved = fields.Boolean(string="Import Permit Approved")
    lpco_number = fields.Char(string="LPCO Number")
    margin = fields.Char(string="Margins")
    deposit_amount = fields.Float(string="Margin Amount")
    deposit_date = fields.Date(string="Deposit Date")
    bank_service_charge = fields.Float(string="Bank Service Charge")
    
    
    
    
    
    
    




















# from odoo import models, fields, api, _

# class PurchaseOrder(models.Model):
#     _inherit = 'purchase.order'

#     rfq_request_id = fields.Many2one('local.create.rfq', string="Local RFQ", readonly=True)
#     rfq_reference = fields.Char(related='rfq_request_id.name', string="RFQ Reference", readonly=True, store=True)
    
#     rfq_foreign_request_id = fields.Many2one('foreign.create.rfq', string="Foreign RFQ", readonly=True)
#     foreign_rfq_reference = fields.Char(related='rfq_foreign_request_id.foreign_reference', string="Foreign RFQ Reference", readonly=True, store=True)
    
#     without_rfq_request_ids = fields.Many2one('without.rfq.local.purchase', string="Direct Purchase Request", readonly=True)
#     without_rfq_reference = fields.Char(related='without_rfq_request_ids.reference_wrfq', string='Direct Purchase Reference', readonly=True, store=True)
    
#     payment_request_id = fields.Many2one('local.payment.request' ,string="Payment Request")
    
#     payment_request_id = fields.Many2one('local.payment.request', string="Payment Request")
#     paymnet_created = fields.Boolean(string="Payment Created", default=False)
#     custom_count = fields.Integer(string="Payment Count", default=0)
    
    
#     purchase_type = fields.Selection([
#         ('local', 'Local Purchase'),
#         ('foreign', 'Foreign Purchase'),
#         ('direct', 'Direct Purchase')
#     ], string='Purchase Type', default='foreign')

#     reference = fields.Char(string='REFERENCE', required=True, copy=False, readonly=True, default=lambda self: _("New"))

    # @api.model
    # def create(self, vals):
    #     """ Override create method to set a unique reference for purchase orders based on purchase type."""
    #     # Set default reference if it is 'New'
    #     if vals.get('reference', _('New')) == _('New'):
    #         vals['reference'] = self.env['ir.sequence'].next_by_code('purchase.order') or _('New')

    #     # Set the purchase type based on context
    #     context_purchase_type = self.env.context.get('purchase_type')
    #     if context_purchase_type:
    #         vals['purchase_type'] = context_purchase_type

    #     # Create the purchase order
    #     order = super(PurchaseOrder, self).create(vals)

    #     # Generate the sequence based on purchase type
    #     if order.purchase_type == 'local':
    #         order.name = self.env['ir.sequence'].next_by_code('local.purchase.order.sequence') or '/'
    #     elif order.purchase_type == 'foreign':
    #         order.name = self.env['ir.sequence'].next_by_code('foreign.purchase.order.sequence') or '/'
    #     elif order.purchase_type == 'direct':
    #         order.name = self.env['ir.sequence'].next_by_code('direct.purchase.order.sequence') or '/'

    #     return order

    # def create_po_from_rfq(self, rfq_id):
    #     """Creates a Purchase Order from the given Local RFQ."""
    #     rfq = self.env['local.create.rfq'].browse(rfq_id)
    #     if not rfq:
    #         return

    #     po_vals = {
    #         'rfq_request_id': rfq.id,
    #         'purchase_type': 'local',
    #         'partner_id': rfq.vendor_id.id,
    #     }

    #     # Create the purchase order
    #     po = self.create(po_vals)

    #     # Copy RFQ lines to the PO lines
    #     for rfq_line in rfq.line_ids:
    #         po_line_vals = {
    #             'order_id': po.id,
    #             'product_id': rfq_line.product_id.id,
    #             'product_qty': rfq_line.quantity,
    #             'price_unit': rfq_line.price_unit,
    #             'date_planned': fields.Datetime.now(),
    #         }
    #         self.env['purchase.order.line'].create(po_line_vals)

    #     return po

    # def create_po_from_without_rfq(self, request_id):
    #     """Creates a Purchase Order from the given Direct Purchase Request."""
    #     request = self.env['without.rfq.local.purchase'].browse(request_id)
    #     if not request:
    #         return

    #     po_vals = {
    #         'without_rfq_request_ids': request.id,
    #         'purchase_type': 'direct',
    #         'partner_id': request.vendor_id.id,
    #     }

    #     # Create the purchase order
    #     po = self.create(po_vals)

    #     # Copy lines to the PO lines
    #     for line in request.line_ids:
    #         line_vals = {
    #             'order_id': po.id,
    #             'product_id': line.product_id.id,
    #             'product_qty': line.quantity,
    #             'price_unit': line.price_unit,
    #             'date_planned': fields.Datetime.now(),
    #         }
    #         self.env['purchase.order.line'].create(line_vals)

    #     return po

    # def create_po_from_foreign_rfq(self, foreign_rfq_id):
    #     """Creates a Purchase Order from the given Foreign RFQ."""
    #     request = self.env['foreign.create.rfq'].browse(foreign_rfq_id)
    #     if not request:
    #         return

    #     po_vals = {
    #         'rfq_foreign_request_id': request.id,
    #         'purchase_type': 'foreign',
    #         'partner_id': request.vendor_id.id,
    #     }

    #     # Create the purchase order
    #     po = self.create(po_vals)

    #     # Copy lines to the PO lines
    #     for line in request.line_ids:
    #         line_vals = {
    #             'order_id': po.id,
    #             'product_id': line.product_id.id,
    #             'product_qty': line.quantity,
    #             'price_unit': line.price_unit,
    #             'date_planned': fields.Datetime.now(),
    #         }
    #         self.env['purchase.order.line'].create(line_vals)

    #     return po
    
    
    

    # def custom_create_function(self):
    #     for rec in self:
    #         if not rec.paymnet_created:
    #             payment_request_details = self.env['local.payment.request'].create({
    #                 'name': 'Payment Request %s' % rec.name,
    #                 'purchase_order_id': rec.id,  # Set the purchase order reference
    #             })
    #             rec.payment_request_id = payment_request_details.id
    #             rec.paymnet_created = True
    #             rec.custom_count = 1

#             if rec.payment_request_id:
#                 return {
#                     'type': 'ir.actions.act_window',
#                     'name': 'Payment Request',
#                     'view_mode': 'form',
#                     'res_model': 'local.payment.request',
#                     'res_id': rec.payment_request_id.id,
#                     'view_id': self.env.ref('custom_purchase_order.view_local_payment_request_form').id,
#                     'target': 'current',
#                 }
#         return {}


        
    
    
    
    

























# from odoo import models, fields, api, _


# class PurchaseOrder(models.Model):
#     _inherit = 'purchase.order'

#     rfq_request_id = fields.Many2one('local.create.rfq', string="Local RFQ", readonly=True)
#     rfq_reference = fields.Char(related='rfq_request_id.name', string="RFQ Reference", readonly=True, store=True)
#     purchase_type = fields.Selection([
#         ('local', 'Local Purchase'),
#         ('foreign', 'Foreign Purchase')
#     ], string='Purchase Type', default='foreign')

#     local_field = fields.Char(string='Local Specific Field')
#     foreign_field = fields.Char(string='Foreign Specific Field')

#     reference = fields.Char(string='REFERENCE', required=True, copy=False, readonly=True, default=lambda self: _("New"))
    
#     # New field to hold the RFQ reference related to this purchase order
#     # rfq_related_references = fields.Char(string="reference")
#     rfq_related_reference = fields.Char(string='RFQ Related Reference', related='rfq_request_id.reference', readonly=True)  # Adjust the related field accordingly

#     @api.model
#     def create(self, vals):
#         """ Override create method to set unique reference for purchase order. """
#         if vals.get('reference', _('New')) == _('New'):
#             vals['reference'] = self.env['ir.sequence'].next_by_code('purchase.order') or _('New')
#         return super(PurchaseOrder, self).create(vals)

#     @api.model
#     def create(self, vals):
#         # Set the purchase type based on context
#         if self.env.context.get('purchase_type') == 'foreign':
#             vals['purchase_type'] = 'foreign'
#         else:
#             vals['purchase_type'] = 'local'  # Default to local if not specified

#         # Create the purchase order
#         order = super(PurchaseOrder, self).create(vals)

#         # Generate the sequence based on purchase type
#         if order.purchase_type == 'local':
#             order.name = self.env['ir.sequence'].next_by_code('local.purchase.order.sequence') or '/'
#         elif order.purchase_type == 'foreign':
#             order.name = self.env['ir.sequence'].next_by_code('foreign.purchase.order.sequence') or '/'

#         return order

#     def create_po_from_rfq(self, rfq_id):
#         """Creates a Purchase Order from the given RFQ."""
#         rfq = self.env['local.create.rfq'].browse(rfq_id)
#         if not rfq:
#             return

#         po_vals = {
#             'rfq_request_id': rfq.id,
#             'purchase_type': rfq.purchase_type,
#             'partner_id': rfq.vendor_id.id,  # Vendor from the RFQ
#         }

#         # Create the purchase order
#         po = self.create(po_vals)

#         # Copy RFQ lines to the PO lines
#         for rfq_line in rfq.line_ids:
#             po_line_vals = {
#                 'order_id': po.id,
#                 'product_id': rfq_line.product_id.id,
#                 'product_qty': rfq_line.quantity,
#                 'price_unit': rfq_line.price_unit,
#                 'vendor_id': rfq_line.vendor_id.id,
#                 'date_planned': fields.Datetime.now(),  # Or use a relevant date from RFQ
#             }
#             self.env['purchase.order.line'].create(po_line_vals)

#         return po
