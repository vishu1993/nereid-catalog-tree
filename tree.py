# -*- coding: utf-8 -*-
'''
    Nereid Catalog Tree

    Products catalogue on a tree

    :copyright: (c) 2013 by Openlabs Technologies & Consulting (P) Ltd.
    :license: GPLv3, see LICENSE for more details

'''

from nereid import abort, render_template
from nereid.helpers import slugify
from nereid.contrib.pagination import Pagination

from trytond.model import ModelView, ModelSQL, fields
from trytond.exceptions import UserError
from trytond.pool import Pool, PoolMeta
from trytond.pyson import Eval

__all__ = [
    'Product', 'Node', 'ProductNodeRelationship',
    'Website', 'WebsiteTreeNode'
]
__metaclass__ = PoolMeta


class Product:
    "Product extension for nereid"
    __name__ = 'product.product'

    nodes = fields.Many2Many(
        'product.product-product.tree_node',
        'product', 'node', 'Tree Nodes'
    )


class Node(ModelSQL, ModelView):
    """
    Tree Node
    A tree is a hierachcial way to group products together.
    A vertex or node is the fundamental unit of which graphs/trees are formed
    """
    __name__ = "product.tree_node"

    name = fields.Char('Name', required=True, select=True, translate=True)
    slug = fields.Char(
        'Slug', depends=['name'], on_change_with=['name', 'slug', 'parent'],
        required=True, select=True, translate=True
    )
    type_ = fields.Selection([
        ('catalog', 'Catalog'),
    ], 'Type', required=True, select=True)
    parent = fields.Many2One(
        'product.tree_node', 'Parent', select=True,
        depends=['type_'],
        domain=[('type_', '=', Eval('type_'))],
        left='left', right='right', ondelete="RESTRICT",
    )
    children = fields.One2Many('product.tree_node', 'parent', 'Children')
    left = fields.Integer('Left', select=True)
    right = fields.Integer('Right', select=True)
    products = fields.Many2Many(
        'product.product-product.tree_node',
        'node', 'product', 'Products'
    )
    products_per_page = fields.Integer('Products per Page')

    @classmethod
    def validate(cls, nodes):
        super(Node, cls).validate(nodes)
        cls.check_recursion(nodes, rec_name='name')

    def on_change_with_slug(self):
        """
        On change the name and slug, ensure that the slug field is auto
        filled with a generated slug, if the field is empty
        """
        if not self.slug:
            self.slug = slugify(self.get_rec_name('rec_name'))
        return self.slug

    def get_rec_name(self, name=None):
        if self.parent:
            return self.parent.rec_name + ' / ' + self.name
        return self.name

    @staticmethod
    def default_left():
        return 0

    @staticmethod
    def default_right():
        return 0

    @staticmethod
    def default_products_per_page():
        return 10

    def render(self, slug=None, page=1):
        """
        Renders a page of products in the tree and all of its branches

        :param slug: slug of the browse node to be shown
        :param page: page of the products to be displayed
        """
        Product = Pool().get('product.product')

        try:
            self.slug
        except UserError:
            abort(404)

        if self.type_ != 'catalog':
            # Display only catalog nodes
            abort(403)

        products = Pagination(Product, [
            ('displayed_on_eshop', '=', True),
            ('nodes.left', '>=', self.left),
            ('nodes.right', '<=', self.right),
        ], page=page, per_page=self.products_per_page)

        return render_template(
            'catalog/node.html', products=products, node=self
        )


class ProductNodeRelationship(ModelSQL):
    """
    This is the relation between a node in a tree
    and a product
    """
    __name__ = 'product.product-product.tree_node'

    product = fields.Many2One(
        'product.product', 'Product',
        ondelete='CASCADE', select=True, required=True,
    )
    node = fields.Many2One(
        'product.tree_node', 'Node',
        domain=[('type_', '=', 'catalog')],
        ondelete='CASCADE', select=True, required=True
    )


class Website:
    """
    Extend site to add templates for product listing and
    category listing
    """
    __name__ = 'nereid.website'

    featured_products_node = fields.Many2One(
        'product.tree_node', 'Featured Products Node',
        domain=[('type_', '=', 'catalog')]
    )
    latest_products_node = fields.Many2One(
        'product.tree_node', 'Latest Products Node',
        domain=[('type_', '=', 'catalog')]
    )
    upcoming_products_node = fields.Many2One(
        'product.tree_node', 'Upcoming Products Node',
        domain=[('type_', '=', 'catalog')]
    )


class WebsiteTreeNode(ModelSQL):
    "Root Tree Nodes on a Website"
    __name__ = 'nereid.website-product.tree_node'
    _table = 'website_tree_node_rel'

    website = fields.Many2One(
        'nereid.website', 'Website',
        ondelete='CASCADE', select=True, required=True
    )
    node = fields.Many2One(
        'product.tree_node', 'Tree Nodes',
        domain=[('type_', '=', 'catalog')],
        ondelete='CASCADE', select=True, required=True
    )
