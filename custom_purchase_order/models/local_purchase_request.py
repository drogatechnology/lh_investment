from odoo import models, fields, api, _
from odoo.exceptions import ValidationError

class LocalPurchaseRequest(models.Model):
    _name = 'local.purchase.request'
    _description = 'Local Purchase Request'
    _rec_name = 'reference'

    rfq_ids = fields.One2many('local.create.rfq', 'purchase_request_id', string='RFQs')  # Link to related RFQs
    rfq_count = fields.Integer(string="", compute="_compute_rfq_count")
    reference = fields.Char(string='REFERENCE', required=True, copy=False, readonly=True, default=lambda self: _("New"))
    request_department = fields.Many2one('hr.department', string='Department', store=True, compute='_compute_request_department')
    requested_by = fields.Many2one('res.users', string='Requested By', default=lambda self: self.env.user)
    approved_by = fields.Many2one('res.users', string='Approved By')
    # purchase_type = fields.Char(string="Purchase Type")
    request_date = fields.Date(string='Request Date', default=fields.Date.today)
    line_ids = fields.One2many('local.purchase.request.line', 'request_id', string='Products')
    local_rfq_created = fields.Boolean(string="RFQ Created", default=False)
    purpose = fields.Char(string="Purpose")
    state = fields.Selection([
        ('draft', 'Draft'),
        ('submitted', 'Submitted'),
        ('approved', 'Approved'),
        ('done', 'Done'),
        ('cancelled', 'Cancelled'),
    ], default='draft', string='Status')
    
    PURCHASE_TYPE_SELECTION = [
        ('goods', 'Goods'),
        ('service', 'Service'),
    ]
    
    purchase_type = fields.Selection(
        selection=PURCHASE_TYPE_SELECTION,
        string="Purchase Type",
        required=True,
        default='goods',  # Set a default value if needed
    )

    
    show_create_rfq_button = fields.Boolean(compute="_compute_show_create_rfq_button", string="Show Create RFQ Button")

    @api.depends('state', 'rfq_ids')
    def _compute_show_create_rfq_button(self):
        """ Compute whether the Create RFQ button should be shown """
        for record in self:
            record.show_create_rfq_button = (record.state == 'approved')
    
    # Compute the count of related RFQs
    @api.depends('rfq_ids')
    def _compute_rfq_count(self):
        for record in self:
            record.rfq_count = len(record.rfq_ids)

    # Override the create function to generate a unique reference if not provided
    @api.model
    def create(self, vals):
        if vals.get('reference', _('New')) == _('New'):
            vals['reference'] = self.env['ir.sequence'].next_by_code('local.purchase.request') or _('New')
        return super(LocalPurchaseRequest, self).create(vals)

    def custom_create_function(self):
        self.ensure_one()

        # Create the RFQ record and copy fields
        rfq_values = {
            'request_date': self.request_date,
            'requested_by': self.requested_by.id,
            'approved_by': self.approved_by.id,
            'request_department' : self.request_department.id,
            'purchase_request_id': self.id,  # Link to the purchase request
    }

        rfq = self.env['local.create.rfq'].create(rfq_values)

        # Copy line items from the purchase request to the RFQ, including the UOM and quantity
        for line in self.line_ids:
            self.env['local.create.rfq.line'].create({
                'rfq_id': rfq.id,
                'product_id': line.product_id.id,
                'uom_id': line.uom_id.id,  # Copy the UOM from the purchase request line
                'quantity': line.quantity,  # Copy the quantity from the purchase request line
        })

        # Mark the purchase request as having an RFQ created
        self.local_rfq_created = True

    # Action to return the list of related RFQs
    def return_list(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': 'Related RFQs',
            'res_model': 'local.create.rfq',
            'view_mode': 'tree,form',
            'domain': [('purchase_request_id', '=', self.id)],  # Filter by related purchase request
            'target': 'current',
        }

    # Action to submit the request
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

    # Action to mark the request as done
    def action_done(self):
        self.ensure_one()
        self.write({'state': 'done'})

    # Action to cancel the request
    def action_cancel(self):
        self.ensure_one()
        self.write({'state': 'cancelled'})
        
    @api.depends('requested_by')
    def _compute_request_department(self):
        """ Automatically compute the department based on the 'requested_by' user """
        for record in self:
            if record.requested_by:
                # Get the first department of the related employee(s) linked to the user
                employee = record.requested_by.employee_ids[:1]
                record.request_department = employee.department_id if employee else False


class LocalPurchaseRequestLine(models.Model):
    _name = 'local.purchase.request.line'
    _description = 'Local Purchase Request Line'

    request_id = fields.Many2one('local.purchase.request', string='Request Reference', ondelete='cascade')
    product_id = fields.Many2one('product.product', string='Product', required=True)
    quantity = fields.Float(string='Quantity', required=True)
    uom_id = fields.Many2one('uom.uom', string='Unit of Measure', compute='_compute_uom_id', store=True, readonly=True)
    budgetary_position = fields.Many2one('budget.line', string="Budget Category")

    
    @api.depends('product_id')
    def _compute_uom_id(self):
        for rec in self:
            if rec.product_id:
                rec.uom_id = rec.product_id.uom_id
            else:
                rec.uom_id = False 
    
    # Constraint to ensure the quantity is positive
    @api.constrains('quantity')
    def _check_quantity(self):
        for line in self:
            if line.quantity <= 0:
                raise ValidationError(_("The quantity of the product must be greater than zero."))
            
    def unlink(self):
        for line in self:
            if line.request_id.state != 'draft':
                raise ValidationError(_("You can only delete lines when the PR is in draft state."))
        return super(LocalPurchaseRequestLine, self).unlink()