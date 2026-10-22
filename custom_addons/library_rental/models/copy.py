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
    inventory_number = fields.Char()
    condition = fields.Selection(
        [
            ("new", "Новий"),
            ("good", "Добрий"),
            ("damaged", "Пошкоджений"),
        ],
        string="Condition",
        default="good",
        required=True,
    )

    _rec_name = "inventory_number"
