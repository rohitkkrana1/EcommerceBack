import frappe
import json
from frappe import auth
from pprint import pprint

@frappe.whitelist(allow_guest=True)
def getItems(filter="", limit=10, offset=0):
    condition = ''

    if filter:
        parsed_filter = json.loads(filter)
        for item in parsed_filter:
            operator = item['operator'].upper()
            field = item['field']
            value = item['value']

            if operator == 'IN' or operator == 'NOT IN':
                j = ','.join([f"'{x}'" for x in value])
                condition += f" AND A.`{field}` {operator} ({j})"
            elif operator == 'LIKE':
                condition += f" AND A.`{field}` {operator} '%{value}%'"
            else:
                condition += f" AND A.`{field}` {operator} '{value}'"

    sql = f"""
    SELECT A.*
    FROM (
        SELECT a.*, b.currency, b.price_list_rate, 
        GROUP_CONCAT(d.dfp_external_storage_s3_key) AS images, 
        GROUP_CONCAT(DISTINCT e.tag) categories
        FROM `tabWebsite Item` a 
        LEFT JOIN `tabItem Price` b ON a.item_code = b.item_code
        LEFT JOIN `tabFile` d ON d.attached_to_doctype='Website Item' AND a.name = d.attached_to_name
        LEFT JOIN `tabTag Link` e ON e.document_type = 'Website Item' AND e.`document_name` = a.name
        WHERE a.published = 1 
        GROUP BY a.name
        LIMIT {limit} OFFSET {offset}
    ) A
    WHERE 1=1 {condition}
    """  
    result = frappe.db.sql(sql, as_dict=True)
    return result


@frappe.whitelist(allow_guest=True)
def userRegister():
    data = json.loads(frappe.request.data)
    try:
        user = frappe.get_doc({"doctype":"User","first_name":data['name'],"email":data['email'],"user_type":"Website User","mobile_no":data['mobile'],"new_password":data["password"],'role_profile_name':"Zuri Customer"})
        user.insert(ignore_permissions = True)
        customer = frappe.get_doc({"doctype":"Customer","customer_name":data["name"],"customer_type":"Individual","customer_group":"Individual","territory":"India"})
        customer.insert(ignore_permissions = True)
        contact = data['name'].split(" ")
        contact  = frappe.get_doc({"doctype":"Contact","first_name":contact[0],"last_name": len(contact) > 1 and contact[1] or ""})
        contact.append("email_ids", dict(email_id=data['email'], is_primary=1))
        contact.append("links", dict(link_doctype='Customer', link_name=data['name']))
        contact.insert(ignore_permissions = True)
        frappe.db.commit()
        frappe.response["message"]="data saved successfully"
    except Exception as e:
        frappe.db.rollback()
        frappe.local.response["message"] = e


@frappe.whitelist(allow_guest=True)
def slider(slider_name):
    images = frappe.db.sql(f"""SELECT b.idx,b.heading as title,b.`description`,b.url,a.dfp_external_storage_s3_key AS image FROM tabFile a 
JOIN `tabWebsite Slideshow Item` b ON a.attached_to_name=b.parent 
AND a.attached_to_doctype=b.parenttype #AND a.file_url=b.image
WHERE a.attached_to_name=%s
GROUP BY a.dfp_external_storage_s3_key
ORDER BY b.idx""",(slider_name,)) 
    return images

@frappe.whitelist(allow_guest=True)
def getCaategoryFrontPage(filter=''):
    str=''
    if filter:
        f = json.loads(filter)
        for fil in f:
            if(fil['operator'].upper() == 'IN'):
                j=','.join(f"""'{x}'""" for x in fil['value'])
                str += f" AND A.`{fil['field']}` {fil['operator']} ({j})"

    sql=f"""SELECT A.* FROM (SELECT a.name,a.parent_item_group,a.route,group_concat(b.dfp_external_storage_s3_key) as image FROM `tabItem Group` a JOIN tabFile b ON a.item_group_name = b.attached_to_name AND b.attached_to_doctype='Item Group'  Group By a.name) A where 1=1 {str}"""
    cate = frappe.db.sql(sql,as_dict=True)
    return cate
    

@frappe.whitelist(allow_guest=True)
def login():
    data = json.loads(frappe.request.data)
    
    loginManager = frappe.auth.LoginManager()
    loginManager.authenticate(user= data["username"],pwd= data["password"])
    loginManager.post_login()
    if not frappe.session.user:
        frappe.clear_messages()
        frappe.response['message'] = {
            "success_key":0,
            "message":"username or password is invalid"
        }

    api_gen = generate_keys(frappe.session.user)
    user = frappe.get_doc('User',frappe.session.user)
    frappe.response["message"] = {
        "success_key":1,
        "message":"Authentication Success",
        "api_key": user.api_key,
        "api_secret":api_gen,
        "name":user.username,
        "email":user.email
    }


def generate_keys(user):
    users = frappe.get_doc('User',user)   
    api_secret = frappe.generate_hash(length=25)

    if not users.api_key:
        users.api_key = frappe.generate_hash(length=15)

    users.api_secret = api_secret
    #user.update(ignore_permissions = True)
    users.save(ignore_permissions=True)
    return api_secret


@frappe.whitelist()
def saveCart():
    return 0


@frappe.whitelist()
def getProfile():
    user = frappe.get_user().doc.name
    if user:
        profile = frappe.get_doc('User',{'email':user})
        frappe.response["message"]={
            'profile':{
                
                'name':{'firstName':profile.first_name,
                        'fullName':profile.full_name
                        },
                'email':profile.email,
                'timeZone':profile.time_zone,
                'language':profile.language,
                'phone':profile.mobile_no,
                'avatar':'',
                'dateOfBirth':'2022-10-22'
            }
        }
    else:
        frappe.response["message"] = {
            "success_key":0,
            "message":"No User found"
        }


@frappe.whitelist()
def editProfile():
    user = frappe.get_user().doc.name
    if user:
        data = json.loads(frappe.request.data)
        profile = frappe.get_doc('Contact',{'user':user})
        profile.first_name = data['first_name']
        profile.mobile_no = data['contact']
        profile.save(ignore_permissions=True)
        frappe.response["message"] = {
            "success_key":1,
            "message":"Profile Edit is successfully Done!"
        }
    else:
        frappe.response["message"] = {
            "success_key":0,
            "message":"Profile Edit was not successful"
        }

@frappe.whitelist()
def getAddresses():
    user = frappe.get_user().doc.name
    if user:
        try:
            contact = frappe.get_doc('Contact',{'user':user})
            if(contact):
                customer = frappe.get_doc('Dynamic Link',{'parent':contact.name})
                address_names = frappe.db.get_all(
                "Dynamic Link",
                fields=("parent"),
                filters=dict(parenttype="Address", link_doctype='Customer', link_name=customer.link_name),
                )
            
            out = []

            for a in address_names:
                address = frappe.get_all("Address", filters={'name':a.parent},fields=['*'])
                out.append(address[0])

            frappe.response["message"] = {
                "Address":out
            }
        
        except Exception as err:
            frappe.response["message"] = {
            "success_key":0,
            "message":err
        }

    else:
        frappe.response["message"] = {
            "success_key":0,
            "message":"No User found"
        }
        
@frappe.whitelist()
def add_address():
    user = frappe.get_user().doc.name
    if user:
        contact = frappe.get_doc('Contact',{'user':user})
        if(contact):
            try:
                data = json.loads(frappe.request.data)
                customer = frappe.get_doc('Dynamic Link',{'parent':contact.name}) 
                #return customer.link_name
                address = frappe.get_doc({
                    'doctype':'Address',
                    'address_title':data['address_title'],
                    'address_type':'Personal',
                    'address_line1':data['address_line1'],
                    'address_line2':data['address_line2'],
                    'city':data['city'],
                    'county':data['state'] and data['state'] or "",
                    'state':data['state'] and data['state'] or "",
                    'pincode': data['pincode'] and data['pincode'] or "",
                    'country':data['country'] and data['country'] or "India",
                    'email_id': data['email_id'] and data['email_id'] or "",
                    'phone': data['phone'] and data['phone'] or ""
                    })
                address.append("links", dict(link_doctype='Customer', link_name=customer.link_name))
                address.insert()           
                frappe.response["message"] = {
                    "success_key":1,
                    "message":"Address Added is successfully Done!"
                }
            except Exception as err:
                frappe.response["message"] = {
                "success_key":0,
                "message":err
                }
        
    else:
        frappe.response["message"] = {
            "success_key":0,
            "message":"No User found"
        }         
        

@frappe.whitelist()
def getAddress():
    user = frappe.get_user().doc.name
    if user:
        try:
            data = json.loads(frappe.request.data)
            address = frappe.get_doc('Address',data['name'])
            frappe.response["message"]={
                'Address': address
            }
        except Exception as err:
            frappe.response["message"] = {
            "success_key":0,
            "message":err
        }

    else:
        frappe.response["message"] = {
            "success_key":0,
            "message":"No User found"
        }


@frappe.whitelist()
def editAddress():
    data = json.loads(frappe.request.data)
    addr = frappe.get_doc('Address',data['id'])
    if addr.name:            
        addr.address_title= data['address_title']
        addr.address_line1=data['address_line1']
        addr.address_line2=data['address_line2']
        addr.city=data['city']
        addr.state=data['state']
        addr.pincode=data['pincode']
        addr.country=data['country']
        addr.email_id = data['email_id']   
        addr.phone = data['phone']   
        addr.save()            
        frappe.response["message"] = {
            "success_key":1,
            "message":"Address Edit is successfully Done!"
        }
    else:
        frappe.response["message"] = {
            "success_key":0,
            "message":"Address Edit was not successful"
        }
