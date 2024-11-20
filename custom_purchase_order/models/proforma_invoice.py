from odoo import models, fields, api

class PurchaseOrder(models.Model):
    _inherit = 'foreign.create.rfq'

    proforma_invoice_no = fields.Char(string="Proforma Invoice Number")
    proforma_invoice_date = fields.Date(string="Proforma Invoice Date")
    incoterm = fields.Many2one('account.incoterms', string="Incoterm")
    country_of_origin = fields.Many2one('res.country',string="Country Of Origin")
    
    MOD_OF_SHIPMENT_TYPE_SELECTION = [
        ('air', 'AIR'),
        ('sea', 'SEA'),
    ]
    
    mod_of_shipment = fields.Selection(
        selection=MOD_OF_SHIPMENT_TYPE_SELECTION,
        string="Mod of Shipment ",
        required=True,
        default='air',  # Set a default value if needed
    )
    port_of_loding = fields.Many2one('purchase.port.loading',string="Port Of Loading")
    port_of_discharge = fields.Many2one('purchase.port.loading',string="Port Of Discharge")    
    port_of_final_destination = fields.Many2one('purchase.port.loading',string="Port Of Final Destination") 
    payment_term = fields.Float(string="Custom Duty Tax")
    