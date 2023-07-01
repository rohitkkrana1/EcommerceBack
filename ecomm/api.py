import frappe
import json
from frappe import auth

@frappe.whitelist(allow_guest=True)
def getItems(filter="",limit=10, offset=0):
    str=''
    if filter:
        f = json.loads(filter)
        for fil in f:
            if(fil['operator'].upper() == 'IN'):
                j=','.join(f"""'{x}'""" for x in fil['value'])
                str += f" AND A.`{fil['field']}` {fil['operator']} ({j})"
            elif(fil['operator'].upper() == 'NOT IN'):
                j=','.join(f"""'{x}'""" for x in fil['value'])
                str += f" AND A.`{fil['field']}` {fil['operator']} ({j})"
            elif(fil['operator'].upper() == 'LIKE'):
                 str += f" AND A.`{fil['field']}` {fil['operator']} '%{fil['value']}%'"
            else:
                str += f" AND A.`{fil['field']}` {fil['operator']} '{fil['value']}'"
    
    sql = f"""select A.* from ( select a.*,b.currency,b.price_list_rate, 
GROUP_CONCAT(d.dfp_external_storage_s3_key) AS images, GROUP_CONCAT(DISTINCT e.tag) categories from `tabWebsite Item` a 
left join `tabItem Price` b on a.item_code = b.item_code
LEFT JOIN `tabFile` d ON d.attached_to_doctype='Website Item' and a.name = d.attached_to_name
LEFT JOIN `tabTag Link` e ON  e.document_type = 'Website Item' AND e.`document_name` = a.name
 where a.published=1 
 GROUP BY a.name
 LIMIT {limit} OFFSET {offset} ) A where 1=1 {str}"""  
    result = frappe.db.sql(sql,as_dict=True)
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
def login():
    data = json.loads(frappe.request.data)
    try:
        loginManager = frappe.auth.LoginManager()
        loginManager.authenticate(user= data["username"],pwd= data["password"])
        loginManager.post_login()
    except frappe.exceptions.AuthenticationError:
        frappe.clear_messages()
        frappe.local.response['message'] = {
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
        "username":user.username,
        "email":user.email
    }


def generate_keys(user):
    user = frappe.get_doc('User',user)
    api_secret = frappe.generate_hash(length=25)

    if not user.api_key:
        user.api_key = frappe.generate_hash(length=15)

    user.api_secret = api_secret
    user.save()
    return api_secret


@frappe.whitelist()
def saveCart():
    return 0


@frappe.whitelist()
def getLoginUser():
    return frappe.get_user().doc.name

