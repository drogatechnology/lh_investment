from odoo import models, fields, api, _


class PurchaseOrder(models.Model):
    _inherit = 'purchase.order'

    rfq_request_id = fields.Many2one('local.create.rfq', string="Local RFQ", readonly=True)
    rfq_reference = fields.Char(related='rfq_request_id.name', string="RFQ Reference", readonly=True, store=True)
    purchase_type = fields.Selection([
        ('local', 'Local Purchase'),
        ('foreign', 'Foreign Purchase')
    ], string='Purchase Type', default='foreign')

    local_field = fields.Char(string='Local Specific Field')
    foreign_field = fields.Char(string='Foreign Specific Field')

    reference = fields.Char(string='REFERENCE', required=True, copy=False, readonly=True, default=lambda self: _("New"))
    
    # New field to hold the RFQ reference related to this purchase order
    # rfq_related_references = fields.Char(string="reference")
    rfq_related_reference = fields.Char(string='RFQ Related Reference', related='rfq_request_id.reference', readonly=True)  # Adjust the related field accordingly

    @api.model
    def create(self, vals):
        """ Override create method to set unique reference for purchase order. """
        if vals.get('reference', _('New')) == _('New'):
            vals['reference'] = self.env['ir.sequence'].next_by_code('purchase.order') or _('New')
        return super(PurchaseOrder, self).create(vals)

    @api.model
    def create(self, vals):
        # Set the purchase type based on context
        if self.env.context.get('purchase_type') == 'foreign':
            vals['purchase_type'] = 'foreign'
        else:
            vals['purchase_type'] = 'local'  # Default to local if not specified

        # Create the purchase order
        order = super(PurchaseOrder, self).create(vals)

        # Generate the sequence based on purchase type
        if order.purchase_type == 'local':
            order.name = self.env['ir.sequence'].next_by_code('local.purchase.order.sequence') or '/'
        elif order.purchase_type == 'foreign':
            order.name = self.env['ir.sequence'].next_by_code('foreign.purchase.order.sequence') or '/'

        return order

    def create_po_from_rfq(self, rfq_id):
        """Creates a Purchase Order from the given RFQ."""
        rfq = self.env['local.create.rfq'].browse(rfq_id)
        if not rfq:
            return

        po_vals = {
            'rfq_request_id': rfq.id,
            'purchase_type': rfq.purchase_type,
            'partner_id': rfq.vendor_id.id,  # Vendor from the RFQ
        }

        # Create the purchase order
        po = self.create(po_vals)

        # Copy RFQ lines to the PO lines
        for rfq_line in rfq.line_ids:
            po_line_vals = {
                'order_id': po.id,
                'product_id': rfq_line.product_id.id,
                'product_qty': rfq_line.quantity,
                'price_unit': rfq_line.price_unit,
                'vendor_id': rfq_line.vendor_id.id,
                'date_planned': fields.Datetime.now(),  # Or use a relevant date from RFQ
            }
            self.env['purchase.order.line'].create(po_line_vals)

        return po
