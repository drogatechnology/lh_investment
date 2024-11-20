from odoo import models, fields, api

class PurchaseOrder(models.Model):
    _inherit = 'purchase.order'

    margin_order_ids = fields.One2many('purchase.lc.margin', 'purchase_order_id', string="Margins")


class PurchaseLCMargin(models.Model):
    _name = 'purchase.lc.margin'
    _description = 'Purchase Order LC Margin'

    purchase_order_id = fields.Many2one('purchase.order', string="Purchase Order", ondelete="cascade")
    # margin_order = fields.Char(string="Margin Order")
    margin_percentage = fields.Float(string="Margin %")
    calculation = fields.Float(string="Calculation")
    usd_amount = fields.Float(string="USD")
    exchange_rate = fields.Float(string="Exchange Rate")
    etb_amount = fields.Float(string="ETB")
    account = fields.Char(string="Account")
    move_reference = fields.Char(string="Move Reference")
    lc_reference = fields.Many2one('account.analytic.account', string="LC Reference")
    
    MARGIN_TYPE_SELECTION = [
        ('firstmargin', 'First Margin'),
        ('lastmargin', 'Last Margin'),
        ('partialmargin', 'Partial Margin '),
    ]
    
    margin_order = fields.Selection(
        selection=MARGIN_TYPE_SELECTION,
        string="Margin Order",
        required=True,
          # Set a default value if needed
    )
    
    # New Many2many field to hold LC references
    # lc_reference_ids = fields.Many2many('purchase.order.lc', string="LC References",
    #                                      domain="[('purchase_order_id', '=', purchase_order_id)]")

    

    # @api.depends('purchase_order_id')
    # def _compute_lc_reference(self):
    #     for record in self:
    #         if record.purchase_order_id:
    #             # Fetch related LC orders based on the purchase order
    #             lc_orders = self.env['purchase.order.lc'].search([('purchase_order_id', '=', record.purchase_order_id.id)])
    #             # Extract LC numbers into a list
    #             lc_numbers = lc_orders.mapped('lc_number')
    #             # Join them into a string for display
    #             record.lc_reference = ', '.join(lc_numbers)
    #         else:
    #             record.lc_reference = ''
                
    @api.model
    def create(self, vals):
        # Create the record without saving immediately
        record = super(PurchaseLCMargin, self).create(vals)
        # Prevent automatic saving logic here if needed
        return record

