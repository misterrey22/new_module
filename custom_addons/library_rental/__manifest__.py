{
    "name": "Library Rental",
    "version": "19.0.1.0.0",
    "category": "Services",
    "summary": "Manage library books, members, and loans",
    "depends": ["base"],
    "data": [
        "security/ir.model.access.csv",
        "views/library_views.xml",
    ],
    "demo": [
        "demo/library_demo.xml",
    ],
    "license": "LGPL-3",
    "installable": True,
    "application": True,
}
