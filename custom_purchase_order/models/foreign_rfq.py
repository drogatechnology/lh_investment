import base64
import io
import xlsxwriter
from odoo import models, fields, api, _
from odoo.exceptions import ValidationError
from odoo.exceptions import UserError
from io import BytesIO

class ForeignCreateRFQ(models.Model):
    _name = 'foreign.create.rfq'
    _description = 'Foreign RFQ'
    _inherit = ["mail.thread", "mail.activity.mixin", "analytic.mixin"]
    _rec_name = 'foreign_reference'

    name = fields.Char(string='RFQ Name')
    purchase_request_id = fields.Many2one('foreign.purchase.request', string="Purchase Request", readonly=True)
    foreign_reference = fields.Char(string='REFERENCE', required=True, copy=False, readonly=True, default=lambda self: _("New"))
    request_date = fields.Date(string="Request Date")
    request_department = fields.Many2one('hr.department', string='Department')
    requested_by = fields.Many2one('res.users', string="Requested By")
    approved_by = fields.Many2one('res.users', string="Approved By")
    line_ids = fields.One2many('foreign.create.rfq.line', 'foreign_rfq_id', string="Products")
    remark = fields.Char(string="Remark")
    technical_remark = fields.Char(string="Technical Remark")
    company_id = fields.Many2one('res.company', string="Company")
    
    rfq_date = fields.Date(string='RFQ Date', default=fields.Date.context_today, required=True)
    vendor_id = fields.Many2one('res.partner', string='Vendor')
    total_amount = fields.Float(string='Total Amount', compute='_compute_total_amount', store=True)
    po_ids = fields.One2many('purchase.order', 'rfq_foreign_request_id', string='POs')
    foreign_po_created = fields.Boolean(string="PO Created", default=False)
    foreign_po_rfq_send_email = fields.Boolean(string="Send RFQ", default=False)
    foreign_po_count = fields.Integer(string="PO Count", compute='_compute_foreign_po_count')
    show_create_po_button = fields.Boolean(string="Show Create PO Button", default=True)
    order_id = fields.Many2one('purchase.order', string='Order Reference', ondelete='cascade')
    
    vendor_email = fields.Char(string="Vendor Email", compute="_compute_vendor_email", store=True)
    port_of_loading = fields.Char(string="Port of Loading")
    currency_request_ids = fields.One2many(
        'foreign.currency.request',  # The model we're linking to
        'foreign_rfq_reference',  # Corresponding Many2one field in foreign.currency.request
        string="Currency Requests"
    )
    
    request_type = fields.Selection(
        [('foreign', 'Foreign')],
        string="Request Type",
        default='foreign',
        readonly=True
    )
    
    state = fields.Selection([
        ('draft', 'Draft'),
        ('confirmed', 'Confirmed'),
        ('sent', 'Approved'),
        ('cancelled', 'Cancelled'),
    ], default='draft', string='Status',tracking=True)

    @api.depends('vendor_id')
    def _compute_vendor_email(self):
        for record in self:
            record.vendor_email = record.vendor_id.email if record.vendor_id else ''

   

    
    @api.depends('line_ids.price_total')
    def _compute_total_amount(self):
        for rfq in self:
            rfq.total_amount = sum(line.price_total for line in rfq.line_ids)

    @api.depends('po_ids')
    def _compute_foreign_po_count(self):
        for record in self:
            record.foreign_po_count = len(record.po_ids)

    @api.model
    def create(self, vals):
        if vals.get('foreign_reference', _('New')) == _('New'):
            vals['foreign_reference'] = self.env['ir.sequence'].next_by_code('foreign.create.rfq') or _('New')
        return super(ForeignCreateRFQ, self).create(vals)

    
    def action_confirm(self):
        self.ensure_one()
              
        # If all checks pass, update the state
        self.write({'state': 'confirmed'})
        
        return True



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
        
    def action_create_fpo(self):
        self.ensure_one()
        if not self.line_ids:
            raise ValidationError(_("You cannot create a PO without product lines."))

        po_values = {
            'rfq_foreign_request_id': self.id,
            'partner_id': self.vendor_id.id,
            'date_order': fields.Date.today(),
            'purchase_type': 'foreign',
            'order_line': [(0, 0, {
                'product_id': line.product_id.id,
                'product_qty': line.quantity,
                'price_unit': line.price_unit,
                'name': line.product_id.name,
                'date_planned': fields.Date.today(),
            }) for line in self.line_ids],
            'foreign_rfq_reference': self.foreign_reference,
        }

        po = self.env['purchase.order'].create(po_values)
        self.foreign_po_created = True
        self.order_id = po.id
        

    def action_view_fpo(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': _('Purchase Orders'),
            'res_model': 'purchase.order',
            'view_mode': 'tree,form',
            'domain': [('rfq_foreign_request_id', '=', self.id)],
            'target': 'current',
        }
        
   
    
    
    def _generate_excel_file(self):
        # Create an Excel file using xlsxwriter
        excel_data = BytesIO()  # Make sure this is a BytesIO object
        workbook = xlsxwriter.Workbook(excel_data)
        worksheet = workbook.add_worksheet()

        # Get company information (e.g., company name, email, etc.)
        company = self.company_id
        company_name = company.name if company else "N/A"
        company_email = company.email if company and company.email else "N/A"
        
        # Merge the first two rows for company name and the title
        worksheet.merge_range('A1:G1', company_name, workbook.add_format({'bold': True, 'align': 'center', 'valign': 'vcenter', 'font_size': 24}))
        worksheet.merge_range('A2:G2', 'Request For Quotation', workbook.add_format({'bold': True, 'align': 'center', 'valign': 'vcenter', 'font_size': 22}))
        
        # Add static RFQ details
        worksheet.write('A4', 'RFQ Reference:')
        worksheet.write('B4', f"{self.foreign_reference}")
        worksheet.write('A5', 'Supplier:')
        worksheet.write('B5', self.vendor_id.name)
        worksheet.write('A6', 'Currency:')
        worksheet.write('B6', 'USD')  # This can be dynamic if needed
        
        # Add a blank row for spacing
        worksheet.write('A7', '')

        # Add the header for the products table
        worksheet.write('A8', 'S.No')
        worksheet.write('B8', 'Product')
        worksheet.write('C8', 'Unit')
        worksheet.write('D8', 'Qty')
        worksheet.write('E8', 'Unit Price')
        worksheet.write('F8', 'Total Price')
        worksheet.write('G8', 'Remark')

        # Define the data format for the table header
        header_format = workbook.add_format({'bold': True, 'bg_color': '#D9EAD3', 'border': 1, 'align': 'center', 'valign': 'vcenter'})

        # Apply table header format
        worksheet.set_row(7, None, header_format)  # Row 7 corresponds to the header

        # Start filling product details below the header
        row = 9  # Start from row after the header
        total_amount = 0  # To calculate total price
        
        for index, line in enumerate(self.line_ids, start=1):
            worksheet.write(row, 0, index)  # S.No
            worksheet.write(row, 1, line.product_id.name)  # Product Name
            worksheet.write(row, 2, line.uom_id.name)  # Unit (UOM)
            worksheet.write(row, 3, line.quantity)  # Quantity
            worksheet.write(row, 4, line.price_unit)  # Unit Price
            total_price = line.quantity * line.price_unit  # Calculate Total Price
            worksheet.write(row, 5, total_price)  # Total Price
            worksheet.write(row, 6, '')  # Remark (Leave empty for now)
            total_amount += total_price  # Add to overall total amount
            row += 1

        # Add a row for Total Price
        worksheet.write(row, 4, 'Total Price')
        worksheet.write(row, 5, total_amount)

        # Create a table (from A1 to G and last row of data)
        worksheet.add_table(0, 0, row, 6, {
            'name': 'RFQ Table',
            'columns': [
                {'header': 'S.No'},
                {'header': 'Product'},
                {'header': 'Unit'},
                {'header': 'Qty'},
                {'header': 'Unit Price'},
                {'header': 'Total Price'},
                {'header': 'Remark'},
            ],
        })

        workbook.close()

        # Move to the beginning of the BytesIO object before sending it
        excel_data.seek(0)

        # Return the BytesIO object itself instead of base64 encoded data
        return excel_data


    def action_open_email_wizard(self):
        # Step 1: Generate the Excel file
        excel_data = self._generate_excel_file()

        # Step 2: Convert the Excel data to base64 directly from the BytesIO object
        attachment_base64 = base64.b64encode(excel_data.read()).decode('utf-8')

        # Step 3: Create the attachment in Odoo
        attachment = self.env['ir.attachment'].create({
            'name': f"RFQ_{self.foreign_reference}.xlsx",  # Name of the attachment (filename)
            'datas': attachment_base64,  # Base64 encoded Excel file content
            'mimetype': 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',  # MIME type for Excel
            'res_model': 'foreign.create.rfq',  # The model associated with the attachment
            'res_id': self.id,  # The ID of the current RFQ record
        })

        # Step 4: Open the email compose wizard with the attachment
        return {
            'type': 'ir.actions.act_window',
            'name': 'RFQ For Vendor',
            'res_model': 'mail.compose.message',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_model': 'foreign.create.rfq',  # The model the email is associated with
                'default_res_id': self.id,  # The specific RFQ record ID
                'default_email_to': self.vendor_email,  # Vendor email address
                'default_attachment_ids': [(4, attachment.id)],  # Attach the generated Excel file
                'default_subject': f"Request For Quotation - {self.foreign_reference}",  # Static subject
                'default_body_html': f"""
                    Dear {self.vendor_id.name},<br/><br/>
                    Here is an attachment with a request for quotation "{self.foreign_reference}" from "{self.env.user.company_id.name}".<br/><br/>
                    If you have any questions, please do not hesitate to contact us.<br/><br/>
                    Best regards,<br/>
                    {self.env.user.name}
                """,  # Static email body
            },
        }






        
    def action_create_and_open_currency_request(self):
        """Creates and opens a new foreign.currency.request form."""
        self.ensure_one()

        # Calculate the total price from the RFQ lines
        total_price = sum(line.price_total for line in self.line_ids)

        # Retrieve the vendor (partner) from the RFQ, assuming it's the supplier associated with the RFQ
        vendor = self.vendor_id    # Assuming partner_id is the vendor for the RFQ

        # Retrieve additional fields from the RFQ
        requested_by = self.requested_by  # Assuming there's a field `requested_by` on RFQ
        department = self.request_department  # Assuming there's a field `department` on RFQ
        requested_date = self.request_date  # Assuming there's a field `requested_date` on RFQ

        # Create the foreign.currency.request record
        currency_request = self.env['foreign.currency.request'].create({
            'foreign_rfq_reference': self.id,  # Link to the current RFQ
            'price_amount': total_price,  # Pass the calculated price_total to price_amount
            'vendor_id': vendor.id,  # Add vendor_id from the RFQ partner (supplier)
            'requested_by': requested_by.id if requested_by else False,  # Assuming requested_by is a Many2one field
            'request_department': department.id if department else False,  # Assuming department is a Many2one field
            'request_date': requested_date,  # Assuming it's a date field on the RFQ
            # Add other default values as needed
        })

        # Return the action to open the created record
        return {
            'type': 'ir.actions.act_window',
            'name': 'Foreign Currency Request',
            'view_mode': 'form',
            'res_model': 'foreign.currency.request',
            'res_id': currency_request.id,  # Open the created record
            'target': 'current',  # Opens in a new modal window
        }
        
  

    

    


class ForeignCreateRFQLine(models.Model):
    _name = 'foreign.create.rfq.line'
    _description = 'Foreign Line'

    foreign_rfq_id = fields.Many2one('foreign.create.rfq', string="RFQ Reference", required=True)
    vendor_id = fields.Many2one('res.partner', string="Vendor")
    product_id = fields.Many2one('product.product', string="Product", required=True, domain="[('id', 'in', available_product_ids)]")
    uom_id = fields.Many2one('uom.uom', string='Unit of Measure', related='product_id.uom_id', readonly=True, store=True)
    quantity = fields.Float(string="Quantity", required=True)
    price_unit = fields.Float(string="Unit Price")
    price_total = fields.Float(string='Total Price', compute='_compute_price_total', store=True)
    technical_by_percent = fields.Float(string="Technical(%)")
    winner = fields.Selection([('win', 'Win'), ('lost', 'Lost')], string="Winner")
    hs_code = fields.Char(string="HS Code", related='product_id.product_tmpl_id.hs_code', readonly=True)
    
    available_product_ids = fields.Many2many('product.product', string='Available Products', compute='_compute_available_product_ids', store=False)

    @api.depends('foreign_rfq_id.purchase_request_id')
    def _compute_available_product_ids(self):
        for line in self:
            if line.foreign_rfq_id.purchase_request_id:
                line.available_product_ids = line.foreign_rfq_id.purchase_request_id.line_ids.mapped('product_id')
            else:
                line.available_product_ids = self.env['product.product'].browse()

    @api.depends('quantity', 'price_unit')
    def _compute_price_total(self):
        for line in self:
            line.price_total = line.quantity * line.price_unit

    def unlink(self):
        for line in self:
            if line.foreign_rfq_id.state != 'draft':
                raise ValidationError(_("You can only delete lines when the RFQ is in draft state."))
        return super(ForeignCreateRFQLine, self).unlink()
