from odoo import models, fields, api, _
from odoo.exceptions import ValidationError
from odoo.exceptions import UserError

class LocalPurchaseRequest(models.Model):
    _name = 'local.purchase.request'
    _description = 'Local Purchase Request'
    _inherit = ["mail.thread", "mail.activity.mixin", "analytic.mixin"]
    _rec_name = 'reference'

    name = fields.Char(string='PR Name')
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
    reason_for_cancel = fields.Char(string="Reason For Cancel")
    cost_center = fields.Many2one('account.analytic.account', string="Cost Center")
    state = fields.Selection([
        ('draft', 'Draft'),
        ('submitted', 'Submitted'),
        ('approved', 'Verfied'),
        ('budget', 'Budget Approved'), 
        ('pmapproved', 'PM Approved'),        
        ('done', 'CEO Approved'),
        ('cancelled', 'Cancelled'),
    ], default='draft', string='Status',tracking=True)
    
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
    
    
    
    # @api.onchange('store_requestion_id')
    # def _onchange_store_requestion_id(self):
    #     if self.store_requestion_id:
    #         self.purchase_type = self.store_requestion_id.purchase_type
    #     else:
    #         self.purchase_type = False
    
    
  
   



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
        
        if self.state != 'done':
            raise ValidationError(_("You Cannot Create a RFQ Which is Not Approved"))

        # Create the RFQ record and copy fields
        rfq_values = {
            'request_date': self.request_date,
            'requested_by': self.requested_by.id,
            'approved_by': self.approved_by.id,
            'request_department' : self.request_department.id,
            'purchase_type' : self.purchase_type,
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
        
        # Check if there are any related Purchase Orders
        rfq_count = self.env['local.create.rfq'].search_count([('purchase_request_id', '=', self.id)])

        if rfq_count == 0:
            # Raise an error if no related Purchase Orders are found
            raise UserError(_("There are no RFQ created yet."))
        return {
            'type': 'ir.actions.act_window',
            'name': 'Related RFQs',
            'res_model': 'local.create.rfq',
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

    # Actions for state transitions
    def action_submit(self):
        self.ensure_one()
        if not self.line_ids:
            raise ValidationError(_("Please add at least one product line before submitting the request."))
        self.write({'state': 'submitted'})
        self.schedule_activity_for_group(
            'custom_purchase_order.group_local_purchase_request_pm_manager',
            summary="Local Purchase Request Submitted",
            note="A local purchase request has been submitted and requires review."
        )

    def action_approve(self):
        self.ensure_one()
        if not self.approved_by:
            self.write({'approved_by': self.env.user.id})
        self.write({'state': 'approved'})
        self.schedule_activity_for_group(
            'custom_purchase_order.group_local_purchase_request_finance_manager',
            summary="Request Verified",
            note="The request has been verified and needs budget approval."
        )

    def action_budget_approve(self):
        self.ensure_one()
        self.write({'state': 'budget'})
        self.schedule_activity_for_group(
            'custom_purchase_order.group_local_purchase_request_ceo',
            summary="Budget Approved",
            note="The budget has been approved and is awaiting final approval from the CEO."
        )

    def action_pm_approve(self):
        self.ensure_one()
        self.write({'state': 'pmapproved'})
        self.schedule_activity_for_group(
            'custom_purchase_order.group_local_purchase_request_user',
            summary="PM Approval Completed",
            note="The PM has approved the request. The process can now proceed."
        )
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': 'PM Approval',
                'message': f"Request approved: {self.name or 'No Reference Provided'}",
                'type': 'info',
                'sticky': False,
            }
        }

    def action_done(self):
        self.ensure_one()
        self.write({'state': 'done'})
        self.schedule_activity_for_group(
            'custom_purchase_order.group_local_purchase_request_user',
            summary="Request Finalized",
            note="The request has been finalized and approved by the CEO."
        )
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': 'Completion',
                'message': f"Request completed: {self.name or 'No Reference Provided'}",
                'type': 'info',
                'sticky': False,
            }
        }

    def action_cancel(self):
        self.write({'state': 'cancel'})

    def action_reset_to_draft(self):
        self.write({'state': 'draft'})
        
    @api.depends('requested_by')
    def _compute_request_department(self):
        """ Automatically compute the department based on the 'requested_by' user """
        for record in self:
            if record.requested_by:
                # Get the first department of the related employee(s) linked to the user
                employee = record.requested_by.employee_ids[:1]
                record.request_department = employee.department_id.id if employee else False



class LocalPurchaseRequestLine(models.Model):
    _name = 'local.purchase.request.line'
    _description = 'Local Purchase Request Line'

    request_id = fields.Many2one('local.purchase.request', string='Request Reference', ondelete='cascade')
    product_id = fields.Many2one('product.product', string='Product', required=True)
    quantity = fields.Float(string='Quantity', required=True)
    uom_id = fields.Many2one('uom.uom', string='Unit of Measure', compute='_compute_uom_id', store=True, readonly=True)
    budgetary_position = fields.Many2one('account.budget.post', string="Budget Category")
    
    available_product_ids = fields.Many2many(
        'product.product', 
        string='Available Products', 
        compute='_compute_available_product_ids', 
        store=False
    )

    
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
    
    
    
    # @api.depends('request_id.store_requestion_id')
    # def _compute_available_product_ids(self):
    #     """ Compute the available products from the related Purchase Request. """
    #     for line in self:
    #         if line.request_id.store_requestion_id:
    #             line.available_product_ids = line.request_id.store_requestion_id.line_ids.mapped('product_id')
    #         else:
    #             line.available_product_ids = self.env['product.product'].browse()










# from odoo import models, fields, api, _
# from odoo.exceptions import ValidationError
# from odoo.exceptions import UserError

# class LocalPurchaseRequest(models.Model):
#     _name = 'local.purchase.request'
#     _description = 'Local Purchase Request'
#     _inherit = ["mail.thread", "mail.activity.mixin", "analytic.mixin"]
#     _rec_name = 'reference'

#     rfq_ids = fields.One2many('local.create.rfq', 'purchase_request_id', string='RFQs')  # Link to related RFQs
#     rfq_count = fields.Integer(string="", compute="_compute_rfq_count")
#     reference = fields.Char(string='REFERENCE', required=True, copy=False, readonly=True, default=lambda self: _("New"))
#     request_department = fields.Many2one('hr.department', string='Department', store=True, compute='_compute_request_department')
#     requested_by = fields.Many2one('res.users', string='Requested By', default=lambda self: self.env.user)
#     approved_by = fields.Many2one('res.users', string='Approved By')
#     # purchase_type = fields.Char(string="Purchase Type")
#     request_date = fields.Date(string='Request Date', default=fields.Date.today)
#     line_ids = fields.One2many('local.purchase.request.line', 'request_id', string='Products')
#     local_rfq_created = fields.Boolean(string="RFQ Created", default=False)
#     purpose = fields.Char(string="Purpose")
#     reason_for_cancel = fields.Char(string="Reason For Cancel")
#     cost_center = fields.Many2one('account.analytic.account', string="Cost Center")
#     state = fields.Selection([
#         ('draft', 'Draft'),
#         ('submitted', 'Submitted'),
#         ('approved', 'Verfied'),
#         ('budget', 'Budget Approved'), 
#         ('pmapproved', 'PM Approved'),        
#         ('done', 'CEO Approved'),
#         ('cancelled', 'Cancelled'),
#     ], default='draft', string='Status')
    
#     PURCHASE_TYPE_SELECTION = [
#         ('goods', 'Goods'),
#         ('service', 'Service'),
#     ]
    
#     purchase_type = fields.Selection(
#         selection=PURCHASE_TYPE_SELECTION,
#         string="Purchase Type",
#         required=True,
#         default='goods',  # Set a default value if needed
#     )

    
#     show_create_rfq_button = fields.Boolean(compute="_compute_show_create_rfq_button", string="Show Create RFQ Button")
    
    
    
#     show_user_button = fields.Boolean(compute="_compute_button_visibility")
#     show_manager_button = fields.Boolean(compute="_compute_button_visibility")
#     show_ceo_button = fields.Boolean(compute="_compute_button_visibility")

#     @api.depends_context('uid')
#     def _compute_button_visibility(self):
#         user = self.env.user
#         for record in self:
#             record.show_user_button = user.show_user_button
#             record.show_manager_button = user.show_manager_button
#             record.show_ceo_button = user.show_ceo_button
    
    

#     @api.depends('state', 'rfq_ids')
#     def _compute_show_create_rfq_button(self):
#         """ Compute whether the Create RFQ button should be shown """
#         for record in self:
#             record.show_create_rfq_button = (record.state == 'approved')
    
#     # Compute the count of related RFQs
#     @api.depends('rfq_ids')
#     def _compute_rfq_count(self):
#         for record in self:
#             record.rfq_count = len(record.rfq_ids)

#     # Override the create function to generate a unique reference if not provided
#     @api.model
#     def create(self, vals):
#         if vals.get('reference', _('New')) == _('New'):
#             vals['reference'] = self.env['ir.sequence'].next_by_code('local.purchase.request') or _('New')
#         return super(LocalPurchaseRequest, self).create(vals)

#     def custom_create_function(self):
#         self.ensure_one()
        
#         if self.state != 'done':
#             raise ValidationError(_("You Cannot Create a RFQ Which is Not Approved"))

#         # Create the RFQ record and copy fields
#         rfq_values = {
#             'request_date': self.request_date,
#             'requested_by': self.requested_by.id,
#             'approved_by': self.approved_by.id,
#             'request_department' : self.request_department.id,
#             'purchase_type' : self.purchase_type,
#             'purchase_request_id': self.id,  # Link to the purchase request
#     }

#         rfq = self.env['local.create.rfq'].create(rfq_values)

#         # Copy line items from the purchase request to the RFQ, including the UOM and quantity
#         for line in self.line_ids:
#             self.env['local.create.rfq.line'].create({
#                 'rfq_id': rfq.id,
#                 'product_id': line.product_id.id,
#                 'uom_id': line.uom_id.id,  # Copy the UOM from the purchase request line
#                 'quantity': line.quantity,  # Copy the quantity from the purchase request line
#         })

#         # Mark the purchase request as having an RFQ created
#         self.local_rfq_created = True

#     # Action to return the list of related RFQs
#     def return_list(self):
#         self.ensure_one()
        
#         # Check if there are any related Purchase Orders
#         rfq_count = self.env['local.create.rfq'].search_count([('purchase_request_id', '=', self.id)])

#         if rfq_count == 0:
#             # Raise an error if no related Purchase Orders are found
#             raise UserError(_("There are no RFQ created yet."))
#         return {
#             'type': 'ir.actions.act_window',
#             'name': 'Related RFQs',
#             'res_model': 'local.create.rfq',
#             'view_mode': 'tree,form',
#             'domain': [('purchase_request_id', '=', self.id)],  # Filter by related purchase request
#             'target': 'current',
#         }

#     # Action to submit the request
#     def action_submit(self):
#         self.ensure_one()
#         if not self.line_ids:
#             raise ValidationError(_("Please add at least one product line before submitting the request."))
#         self.write({'state': 'submitted'})
        
    

#     # Action to approve the request
#     def action_approve(self):
#         self.ensure_one()
#         if not self.approved_by:
#             self.write({'approved_by': self.env.user.id})
#         self.write({'state': 'approved'})
        
#     # Action approve budget
#     def action_budget_approve(self):
#         self.ensure_one()
#         self.write({'state': 'budget'})
        
#      # Action approve budget
#     def action_pm_approve(self):
#         self.ensure_one()
#         self.write({'state': 'pmapproved'})

#     # Action to mark the request as done
#     def action_done(self):
#         self.ensure_one()
#         self.write({'state': 'done'})

#     # Action to cancel the request
#     def action_cancel(self):
#         self.ensure_one()
#         self.write({'state': 'cancelled'})
        
#      # Action to reset to draft
#     def action_reset_to_draft(self):
#         self.ensure_one()
#         self.write({'state': 'draft'})
        
#     @api.depends('requested_by')
#     def _compute_request_department(self):
#         """ Automatically compute the department based on the 'requested_by' user """
#         for record in self:
#             if record.requested_by:
#                 # Get the first department of the related employee(s) linked to the user
#                 employee = record.requested_by.employee_ids[:1]
#                 record.request_department = employee.department_id.id if employee else False



# class LocalPurchaseRequestLine(models.Model):
#     _name = 'local.purchase.request.line'
#     _description = 'Local Purchase Request Line'

#     request_id = fields.Many2one('local.purchase.request', string='Request Reference', ondelete='cascade')
#     product_id = fields.Many2one('product.product', string='Product', required=True)
#     quantity = fields.Float(string='Quantity', required=True)
#     uom_id = fields.Many2one('uom.uom', string='Unit of Measure', compute='_compute_uom_id', store=True, readonly=True)
#     budgetary_position = fields.Many2one('account.budget.post', string="Budget Category")

    
#     @api.depends('product_id')
#     def _compute_uom_id(self):
#         for rec in self:
#             if rec.product_id:
#                 rec.uom_id = rec.product_id.uom_id
#             else:
#                 rec.uom_id = False 
    
#     # Constraint to ensure the quantity is positive
#     @api.constrains('quantity')
#     def _check_quantity(self):
#         for line in self:
#             if line.quantity <= 0:
#                 raise ValidationError(_("The quantity of the product must be greater than zero."))
            
#     def unlink(self):
#         for line in self:
#             if line.request_id.state != 'draft':
#                 raise ValidationError(_("You can only delete lines when the PR is in draft state."))
#         return super(LocalPurchaseRequestLine, self).unlink()