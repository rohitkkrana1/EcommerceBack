# -*- coding: utf-8 -*-
# Copyright (c) 2021, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

import json
import frappe
from frappe.utils import cint
from . import cdn 
from erpnext.e_commerce.product_data_engine.filters import ProductFiltersBuilder
from ecomm.EnginQuery import ProductQuery
from erpnext.setup.doctype.item_group.item_group import get_child_groups_for_website
from erpnext.e_commerce.variant_selector.utils import get_attributes_and_values
cdn = "https://erpasset.s3.ap-south-1.amazonaws.com/"
@frappe.whitelist(allow_guest=True)
def testing():
	item_names = []
	item_name_list = frappe.db.get_all(
       			"Tag Link",
				fields=["document_name"],
          		filters={
					"tag":"all-sarees",
					"document_type":"Website Item"
				}
            )
	item_names.append(x.document_name for x in item_name_list)   
	item_code_list = frappe.db.get_all(
					"Website Item",
					fields=["item_code"],
					filters=[
						["name","in",item_names]
					]
				)
	return item_names

@frappe.whitelist(allow_guest=True)
def get_product_filter_data(query_args=None):
	"""
	Returns filtered products and discount filters.
	:param query_args (dict): contains filters to get products list

	Query Args filters:
	search (str): Search Term.
	field_filters (dict): Keys include item_group, brand, etc.
	attribute_filters(dict): Keys include Color, Size, etc.
	start (int): Offset items by
	item_group (str): Valid Item Group
	from_filters (bool): Set as True to jump to page 1
	"""
	#return query_args
	if isinstance(query_args, str):
		query_args = json.loads(query_args)
		query_args = frappe._dict(query_args)
  
	if query_args:
		search = query_args.get("search")
		field_filters = query_args.get("field_filters", {})
		attribute_filters = query_args.get("attribute_filters", {})
		tags_filters = query_args.get("tags_filters")
		start = cint(query_args.get("start")) if query_args.get("start") else 0
		item_group = query_args.get("item_group")
		from_filters = query_args.get("from_filters")
	else:
		search, attribute_filters, tags_filters, item_group, from_filters = None, None, None, None, None
		field_filters = {}
		start = 0
	# if new filter is checked, reset start to show filtered items from page 1
	if from_filters:
		start = 0

	sub_categories = []
	if item_group:
		sub_categories = get_child_groups_for_website(item_group, immediate=True)

	engine = ProductQuery()
	
	try:
		result = engine.query(
			attribute_filters,tags_filters, field_filters, search_term=search, start=start, item_group=item_group
		)
	except Exception:
		frappe.log_error("Product query with filter failed")
		return {"exc": "Something went wrong!"}

	result["items"] = getImages(result["items"])
	result["items"] = getVeriant(result["items"])

	# discount filter data
	filters = {}
	discounts = result["discounts"]

	if discounts:
		filter_engine = ProductFiltersBuilder()
		filters["discount_filters"] = filter_engine.get_discount_filters(discounts)

	return {
		"items": result["items"] or [],
		"filters": filters,
		"settings": engine.settings,
		"sub_categories": sub_categories,
		"items_count": result["items_count"],
	}

def getImages(items= []):

    if len(items) > 0:
        for item in items:
        
            images = frappe.get_all('File',filters={"attached_to_name":item.name,"attached_to_doctype":'Website Item'},fields={"dfp_external_storage_s3_key"})
            item['images']=[]
            if len(images)>0:
                item["images"] = [f"{cdn+x.dfp_external_storage_s3_key}" for x in images]
                
    return items

def getVeriant(items=[]):
	f=[]
	if len(items)>0:
		for item in items:
			if item.has_variants==1:
				item['variant'] = get_attributes_and_values(item.item_code)
				f.append(item)
	return items


@frappe.whitelist(allow_guest=True)
def get_guest_redirect_on_action():
	return frappe.db.get_single_value("E Commerce Settings", "redirect_on_action")