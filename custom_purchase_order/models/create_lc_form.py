class PurchaseOrder(models.Model):
    _inherit = 'purchase.order'
    order_liness = fields.One2many('lc_created_detail', 'purchase_request_lc_id', string='Order Lines')


class Followup(models.Model):
    _name = 'lc_created_detailss'
    _description = 'Follow-up Log'

    date = fields.Date(string='History Follow -up', default=fields.Date.today(), required=True)
    method = fields.Char(string='Method of communication ', required=True)
    result = fields.Char(string='Communication result', required=True)
    purchase_request_lc_id = fields.Many2one('purchase.order', string='Shipping Invoice')