{
    'name': 'Custom Purchase Request',
    'version': '1.0',
    'summary': 'Manage Local and Foreign Purchase Orders and RFQs separately.',
    'depends': ['purchase'],  # Ensure this module is installed
    'data': [
        'security/ir.model.access.csv',
        'views/purchase_menu.xml',  # XML file for menus and actions
        'data/purchase_order_sequence.xml',  # XML file for sequences
        'views/local_purchase_request_views.xml',  # XML for local purchase request views
        'data/local_purchase_request.xml',  # Data for local purchase requests
        'views/local_rfq.xml',  # XML for RFQ views
        'data/local_rfq_sequence.xml',  # Data for RFQ sequences    
        'report/rfq_report_template.xml',
        'report/rfq_report.xml',
        
    ],
    'assets': {
        'web.assets_backend': [
            'custom_purchase_order/static/src/css/custom_styles.css',  # Correct module name
        ],
    },
    'installable': True,
    'application': False,
}
