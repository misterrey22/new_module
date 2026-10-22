from odoo import fields, models


class LibraryBook(models.Model):
    _name = "library.book"
    _description = "Library Book"

    name = fields.Char(required=True)
    author = fields.Char()
    isbn = fields.Char()
    publish_year = fields.Integer()
    copy_ids = fields.One2many("library.copy", "book_id", string="Copies")
