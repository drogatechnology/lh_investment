from odoo import models, fields, api, _
from odoo.exceptions import ValidationError


class WithoutRFQLocalPurchase(models.Model):
    _name = 'without.rfq.local.purchase'
    _description = 'Without RFQ Local Purchase'
    _inherit = ["mail.thread", "mail.activity.mixin", "analytic.mixin"]
    _rec_name = 'reference_wrfq'

    name = fields.Char(string='Direct purchase Name')
    reference_wrfq = fields.Char(string='REFERENCE', required=True, copy=False, readonly=True, default=lambda self: _("New"))
    request_department = fields.Many2one('hr.department', string='Department', compute='_compute_request_department', store=True)
    requested_by = fields.Many2one('res.users', string='Requested By', default=lambda self: self.env.user)
    approved_by = fields.Many2one('res.users', string='Approved By')
    request_date = fields.Date(string='Request Date', default=fields.Date.today)
    vendor_id = fields.Many2one('res.partner', string="Vendor")
    line_ids = fields.One2many('without.rfq.local.purchase.line', 'request_id', string='Products')
    purpose = fields.Char(string="Purpose")
    order_id = fields.Many2one('purchase.order', string='Order Reference', ondelete='cascade')

    state = fields.Selection([
        ('draft', 'Draft'),
        ('submitted', 'Submitted'),
        ('approved', 'Verfied'),
        ('budget', 'Budget Approved'), 
        ('pmapproved', 'PM Approved'),        
        ('done', 'CEO Approved'),
        ('cancelled', 'Cancelled'),
    ], default='draft', string='Status',tracking=True)
    

    purchase_type = fields.Selection(
        [('goods', 'Goods'), ('service', 'Service')],
        string="Purchase Type", required=True, default='goods',
    )

    withoutpo_ids = fields.One2many('purchase.order', 'without_rfq_request_ids', string='POs')
    show_purchase_order_button = fields.Boolean(compute="_compute_show_purchase_order_button", string="Show Purchase Order Button")
    show_create_po_button = fields.Boolean(string="Show Create PO Button", default=True)
    local_po_created = fields.Boolean(string="PO Created", default=False)
    count_withoutrfq_po = fields.Integer(string=".", compute='_compute_po_count')
    
    @api.depends('withoutpo_ids')
    def _compute_po_count(self):
        """ Compute the count of related POs. """
        for record in self:
            record.count_withoutrfq_po = len(record.withoutpo_ids)
    

    @api.model
    def create(self, vals):
        if vals.get('reference_wrfq', _('New')) == _('New'):
            vals['reference_wrfq'] = self.env['ir.sequence'].next_by_code('without.rfq.local.purchase') or _('New')
        return super(WithoutRFQLocalPurchase, self).create(vals)

    @api.depends('requested_by')
    def _compute_request_department(self):
        """ Auto-assign the department based on the user making the request. """
        for record in self:
            employee = self.env['hr.employee'].search([('user_id', '=', record.requested_by.id)], limit=1)
            record.request_department = employee.department_id.id if employee else False


    @api.depends('state')
    def _compute_show_purchase_order_button(self):
        """ Control the visibility of the 'Create PO' button based on the state. """
        for record in self:
            record.show_purchase_order_button = record.state == 'approved' and not record.local_po_created

    
    def action_submit(self):
        self.ensure_one()
        if not self.line_ids:
            raise ValidationError(_("Please add at least one product line before submitting the request."))
        self.write({'state': 'submitted'})
        
    

    # Action to approve the request
    def action_approve(self):
        self.ensure_one()
        if not self.approved_by:
            self.write({'approved_by': self.env.user.id})
        self.write({'state': 'approved'})
        
    # Action approve budget
    def action_budget_approve(self):
        self.ensure_one()
        self.write({'state': 'budget'})
        
     # Action approve budget
    def action_pm_approve(self):
        self.ensure_one()
        self.write({'state': 'pmapproved'})

    # Action to mark the request as done
    def action_done(self):
        self.ensure_one()
        self.write({'state': 'done'})

    # Action to cancel the request
    def action_cancel(self):
        self.ensure_one()
        self.write({'state': 'cancelled'})
        
     # Action to reset to draft
    def action_reset_to_draft(self):
        self.ensure_one()
        self.write({'state': 'draft'})

    def action_create_dpo(self):
        """ Create a Purchase Order for the vendor. """
        self.ensure_one()
        if not self.line_ids:
            raise ValidationError(_("You cannot create a PO without product lines."))

        # Prepare the purchase order values
        po_values = {
            'without_rfq_request_ids': self.id,  # Link to this model
            'partner_id': self.vendor_id.id,  # Vendor ID
            'date_order': fields.Date.today(),
            'purchase_type': 'direct',  # Explicitly setting the purchase type to 'direct'
            'order_line': [(0, 0, {
                'product_id': line.product_id.id,
                'product_qty': line.quantity,
                'price_unit': line.price_unit,
                'name': line.product_id.name or '',  # Product name
                'date_planned': fields.Date.today(),  # Planned date
            }) for line in self.line_ids],  # Lines from this request
            'without_rfq_reference': self.reference_wrfq,  # Reference link
        }

        # Create the purchase order
        po = self.env['purchase.order'].create(po_values)

        # Mark the request as PO created
        self.local_po_created = True
        self.order_id = po.id  # Link the created PO to the request




    def action_view_dpo(self):
        """ Opens the list of related Purchase Orders. """
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': _('Purchase Orders'),
            'res_model': 'purchase.order',
            'view_mode': 'tree,form',
            'domain': [('without_rfq_request_ids', '=', self.id)],
            'target': 'current',
        }
    
    def action_cancel(self):
        """ Mark the request as cancelled. """
        self.ensure_one()
        self.write({'state': 'cancelled'})

    def action_reset_draft(self):
        """ Reset the request back to draft state. """
        self.ensure_one()
        self.write({'state': 'draft'})
        self.local_po_created = False


class WithoutRFQLocalPurchaseLine(models.Model):
    _name = 'without.rfq.local.purchase.line'
    _description = 'Without RFQ Local Purchase Line'

    request_id = fields.Many2one('without.rfq.local.purchase', string="Request Reference", required=True)
    product_id = fields.Many2one('product.product', string="Product", required=True)
    uom_id = fields.Many2one('uom.uom', string='Unit of Measure', related='product_id.uom_id', readonly=True, store=True)
    quantity = fields.Float(string="Quantity", required=True)
    price_unit = fields.Float(string="Unit Price", required=True)
    price_total = fields.Float(string='Total Price', compute='_compute_price_total', store=True)
    state = fields.Selection(related='request_id.state', string="Status", store=True)

    @api.depends('quantity', 'price_unit')
    def _compute_price_total(self):
        """ Compute the total price of the line. """
        for line in self:
            line.price_total = line.quantity * line.price_unit
