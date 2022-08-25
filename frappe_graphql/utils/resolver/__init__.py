from graphql import GraphQLSchema, GraphQLType, GraphQLResolveInfo

import frappe
from frappe.model.meta import Meta

from .root_query import setup_root_query_resolvers
from .link_field import setup_link_field_resolvers
from .select_fields import setup_select_field_resolvers
from .child_tables import setup_child_table_resolvers
from .translate import setup_translatable_resolvers
from .utils import get_singular_doctype


def setup_default_resolvers(schema: GraphQLSchema):
    setup_root_query_resolvers(schema=schema)

    doctype_resolver_processors = frappe.get_hooks("doctype_resolver_processors")

    # Setup custom resolvers for DocTypes
    for type_name, gql_type in schema.type_map.items():
        dt = get_singular_doctype(type_name)
        if not dt:
            continue

        meta = frappe.get_meta(dt)

        setup_frappe_df(meta, gql_type)
        setup_doctype_resolver(meta, gql_type)
        setup_link_field_resolvers(meta, gql_type)
        setup_select_field_resolvers(meta, gql_type)
        setup_child_table_resolvers(meta, gql_type)
        setup_translatable_resolvers(meta, gql_type)

        for cmd in doctype_resolver_processors:
            frappe.get_attr(cmd)(meta=meta, gql_type=gql_type)


def setup_frappe_df(meta: Meta, gql_type: GraphQLType):
    """
    Sets up frappe-DocField on the GraphQLFields as `frappe_df`.
    This is useful when resolving:
    - Link / Dynamic Link Fields
    - Child Tables
    - Checking if the leaf-node is translatable
    """
    for df in meta.fields:
        if df.fieldname not in gql_type.fields:
            continue

        gql_type.fields[df.fieldname].frappe_df = df


def setup_doctype_resolver(meta: Meta, gql_type: GraphQLType):
    """
    Sets custom resolver to BaseDocument.doctype field
    """
    if "doctype" not in gql_type.fields:
        return

    gql_type.fields["doctype"].resolve = _doctype_resolver


def _doctype_resolver(obj, info: GraphQLResolveInfo, **kwargs):
    dt = get_singular_doctype(info.parent_type.name)
    return dt
