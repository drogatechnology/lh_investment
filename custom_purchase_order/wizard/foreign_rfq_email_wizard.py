from odoo import models, fields

class ForeignRFQEmailWizard(models.TransientModel):
    _name = 'foreign.rfq.email.wizard'
    _description = 'Foreign RFQ Email Wizard'

    vendor_email = fields.Char(string="Vendor Email", required=True)
    message = fields.Text(string="Message", required=True)
    pdf_attachment = fields.Binary(string="Attachment")  # This will hold the Excel file
    attachment_name = fields.Char(string="Attachment Name")
    rfq_id = fields.Many2one('foreign.create.rfq', string="RFQ", required=True)

    def send_email(self):
        """Send the RFQ email with the attachment."""
        # Create email values
        email_values = {
            'email_to': self.vendor_email,
            'subject': f"Request for Quotation - {self.rfq_id.foreign_reference}",
            'body_html': self.message,
            'attachment_ids': [(0, 0, {
                'name': self.attachment_name,
                'datas': self.pdf_attachment,
                'datas_fname': self.attachment_name,
                'mimetype': 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
            })],
        }

        # Send the email using the mail.mail model
        mail = self.env['mail.mail'].create(email_values)
        mail.send()

        return {'type': 'ir.actions.client', 'tag': 'reload'}


    def cancel(self):
        """Close the wizard"""
        return {'type': 'ir.actions.act_window_close'}
