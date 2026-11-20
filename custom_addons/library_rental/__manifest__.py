{
    "name": "Бібліотечний прокат",
    "version": "19.0.1.1.0",
    "author": "Library Rental",
    "category": "Services",
    "summary": "Облік книг, примірників, читачів і видач",
    "description": "Модуль для керування бібліотечним фондом і видачами книг.",
    "depends": ["base"],
    "data": [
        "security/library_security.xml",
        "security/ir.model.access.csv",
        "views/return_wizard_views.xml",
        "views/library_views.xml",
        "report/report_member_loan_history.xml",
    ],
    "demo": [
        "demo/library_demo.xml",
    ],
    "assets": {
        "web.assets_backend": [
            "library_rental/static/src/scss/library_loan.scss",
        ],
    },
    "license": "LGPL-3",
    "installable": True,
    "application": True,
}
