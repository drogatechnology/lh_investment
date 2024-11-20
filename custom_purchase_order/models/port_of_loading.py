from odoo import models, fields

class PortOfLoading(models.Model):
    _name = 'purchase.port.loading'
    _description = 'Port of Loading'

    name = fields.Char(string="Port Name", required=True)
    country = fields.Many2one('res.country', string="Country", required=True)
    
    port_type = fields.Selection(
        selection=[
            ('loading', 'Loading'),
            ('discharge', 'Discharge'),
            ('final_destination', 'Final Destination'),
        ],
        string="Port Type",
        required=True
    )

    shipment_type = fields.Selection(
        selection=[
            ('air', 'Air'),
            ('sea', 'Sea'),
        ],
        string="Shipment Type",
        required=True
    )

    state = fields.Selection(
        selection=[
            ('active', 'Active'),
            ('close', 'Close'),
        ],
        string="State",
        default='active',
        required=True
    )
