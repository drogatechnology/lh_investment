{
    'name': 'Store Requestion',
    'version': '1.0',
    'summary': 'Manage Store Requestion.',
    'depends': ['base','stock','hr','custom_purchase_order','de_hr_workspace'],  # Ensure this module is installed
    'data': [
        
        'security/store_requestion_security.xml',
        # 'security/foreign_purchase_request_security.xml',
        # 'security/payment_request_securtiy.xml',
        'security/ir.model.access.csv',
        
        'data/store_requestion_seq.xml',  
        # 'data/local_purchase_request.xml',  
        # 'data/local_rfq_sequence.xml',  
        # 'data/foreign_rfq_sequence.xml',
        # 'data/foreign_purchase_request.xml',
        # 'data/without_rfq_purchase_request_sequence.xml',
        # 'data/payment_request_sequence.xml',
        # 'data/foreign_currency_request_sequence.xml',
        # 'data/foreign_email_template.xml',
        # 'data/email_templates.xml',
        
        
        'views/store_requestion_view.xml',         
        # 'views/local_purchase_request_views.xml',         
        # 'views/local_rfq.xml',           
        # 'views/withoutrfq_purchase_request.xml', 
        # 'views/foreign_purchase_request_view.xml',
        # 'views/foreign_rfq.xml',
        # 'views/local_payment_request.xml',
        # 'views/purchase_margin_views.xml',
        # 'views/lc_view.xml',
        # 'views/shippment_view.xml',
        # 'views/good_clearance_post_clerance_view.xml',
        # 'views/port_of_loading_views.xml',
        # 'views/foreign_currency_request.xml',
        # 'views/exchange_rate_menu.xml',
        # 'views/amount_threshold_required_ceo.xml',        
        # 'views/mail_views.xml',
        
        
        
        # 'wizard/foreign_rfq_send_email.xml',
        
        
        # 'reports/rfq_report_template.xml',
        # 'reports/rfq_report_template_foreign.xml',
        # 'reports/rfq_report.xml',
        
        # 'views/res_config_settings_views.xml',
        # 'views/res_users_views.xml',
        
        
        # 'views/foreign_purchase_order_added_pages.xml',
        
        
        
        
        # 'report/rfq_report_template.xml',
        # 'report/rfq_report.xml',
        
    ],
    'assets': {
        
        
    },
    'installable': True,
    'application': False,
}
