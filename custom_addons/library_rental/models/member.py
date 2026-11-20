from odoo import fields, models
from odoo.tools import _


class LibraryMember(models.Model):
    _name = "library.member"
    _description = "Library Member"
    _rec_name = "name"

    name = fields.Char(string="Name", required=True)
    membership_number = fields.Char(string="Membership Number", required=True)
    user_id = fields.Many2one(
        "res.users",
        string="User",
        ondelete="set null",
    )

    _membership_number_unique = models.Constraint(
        "unique(membership_number)",
        _("Membership number must be unique."),
    )
    _unique_user = models.Constraint(
        "unique(user_id)",
        _("One user can be linked to only one library member."),
    )
