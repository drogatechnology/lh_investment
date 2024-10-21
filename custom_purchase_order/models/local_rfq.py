from odoo import models, fields, api, _
from odoo.exceptions import ValidationError


class LocalCreateRFQ(models.Model):
    _name = 'local.create.rfq'
    _description = 'Local RFQ'
    _rec_name = 'reference'

    name = fields.Char(string='RFQ Name')
    purchase_request_id = fields.Many2one('local.purchase.request', string="Purchase Request", readonly=True)
    reference = fields.Char(string='REFERENCE', required=True, copy=False, readonly=True, default=lambda self: _("New"))
    request_date = fields.Date(string="Request Date")
    request_department = fields.Many2one('hr.department', string='Department')
    requested_by = fields.Many2one('res.users', string="Requested By")
    approved_by = fields.Many2one('res.users', string="Approved By")
    line_ids = fields.One2many('local.create.rfq.line', 'rfq_id', string="Products")
    remark = fields.Char(string="Remark")
    technical_remark = fields.Char(string="Technical Remark")
   
    company_id= fields.Many2one('res.company', string="Company")

    name = fields.Char(string="RFQ Name")
    rfq_date = fields.Date(string='RFQ Date', default=fields.Date.context_today, required=True)
    vendor_id = fields.Many2one('res.partner', string='Vendor')
    total_amount = fields.Float(string='Total Amount', compute='_compute_total_amount', store=True)
    
    
    po_ids = fields.One2many('purchase.order', 'rfq_request_id', string='POs')
    local_po_created = fields.Boolean(string="PO Created", default=False)
    po_count = fields.Integer(string=".", compute='_compute_po_count')
    show_create_po_button = fields.Boolean(string="Show Create PO Button", default=True)

    state = fields.Selection([
        ('draft', 'Draft'),
        ('confirmed', 'Confirmed'),
        ('sent', 'Approved'),
        ('cancelled', 'Cancelled'),
    ], string='State', default='draft')

    po_ids = fields.One2many('purchase.order', 'rfq_request_id', string='POs')
    local_po_created = fields.Boolean(string="PO Created", default=False)
    po_count = fields.Integer(string="PO Count", compute='_compute_po_count')

    @api.depends('line_ids.price_total')
    def _compute_total_amount(self):
        """ Compute the total amount of the RFQ. """
        for rfq in self:
            rfq.total_amount = sum(line.price_total for line in rfq.line_ids)

    @api.depends('po_ids')
    def _compute_po_count(self):
        """ Compute the count of related POs. """
        for record in self:
            record.po_count = len(record.po_ids)

    @api.model
    def create(self, vals):
        if vals.get('reference', _('New')) == _('New'):
            vals['reference'] = self.env['ir.sequence'].next_by_code('local.create.rfq') or _('New')
        return super(LocalCreateRFQ, self).create(vals)

    def action_confirm(self):
        self.ensure_one()
        if not self.line_ids:
            raise ValidationError(_("You cannot confirm an RFQ without product lines."))
        self.write({'state': 'confirmed'})

    def action_send(self):
        self.ensure_one()
        if self.state != 'confirmed':
            raise ValidationError(_("Only confirmed RFQs can be sent."))
        self.write({'state': 'sent'})

    def action_cancel(self):
        self.ensure_one()
        self.write({'state': 'cancelled'})

    def action_reset_to_draft(self):
        """ Resets the RFQ back to draft state and resets the winners. """
        self.ensure_one()
        self.write({'state': 'draft'})
        self.line_ids.write({'winner': False})
        
    def action_create_po(self):
        """ Create Purchase Orders from the RFQ for each vendor with winning lines. """
        self.ensure_one()

        # Filter lines with 'win' status
        winning_lines = self.line_ids.filtered(lambda line: line.winner == 'win')

        if not winning_lines:
            raise ValidationError(_("You cannot create a PO without any winning lines."))

        # Group winning lines by vendor
        vendors = winning_lines.mapped('vendor_id')

        # Create a PO for each vendor with all their respective winning lines
        for vendor in vendors:
            # Filter the winning lines for the current vendor
            vendor_lines = winning_lines.filtered(lambda line: line.vendor_id == vendor)

            # Prepare the values for the Purchase Order with all lines for this vendor
            po_values = {
                'rfq_request_id': self.id,  # Link the PO to the RFQ
                'partner_id': vendor.id,  # Set the vendor from the winning lines
                'date_order': fields.Date.today(),  # Set the order date
                'order_line': [(0, 0, {
                    'product_id': line.product_id.id,
                    'product_qty': line.quantity,
                    'price_unit': line.price_unit,
                    'name': line.product_id.name or '',  # Add product description
                    'date_planned': fields.Date.today(),  # Set planned date
                }) for line in vendor_lines],  # Combine all the vendor's winning lines as order lines
                'rfq_reference': self.reference,  # Pass the RFQ reference to the PO
            }

            # Create the Purchase Order for the vendor (only one per vendor)
            self.env['purchase.order'].create(po_values)

        # Mark the RFQ as PO created
        self.local_po_created = True

        # Optionally hide the 'Create PO' button after creating the POs
        self.show_create_po_button = False

        return True

        
    
    

    def action_view_po(self):
        """ Opens the list of related Purchase Orders. """
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': _('Purchase Orders'),
            'res_model': 'purchase.order',
            'view_mode': 'tree,form',
            'domain': [('rfq_request_id', '=', self.id)],
            'target': 'current',
        }
        
        # Action to return the list of related po
    def return_list(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': 'Related PO',
            'res_model': 'purchase.order',
            'view_mode': 'tree,form',
            'domain': [('rfq_request_id', '=', self.id)],  # Filter by related purchase request
            'target': 'current',
        }


class LocalCreateRFQLine(models.Model):
    _name = 'local.create.rfq.line'
    _description = 'Local RFQ Line'

    rfq_id = fields.Many2one('local.create.rfq', string="RFQ Reference", required=True)
    vendor_id = fields.Many2one('res.partner', string="Vendor")
    product_id = fields.Many2one('product.product', string="Product", required=True, domain="[('id', 'in', available_product_ids)]")
    uom_id = fields.Many2one('uom.uom', string='Unit of Measure', related='product_id.uom_id', readonly=True, store=True)
    quantity = fields.Float(string="Quantity", required=True)
    price_unit = fields.Float(string="Unit Price")
    price_total = fields.Float(string='Total Price', compute='_compute_price_total', store=True)
    winner = fields.Selection([('win', 'Win'), ('lost', 'Lost')], string="Winner")
    
    available_product_ids = fields.Many2many(
        'product.product', 
        string='Available Products', 
        compute='_compute_available_product_ids', 
        store=False
    )

    @api.depends('rfq_id.purchase_request_id')
    def _compute_available_product_ids(self):
        """ Compute the available products from the related Purchase Request. """
        for line in self:
            if line.rfq_id.purchase_request_id:
                line.available_product_ids = line.rfq_id.purchase_request_id.line_ids.mapped('product_id')
            else:
                line.available_product_ids = self.env['product.product'].browse()

    @api.depends('quantity', 'price_unit')
    def _compute_price_total(self):
        """ Compute the total price of the line. """
        for line in self:
            line.price_total = line.quantity * line.price_unit

    def action_accept(self):
        """ Mark this line as the winner and other vendors as 'lost' for the same product. """
        self.ensure_one()

        # Mark this line as 'win'
        self.winner = 'win'

        # Mark all other lines with the same product but different vendors as 'lost'
        self.sudo().search([
            ('rfq_id', '=', self.rfq_id.id),
            ('product_id', '=', self.product_id.id),
            ('id', '!=', self.id)
        ]).write({'winner': 'lost'})

    def action_refuse(self):
        """ Mark this line as lost. """
        self.winner = 'lost'

    @api.constrains('winner')
    def _check_winner(self):
        """ Ensure that only one line is marked as 'Win' per product in the RFQ. """
        for line in self:
            if line.winner == 'win':
                win_count = self.env['local.create.rfq.line'].search_count([
                    ('rfq_id', '=', line.rfq_id.id),
                    ('product_id', '=', line.product_id.id),
                    ('winner', '=', 'win')
                ])
                if win_count > 1:
                    raise ValidationError(_("You cannot select more than one 'Win' for the same product in this RFQ."))
                
    def unlink(self):
        for line in self:
            if line.rfq_id.state != 'draft':
                raise ValidationError(_("You can only delete lines when the RFQ is in draft state."))
        return super(LocalCreateRFQLine, self).unlink()
    
    
    @api.onchange('product_id')
    def _onchange_product_id(self):
        """ Set the quantity automatically if the product already exists in the RFQ lines. """
        if self.product_id and self.rfq_id:
            # Get all the lines in the RFQ for this product
            existing_lines = self.rfq_id.line_ids.filtered(lambda line: line.product_id == self.product_id)

            # If the product already exists in another line, inherit its quantity
            if existing_lines:
                self.quantity = existing_lines[0].quantity
            else:
                # If no such product exists in the RFQ lines, fetch it from the related purchase request
                if self.rfq_id.purchase_request_id:
                    request_lines = self.rfq_id.purchase_request_id.line_ids.filtered(lambda rline: rline.product_id == self.product_id)
                    if request_lines:
                        self.quantity = request_lines[0].quantity
                    else:
                        self.quantity = 0.0



