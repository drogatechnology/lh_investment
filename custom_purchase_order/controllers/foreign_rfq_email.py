from odoo import http
from odoo.http import request

class ProformaInvoiceController(http.Controller):
    @http.route('/report/proforma_invoice/<int:sale_order_id>', type='http', auth="user")
    def get_proforma_invoice(self, sale_order_id, **kwargs):
        # Find the report action
        report = request.env.ref('custom_sale_proforma_invoice.action_report_proforma_invoice')
        
        # Render the PDF for the given sale order ID
        pdf_content, content_type = report._render_qweb_pdf([sale_order_id])

        # Return the PDF content as an inline response (display in browser)
        pdf_http_headers = [
            ('Content-Type', 'application/pdf'),
            ('Content-Length', len(pdf_content)),
            ('Content-Disposition', 'inline; filename="Proforma_Invoice.pdf"')
        ]
        return request.make_response(pdf_content, headers=pdf_http_headers)
