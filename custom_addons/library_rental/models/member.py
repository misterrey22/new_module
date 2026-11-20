from odoo import fields, models
from odoo.tools import _


class LibraryMember(models.Model):
    _name = "library.member"
    _description = "Library Member"
    _rec_name = "name"

    name = fields.Char(string="Name", required=True)
    membership_number = fields.Char(string="Membership Number", required=True)

    _membership_number_unique = models.Constraint(
        "unique(membership_number)",
        _("Membership number must be unique."),
    )
