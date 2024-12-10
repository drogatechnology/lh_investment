from odoo import models, fields, api, _
from odoo.exceptions import ValidationError

class ForeignPurchaseRequest(models.Model):
    _name = 'foreign.purchase.request'
    _description = 'Foreign Purchase Request'
    _inherit = ["mail.thread", "mail.activity.mixin", "analytic.mixin"]
    _rec_name = 'reference'

    rfq_ids_foreign = fields.One2many('foreign.create.rfq', 'purchase_request_id', string='RFQs')  # Link to related RFQs
    rfq_count = fields.Integer(string="", compute="_compute_rfq_count")
    reference = fields.Char(string='REFERENCE', required=True, copy=False, readonly=True, default=lambda self: _("New"))
    request_department = fields.Many2one('hr.department', string='Department', store=True, compute='_compute_request_department')
    requested_by = fields.Many2one('res.users', string='Requested By', default=lambda self: self.env.user)
    approved_by = fields.Many2one('res.users', string='Approved By')
    cost_center = fields.Many2one('account.analtyic.account',string='cost center')
    # purchase_type = fields.Char(string="Purchase Type")
    request_date = fields.Date(string='Request Date', default=fields.Date.today)
    line_ids = fields.One2many('foreign.purchase.request.line', 'request_id', string='Products')
    foreign_rfq_created = fields.Boolean(string="RFQ Created", default=False)
    purpose = fields.Char(string="Purpose")
    
    cost_center = fields.Many2one(
        'account.analytic.account',
        string="Cost Center",
        help="Select the cost center associated with this RFQ"
    )

    state = fields.Selection([
        ('draft', 'Draft'),
        ('submitted', 'Submitted'),
        ('approved', 'Verfied'),
        ('budget', 'Budget Approved'), 
        ('pmapproved', 'PM Approved'),        
        ('done', 'CEO Approved'),
        ('cancelled', 'Cancelled'),
    ], default='draft', string='Status',tracking=True)
    
  

    
    show_create_rfq_button = fields.Boolean(compute="_compute_show_create_rfq_button", string="Show Create RFQ Button")

    @api.depends('state', 'rfq_ids_foreign')
    def _compute_show_create_rfq_button(self):
        """ Compute whether the Create RFQ button should be shown """
        for record in self:
            record.show_create_rfq_button = (record.state == 'approved')
    
    # Compute the count of related RFQs
    @api.depends('rfq_ids_foreign')
    def _compute_rfq_count(self):
        for record in self:
            record.rfq_count = len(record.rfq_ids_foreign)

    # Override the create function to generate a unique reference if not provided
    @api.model
    def create(self, vals):
        if vals.get('reference', _('New')) == _('New'):
            vals['reference'] = self.env['ir.sequence'].next_by_code('foreign.purchase.request') or _('New')
        return super(ForeignPurchaseRequest, self).create(vals)

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

        rfq = self.env['foreign.create.rfq'].create(rfq_values)

        # Copy line items from the purchase request to the RFQ, including the UOM and quantity
        for line in self.line_ids:
            self.env['foreign.create.rfq.line'].create({
                'foreign_rfq_id': rfq.id,
                'product_id': line.product_id.id,
                'uom_id': line.uom_id.id,  # Copy the UOM from the purchase request line
                'quantity': line.quantity,  # Copy the quantity from the purchase request line
        })

        # Mark the purchase request as having an RFQ created
        self.foreign_rfq_created = True

    # Action to return the list of related RFQs
    def return_list(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': 'Related RFQs',
            'res_model': 'foreign.create.rfq',
            'view_mode': 'tree,form',
            'domain': [('purchase_request_id', '=', self.id)],  # Filter by related purchase request
            'target': 'current',
        }

     # Reusable method to schedule activity
    def schedule_activity_for_group(self, group_xml_id, summary, note):
        """Schedule an activity for all users in the specified group."""
        group = self.env.ref(group_xml_id)
        for user in group.users:
            self.activity_schedule(
                'mail.mail_activity_data_todo',
                user_id=user.id,
                summary=summary,
                note=note,
            )
    
    
    
    # Action to submit the request
    def action_submit(self):
        self.ensure_one()
        if not self.line_ids:
            raise ValidationError(_("Please add at least one product line before submitting the request."))
        self.write({'state': 'submitted'})
        self.schedule_activity_for_group(
            'custom_purchase_order.group_foreign_purchase_request_pm_manager',
            summary="Foreign Purchase Request Submitted",
            note="A Foreign purchase request has been submitted and requires review."
        )
        
    

    # Action to approve the request
    def action_approve(self):
        self.ensure_one()
        if not self.approved_by:
            self.write({'approved_by': self.env.user.id})
        self.write({'state': 'approved'})
        self.schedule_activity_for_group(
            'custom_purchase_order.group_foreign_purchase_request_finance_manager',
            summary="Request Verified",
            note="The request has been verified and needs budget approval."
        )
        
    # Action approve budget
    def action_budget_approve(self):
        self.ensure_one()
        self.write({'state': 'budget'})
        self.schedule_activity_for_group(
            'custom_purchase_order.group_foreign_purchase_request_ceo',
            summary="Budget Approved",
            note="The budget has been approved and is awaiting final approval from the CEO."
        )
        
     # Action approve budget
    def action_pm_approve(self):
        self.ensure_one()
        self.write({'state': 'pmapproved'})
        self.schedule_activity_for_group(
            'custom_purchase_order.group_local_purchase_request_user',
            summary="PM Approval Completed",
            note="The PM has approved the request. The process can now proceed."
        )

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
        
    @api.depends('requested_by')
    def _compute_request_department(self):
        """ Automatically compute the department based on the 'requested_by' user """
        for record in self:
            if record.requested_by:
                # Get the first department of the related employee(s) linked to the user
                employee = record.requested_by.employee_ids[:1]
                record.request_department = employee.department_id.id if employee else False



class ForeignPurchaseRequestLine(models.Model):
    _name = 'foreign.purchase.request.line'
    _description = 'Foreign Purchase Request Line'

    request_id = fields.Many2one('foreign.purchase.request', string='Request Reference', ondelete='cascade')
    product_id = fields.Many2one('product.product', string='Product', required=True)
    quantity = fields.Float(string='Quantity', required=True)
    uom_id = fields.Many2one('uom.uom', string='Unit of Measure', compute='_compute_uom_id', store=True, readonly=True)
    budgetary_position = fields.Many2one('account.budget.post', string="Budget Category")

    
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
        return super(ForeignPurchaseRequestLine, self).unlink()