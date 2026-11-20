from odoo import fields, models


class LibraryCopy(models.Model):
    _name = "library.copy"
    _description = "Library Copy"

    # Restrict deletion so removing a book cannot silently delete its copies.
    book_id = fields.Many2one(
        "library.book",
        required=True,
        ondelete="restrict",
        string="Book",
    )
    inventory_number = fields.Char(string="Inventory Number")
    condition = fields.Selection(
        [
            ("new", "New"),
            ("good", "Good"),
            ("damaged", "Damaged"),
        ],
        string="Condition",
        default="good",
        required=True,
    )

    _rec_name = "inventory_number"
