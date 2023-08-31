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
        user = frappe.get_doc({"doctype":"User","first_name":data['name'],"email":data['email'],"user_type":"Website User","mobile_no":data['mobile'],"new_password":data["password"]})
        user.insert(ignore_permissions = True)
        customer = frappe.get_doc({"doctype":"Customer","customer_name":data["name"],"coustmer_type":"Individual","customer_group":"Individual","territory":"India"})
        customer.insert(ignore_permissions = True)
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
        profile = frappe.get_doc('Customer',{'customer_name':user})
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
def getContact():
    user = frappe.get_user().doc.name
    if user:
        try:
            contact = frappe.get_all('Contact',filters={'user':user},fields=['name','address','email_id','first_name','mobile_no','last_name','middle_name'])
            frappe.response["message"]={
                'Address': contact
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
def getSingleContact():
    user = frappe.get_user().doc.name
    if user:
        try:
            data = json.loads(frappe.request.data)
            contact = frappe.get_doc('Contact',data['name']).as_dict()
            frappe.response["message"]={
                'Address': contact
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
    addr = frappe.get_doc('Contact',data['id']).as_dict()
    pprint(data['address'])
    if addr.name:       
        addr.first_name = data['name']
        addr.mobile_no = data['contact']
        addr.address = [{
            'address_title':'Test',
            'address_type':'Office',
            'address_line1':'Testing  12',
            'address_line2':'checking',
            'city':'Bareilly',
            'state':'UP',
            'Country':'India'
        }]
        addr.save(ignore_permissions=True)
        frappe.response["message"] = {
            "success_key":1,
            "message":"Address Edit is successfully Done!"
        }
    else:
        frappe.response["message"] = {
            "success_key":0,
            "message":"Address Edit was not successful"
        }