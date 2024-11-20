from odoo import models, fields, api


class PurchaseOrder(models.Model):
    _inherit = 'purchase.order'

    lc_order_ids = fields.One2many('purchase.order.lc', 'purchase_order_id', string="LC Orders")


class PurchaseOrderLC(models.Model):
    _name = 'purchase.order.lc'
    _description = 'Purchase Order LC'
    _rec_name = 'lc_number'

    lc_number = fields.Char(string="LC/TT Number")
    bank = fields.Char(string="Bank")
    branch = fields.Char(string="Branch")
    issue_date = fields.Date(string="Issue Date")
    expire_date = fields.Date(string="Expire Date")
    last_day_shipment = fields.Date(string="Last Shipment Date")
    request_approved_date = fields.Date(string="Request Approved Date")
    total_amount_usd = fields.Float(string="Total Amount USD/Others")
    exchange_rate = fields.Float(string="Exchange Rate")
    total_amount_etb = fields.Float(string="Total Amount ETB")
    draft_lc_approved = fields.Date(string="Draft LC Approved Date")
    draft_lc_approved_by_supplier = fields.Date(string="Draft LC Approved Date by Supplier")
    lc_send_date_to_supplier = fields.Date(string="LC Send to Supplier Date")
    lc_received_date_from_bank = fields.Date(string="LC Received Date from Bank")

    state = fields.Selection([
        ('draft', 'Draft'),
        ('active', 'Active'),
        ('expired', 'Expired'),
        ('closed', 'Closed')
    ], string="State", default="draft")

    purchase_order_id = fields.Many2one('purchase.order', string="Purchase Order", ondelete="cascade")

    # Related field to display the reference (name) of the selected purchase order
    existing_purchase_order_reference = fields.Char(
        string="Purchase Order Reference",
        related='purchase_order_id.name',
        readonly=True
    )

    def action_activate(self):
        """ Set state to Active """
        self.state = 'active'

    def action_expire(self):
        """ Set state to Expired """
        self.state = 'expired'

    def action_close(self):
        """ Set state to Closed """
        self.state = 'closed'

    def action_cancel(self):
        """ Reset state to Draft """
        self.state = 'draft'





# from odoo import models, fields, api


# class PurchaseOrder(models.Model):
#     _inherit = 'purchase.order'

#     lc_order_ids = fields.One2many('purchase.order.lc', 'purchase_order_id', string="LC Orders")

# class PurchaseOrderLC(models.Model):
#     _name = 'purchase.order.lc'
#     _description = 'Purchase Order LC'

#     lc_number = fields.Char(string="LC/TT Number")
#     bank = fields.Char(string="Bank")
#     branch = fields.Char(string="Branch")
#     issue_date = fields.Date(string="Issue Date")
#     expire_date= fields.Date(string="Expire Date")
#     last_day_shipment = fields.Date(string="Last Shipment Date")
#     request_approved_date = fields.Date(string="Request Approved Date")
#     total_amount_usd = fields.Float(string="Total Amount USD/Others")
#     exchange_rate = fields.Float(string="Exchange Rate")
#     total_amount_etb = fields.Float(string="Total Amount ETB")
#     draft_lc_approved = fields.Date(string="Draft LC Approved Date")
#     draft_lc_approved_by_supplier= fields.Date(string="Draft LC Approved Date by supplier")
#     lc_send_date_to_supplier = fields.Date(string="LC Send to Supplier Date")
#     lc_received_date_from_bank = fields.Date(string="LC Received Date from Bank ")
    
    
#     state = fields.Selection([
#         ('draft', 'Draft'),
#         ('active', 'Active'),
#         ('expired', 'Expired'),
#         ('closed', 'Closed')
#     ], string="State", default="draft")

#     purchase_order_id = fields.Many2one('purchase.order', string="Purchase Order", ondelete="cascade")

#     # New field to display the existing purchase order
#     existing_purchase_order_id = fields.Many2one(
#         'purchase.order', 
#         string="Purchase Order", 
        
#         readonly=True
#     )

#     @api.onchange('purchase_order_id')
#     def _onchange_purchase_order_id(self):
#         """ Automatically set the existing purchase order field when a purchase order is selected. """
#         if self.purchase_order_id:
#             self.existing_purchase_order_id = self.purchase_order_id.id
#         else:
#             self.existing_purchase_order_id = False

#     def action_save(self):
#         """ Save the LC entry and close the wizard. """
#         self.ensure_one()  # Ensure we are working with a single record
#         self.write({})  # This will trigger the save for the record

#         return {'type': 'ir.actions.act_window_close'}  # Close the wizard

#     def action_discard(self):
#         """ Close the wizard without saving changes. """
#         return {'type': 'ir.actions.act_window_close'}

#     @api.model
#     def create(self, vals):
#         """ Override create method to set existing purchase order ID. """
#         if 'purchase_order_id' in vals:
#             vals['existing_purchase_order_id'] = vals['purchase_order_id']
#         return super(PurchaseOrderLC, self).create(vals)

#     def write(self, vals):
#         """ Override write method to ensure existing purchase order ID is updated. """
#         if 'purchase_order_id' in vals:
#             vals['existing_purchase_order_id'] = vals['purchase_order_id']
#         return super(PurchaseOrderLC, self).write(vals)

#     def action_activate(self):
#         """ Set state to Active """
#         self.state = 'active'

#     def action_expire(self):
#         """ Set state to Expired """
#         self.state = 'expired'

#     def action_close(self):
#         """ Set state to Closed """
#         self.state = 'closed'

    
        

#     def action_cancel(self):
#         """ Reset state to Draft """
#         self.state = 'draft'
        
   



