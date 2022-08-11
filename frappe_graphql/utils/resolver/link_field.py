from graphql import GraphQLSchema, GraphQLResolveInfo

import frappe

from .dataloaders import get_doctype_dataloader
from .utils import get_singular_doctype


def setup_link_field_resolvers(schema: GraphQLSchema):
    """
    This will set up Link fields on DocTypes to resolve target docs
    """
    for type_name, gql_type in schema.type_map.items():
        dt = get_singular_doctype(type_name)
        if not dt:
            continue

        meta = frappe.get_meta(dt)
        for df in meta.get_link_fields() + meta.get_dynamic_link_fields():
            if df.fieldname not in gql_type.fields:
                continue

            gql_field = gql_type.fields[df.fieldname]
            gql_field.frappe_docfield = df
            if df.fieldtype == "Link":
                gql_field.resolve = _resolve_link_field
            elif df.fieldtype == "Dynamic Link":
                gql_field.resolve = _resolve_dynamic_link_field
            else:
                continue

            _name_df = f"{df.fieldname}__name"
            if _name_df not in gql_type.fields:
                continue

            gql_type.fields[_name_df].resolve = _resolve_link_name_field


def _resolve_link_field(obj, info: GraphQLResolveInfo, **kwargs):
    df = _get_frappe_docfield_from_resolve_info(info)
    if not df:
        return None

    dt = df.options
    dn = obj.get(info.field_name)

    if not (dt and dn):
        return None

    return get_doctype_dataloader(dt).load(dn)


def _resolve_dynamic_link_field(obj, info: GraphQLResolveInfo, **kwargs):
    df = _get_frappe_docfield_from_resolve_info(info)
    if not df:
        return None

    dt = obj.get(df.options)
    if not dt:
        return None

    dn = obj.get(info.field_name)
    if not dn:
        return None

    return get_doctype_dataloader(dt).load(dn)


def _resolve_link_name_field(obj, info: GraphQLResolveInfo, **kwargs):
    df = info.field_name.split("__name")[0]
    return obj.get(df)


def _get_frappe_docfield_from_resolve_info(info: GraphQLResolveInfo):
    return getattr(info.parent_type.fields[info.field_name], "frappe_docfield", None)