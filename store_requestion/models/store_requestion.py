from odoo import models, fields, api, _
from odoo.exceptions import ValidationError
from odoo.exceptions import UserError



class StoreRequestionInherit(models.Model):
    _inherit = 'local.purchase.request'
    
    store_requestion_id = fields.Many2one('store.requestion.request', string="Store Request", readonly=True)
    
class StoreRequestionInheritSiv(models.Model):
    _inherit = 'stock.picking'
           
    store_isue_voucher_id = fields.Many2one('store.requestion.request', string="Store Request", readonly=True)
    siv_reference = fields.Char(related='store_isue_voucher_id.name', string="SIV Reference", readonly=True, store=True)

class StoreRequestion(models.Model):
    _name = 'store.requestion.request'
    _description = 'Store Requestion'
    _inherit = ["mail.thread", "mail.activity.mixin", "analytic.mixin"]
    _rec_name = 'reference' 

    
    name = fields.Char(string='Name')
    pr_ids = fields.One2many('local.purchase.request', 'store_requestion_id', string='PRS')  # Link to related PRs
    siv_ids = fields.One2many('stock.picking', 'store_isue_voucher_id', string='SIVS')  # Link to related PRs
    pr_count = fields.Integer(string="", compute="_compute_pr_count")
    siv_count = fields.Integer(string="", compute="_compute_siv_count")
    reference = fields.Char(string='REFERENCE', required=True, copy=False, readonly=True, default=lambda self: _("New"))
    request_department = fields.Many2one('hr.department', string='Department', store=True, compute='_compute_request_department')
    requested_by = fields.Many2one('res.users', string="Requested By" , required=True)
    approved_by = fields.Many2one('res.users', string="Approved By")
    request_date = fields.Date(string='Request Date', default=fields.Date.today)
    line_ids = fields.One2many('store.requestion.request.line', 'store_request_line_id', string='Products')
    pr_created = fields.Boolean(string="PR Created", default=False)
    siv_created = fields.Boolean(string="SIV Created", default=False)
    purpose = fields.Char(string="Purpose")
    reason_for_cancel = fields.Char(string="Reason For Cancel")
    # cost_center = fields.Many2one('account.analytic.account', string="Cost Center")
    state = fields.Selection([
        ('draft', 'Draft'),
        ('dmapproved', 'DM Approved'),
        ('smapproved', 'SM Approved'),
        ('storekeeper', 'Store Kepeer'), 
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
    
    source_location_id = fields.Many2one(
        'stock.location', 
        string="Source Location", 
        default=lambda self: self.env['stock.location'].search([('name', '=', 'Physical Locations')], limit=1).id
    )
    destination_location_id = fields.Many2one(
        'stock.location', 
        string="Destination Location", 
        default=lambda self: self.env['stock.location'].search([('name', '=', 'Virtual Locations')], limit=1).id
    )
    
    stock_picking_id = fields.Many2one(
        'stock.picking.type', 
        string="Operation Type", 
        default=lambda self: self.env['stock.picking.type'].search([('name', '=', 'Internal Transfers')], limit=1).id)
    
    
    @api.model
    def create(self, vals):
        if vals.get('reference', _('New')) == _('New'):
            vals['reference'] = self.env['ir.sequence'].next_by_code('store.requestion.request') or _('New')
        return super(StoreRequestion, self).create(vals)
    
    
    def action_submit(self):
        self.ensure_one()
        if not self.line_ids:
            raise ValidationError(_("Please add at least one product line before submitting the request."))
        self.write({'state': 'dmapproved'})
        
    

    # Action to approve the request
    def action_approve(self):
        self.ensure_one()
        if not self.approved_by:
            self.write({'approved_by': self.env.user.id})
        self.write({'state': 'smapproved'})
        
    
        
     # Action approve budget
    def action_pm_approve(self):
        self.ensure_one()

        # Update the state to 'pmapproved'
        self.write({'state': 'storekeeper'})
        
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

    
    show_create_pr_button = fields.Boolean(compute="_compute_show_create_pr_button", string="Show Create PR Button")
    show_create_siv_button = fields.Boolean(compute="_compute_show_create_siv_button", string="Show Create SIV Button")
    
    
    
    
    

    @api.depends('state', 'pr_ids')
    def _compute_show_create_pr_button(self):
        """ Compute whether the Create PR button should be shown """
        for record in self:
            record.show_create_pr_button = (record.state == 'approved')
            
    @api.depends('state', 'siv_ids')
    def _compute_show_create_siv_button(self):
        """ Compute whether the Create PR button should be shown """
        for record in self:
            record.show_create_siv_button = (record.state == 'approved')
    
    # Compute the count of related PRs
    @api.depends('pr_ids')
    def _compute_pr_count(self):
        for record in self:
            record.pr_count = len(record.pr_ids)
            
     # Compute the count of related SIVs
    @api.depends('siv_ids')
    def _compute_siv_count(self):
        for record in self:
            record.siv_count = len(record.siv_ids)

    # Override the create function to generate a unique reference if not provided
   

    def custom_create_function(self):
        self.ensure_one()
        
        if self.state != 'storekeeper':
            raise ValidationError(_("You Cannot Create a PR Which is Not Approved"))

        # Create the PR record and copy fields
        pr_values = {
            'request_date': self.request_date,
            'requested_by': self.requested_by.id,
            'approved_by': self.approved_by.id,
            'request_department' : self.request_department.id,
            'purchase_type' : self.purchase_type,
            'store_requestion_id': self.id,  # Link to the purchase request
    }

        pr = self.env['local.purchase.request'].create(pr_values)

        # Copy line items from the purchase request to the PR, including the UOM and quantity
        for line in self.line_ids:
            self.env['local.purchase.request.line'].create({
                'request_id': pr.id,
                'product_id': line.product_id.id,
                'uom_id': line.uom_id.id,  # Copy the UOM from the purchase request line
                'quantity': line.quantity,  # Copy the quantity from the purchase request line
        })

        # Mark the purchase request as having an PR created
        self.pr_created = True

    # Action to return the list of related PRs
    def return_list(self):
        self.ensure_one()
        
        # Check if there are any related Purchase Orders
        pr_count = self.env['local.purchase.request'].search_count([('store_requestion_id', '=', self.id)])

        if pr_count == 0:
            # Raise an error if no related Purchase Orders are found
            raise UserError(_("There are no PR created yet."))
        return {
            'type': 'ir.actions.act_window',
            'name': 'Related PRs',
            'res_model': 'local.purchase.request',
            'view_mode': 'tree,form',
            'domain': [('store_requestion_id', '=', self.id)],  # Filter by related purchase request
            'target': 'current',
        }
        
        
        
        
    def action_create_siv(self):
        """
        Create an SIV (Stock Issue Voucher) from the store requestion request.
        """
        self.ensure_one()

        if self.state != 'storekeeper':
            raise ValidationError(_("You cannot create an SIV for a request that is not done."))

        # Prepare the SIV (Stock Picking) record values
        siv_values = {
            'origin': self.reference,
            'location_id': self.source_location_id.id,  # Source location
            'location_dest_id': self.destination_location_id.id,  # Destination location
            'picking_type_id': self.env.ref('stock.picking_type_internal').id,  # Internal transfer picking type
            'store_isue_voucher_id': self.id,  # Link to the store requestion request
        }

        siv = self.env['stock.picking'].create(siv_values)

        # Copy request lines to stock moves in the new SIV
        for line in self.line_ids:
            self.env['stock.move'].create({
                'picking_id': siv.id,
                'product_id': line.product_id.id,
                'product_uom_qty': line.quantity,  # Quantity requested
                'product_uom': line.uom_id.id,  # UoM for the product
                'location_id': self.source_location_id.id,  # Source location
                'location_dest_id': self.destination_location_id.id,  # Destination location
                'name': line.product_id.name or _("No Description"),  # Description of the move
            })

        # Mark the requestion as having an SIV created
        self.siv_created = True

    def action_view_created_siv(self):
        """
        View the SIVs (Stock Issue Vouchers) linked to this store requestion request.
        """
        self.ensure_one()

        # Check if there are any related SIVs
        siv_count = self.env['stock.picking'].search_count([('store_isue_voucher_id', '=', self.id)])

        if siv_count == 0:
            raise UserError(_("There are no SIVs created yet."))

        return {
            'type': 'ir.actions.act_window',
            'name': 'Related SIVs',
            'res_model': 'stock.picking',
            'view_mode': 'tree,form',
            'domain': [('store_isue_voucher_id', '=', self.id)],  # Filter by related requestion
            'target': 'current',
        }




class StoreRequestionLine(models.Model):
    _name = 'store.requestion.request.line'
    _description = 'Store Request Line'

    store_request_line_id = fields.Many2one('store.requestion.request', string='Request Reference', ondelete='cascade')
    state = fields.Selection(related='store_request_line_id.state', string='Request State', store=True, readonly=True)
    product_id = fields.Many2one('product.product', string='Product', required=True)
    quantity = fields.Float(string='Demand', required=True,)
    uom_id = fields.Many2one('uom.uom', string='Unit of Measure', compute='_compute_uom_id', store=True, readonly=True)
    budgetary_position = fields.Many2one('account.budget.post', string="Budget Category")   
    product_availability = fields.Float(string="Stock Balance", compute='_compute_product_availability', readonly=True)
    
    
    @api.depends('product_id', 'store_request_line_id.source_location_id')
    def _compute_product_availability(self):
        for record in self:
            source_location = record.store_request_line_id.source_location_id
            if source_location and record.product_id:
                product_qty = self.env['stock.quant'].search([
                    ('product_id', '=', record.product_id.id),
                    ('location_id', '=', source_location.id)
                ]).quantity
                record.product_availability = product_qty
            else:
                record.product_availability = 0.0

    
    
    
    
    @api.depends('product_id')
    def _compute_uom_id(self):
        for rec in self:
            if rec.product_id:
                rec.uom_id = rec.product_id.uom_id
            else:
                rec.uom_id = False 
    @api.constrains('quantity')
    def _check_quantity(self):
        for line in self:
            if line.quantity < 0:
                raise ValidationError(_("The quantity of the product must be greater than zero."))
            
    def unlink(self):
        for line in self:
            if line.request_id.state != 'draft':
                raise ValidationError(_("You can only delete lines when the PR is in draft state."))
        return super(StoreRequestionLine, self).unlink()
    
   
                



