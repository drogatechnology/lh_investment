from odoo import models, fields

class PurchaseOrder(models.Model):
    _inherit = 'purchase.order'

    shipment_percent = fields.Float(string="1st Shipment Amount")
    is_shipment_partial = fields.Boolean(string="Is Shipment Partial")
    shipment_date = fields.Date(string="Estimated Shipment Date")
    production_completion_date = fields.Date(string="Estimated Production Completion Date")
    shipment_scan_copy_received_date = fields.Date(string="Scan Copy Received Date")
    shipment_original_copy_received_date = fields.Date(string="Original Document Received Date")
    shipment_original_send_from_supplier = fields.Date(string="Original Document Sent From Supplier to Applicant Bank")
    
    shipment_original_send_from_supplier_courier = fields.Float(string="Original Document Sent By Courier")
    document_tracking_number = fields.Char(string="Courier Tracking Number")
    shipment_original_copy_received_by_applicant_bank = fields.Date(string="Original Document Received by Applicant Bank")
    disrepancy = fields.Date(string="Discrepancy Date")
    exchange_rate_lc_settlement = fields.Float(string="Exchange Rate")  # Changed to Float
    shipment_lc_amount = fields.Float(string="LC Settlement Amount")  # Changed to Float
    shipmnet_doc_handed_to_finance = fields.Date(string="Document Handed to Finance")
    supplier_payment_date = fields.Date(string="Supplier Payment Date")
