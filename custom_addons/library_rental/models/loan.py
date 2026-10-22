from odoo import api, fields, models
from odoo.exceptions import ValidationError


class LibraryLoan(models.Model):
    _name = "library.loan"
    _description = "Library Loan"

    copy_id = fields.Many2one(
        "library.copy",
        required=True,
        ondelete="restrict",
        string="Copy",
    )
    member_id = fields.Many2one(
        "library.member",
        required=True,
        ondelete="restrict",
        string="Member",
    )
    book_author = fields.Char(
        related="copy_id.book_id.author",
        string="Book Author",
    )
    loan_date = fields.Date(default=fields.Date.today, required=True)
    due_date = fields.Date()
    return_date = fields.Date()
    state = fields.Selection(
        [
            ("active", "Active"),
            ("returned", "Returned"),
        ],
        default="active",
        required=True,
    )

    @api.constrains("copy_id", "state")
    def _check_one_active_loan_per_copy(self):
        for loan in self.filtered_domain([("state", "=", "active")]):
            duplicate = self.search(
                [
                    ("copy_id", "=", loan.copy_id.id),
                    ("state", "=", "active"),
                    ("id", "!=", loan.id),
                ],
                limit=1,
            )
            if duplicate:
                raise ValidationError(
                    "A copy cannot have more than one active loan."
                )
