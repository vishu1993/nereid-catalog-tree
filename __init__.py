# -*- coding: utf-8 -*-
"""
    __init__

    :copyright: (c) 2013 by Openlabs Technologies & Consulting (P) Limited
    :license: BSD, see LICENSE for more details.
"""
from trytond.pool import Pool
from tree import (
    Product, Node, ProductNodeRelationship,
    Website, WebsiteTreeNode,
)


def register():
    Pool.register(
        Product,
        Node,
        ProductNodeRelationship,
        Website,
        WebsiteTreeNode,
        module='nereid_catalog_tree',
        type_='model'
    )
