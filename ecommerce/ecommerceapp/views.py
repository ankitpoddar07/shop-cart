from django.shortcuts import render,redirect
from ecommerceapp.models import Contact,Product,OrderUpdate,Orders
from django.contrib import messages
from math import ceil
from ecommerceapp import keys
from django.conf import settings
MERCHANT_KEY = 'xxxxxxxxxxxxxxxx'
import json
from django.views.decorators.csrf import  csrf_exempt
from PayTm import Checksum



# Create your views here.
# All products passing in key value pair using Dictionary
def index(request):

    allProds = []
    catprods = Product.objects.values('category','id')
    print(catprods)
    cats = {item['category'] for item in catprods}
    for cat in cats:
        prod= Product.objects.filter(category=cat)
        n=len(prod)
        nSlides = n // 4 + ceil((n / 4) - (n // 4))
        allProds.append([prod, range(1, nSlides), nSlides])

    params= {'allProds':allProds}

    return render(request,"index.html",params)

def contact(request):
    if request.method=="POST":
        name=request.POST.get("name")
        email=request.POST.get("email")
        desc=request.POST.get("desc")
        pnumber=request.POST.get("pnumber")
        myquery=Contact(name=name,email=email,desc=desc,phonenumber=pnumber)
        myquery.save()
        messages.info(request,"Thankyou for your cooperation - We will get back to you soon.. with solution")
        return render(request,"contact.html")


    return render(request,"contact.html")

def about(request):
    return render(request,"about.html")

def blog(request):
    return render(request,"blog.html")

def service(request):
    return render(request,"service.html")


def checkout(request):
    if not request.user.is_authenticated:
        messages.warning(request,"Login & Try Again")
        return redirect('/auth/login')

    if request.method=="POST":
        items_json = request.POST.get('itemsJson', '')
        name = request.POST.get('name', '')
        amount = request.POST.get('amt')
        email = request.POST.get('email', '')
        address1 = request.POST.get('address1', '')
        address2 = request.POST.get('address2','')
        city = request.POST.get('city', '')
        state = request.POST.get('state', '')
        zip_code = request.POST.get('zip_code', '')
        phone = request.POST.get('phone', '')
        Order = Orders(items_json=items_json,name=name,amount=amount, email=email, address1=address1,address2=address2,city=city,state=state,zip_code=zip_code,phone=phone)
        print(amount)
        Order.save()
        update = OrderUpdate(order_id=Order.order_id,update_desc="the order has been placed")
        update.save()
        thank = True

# # # PAYMENT INTEGRATION

        id = Order.order_id
        oid=str(id)+"ShopCart"
        param_dict = {

            'MID':'DIY12386817555599231',
            'ORDER_ID': oid,
            'TXN_AMOUNT': str(amount),
            'CUST_ID': email,
            'INDUSTRY_TYPE_ID': 'Retail',
            'WEBSITE': 'WEBSTAGING',
            'CHANNEL_ID': 'WEB',
            'CALLBACK_URL': 'http://127.0.0.1:8000/handlerequest/',

        }
        param_dict['CHECKSUMHASH'] = Checksum.generate_checksum(param_dict, MERCHANT_KEY)
        return render(request, 'paytm.html', {'param_dict': param_dict})

    return render(request, 'checkout.html')

@csrf_exempt

def handlerequest(request):
    # Paytm will send a POST request here
    if request.method == 'POST':
        form = request.POST
        response_dict = {key: form[key] for key in form.keys()}
        checksum = form.get('CHECKSUMHASH', None)  # Initialize checksum to None

        print("Paytm Response:", response_dict)

        # Populate response_dict and extract checksum
        for key in form.keys():
            response_dict[key] = form[key]
            if key == 'CHECKSUMHASH':
                checksum = form[key]

        # Verify checksum
        if checksum is None:
            print("Checksum not found in response.")
            return render(request, 'paymentstatus.html', {'response': {'RESPMSG': 'Checksum not found'}})

        MERCHANT_KEY = 'xxxxxxxxxxxxxxxx'  # Replace with your actual merchant key

        try:
            verify = Checksum.verify_checksum(response_dict, MERCHANT_KEY, checksum)
            if verify:
                if response_dict.get('RESPCODE') == '01':  # Check if payment was successful
                    print('Order successful')

                    # Extract order details
                    order_id = response_dict.get('ORDERID', '')
                    txn_amount = response_dict.get('TXNAMOUNT', '')

                    if order_id and txn_amount:
                        # Remove "ShopyCart" prefix from order_id
                        rid = order_id.replace("ShopyCart", "")

                        # Fetch the order from the database
                        filter2 = Orders.objects.filter(order_id=rid)
                        if filter2.exists():
                            for order in filter2:
                                order.oid = order_id
                                order.amountpaid = txn_amount
                                order.paymentstatus = "PAID"
                                order.save()
                            print("Order updated successfully.")
                        else:
                            print("No matching order found.")
                    else:
                        print("Missing ORDERID or TXNAMOUNT in response.")
                else:
                    print('Order was not successful because:', response_dict.get('RESPMSG', 'Unknown error'))
            else:
                print('Checksum verification failed.')
        except Exception as e:
            print(f"Error during checksum verification or order update: {str(e)}")

        # Render the payment status page with the response
        return render(request, 'paymentstatus.html', {'response': response_dict})
    else:
        return render(request, 'paymentstatus.html', {'response': {'RESPMSG': 'Invalid request method'}})



def profile(request):
    if not request.user.is_authenticated:
        messages.warning(request, "Login & Try Again")
        return redirect('/auth/login')
    
    currentuser = request.user.username
    items = Orders.objects.filter(email=currentuser)
    rid = None  
    
    for i in items:
        myid = i.oid
        if myid:
            rid = myid.replace("ShopCart", "")
            if rid.isdigit():
                break


    if not rid or not rid.isdigit():
        messages.error(request, "No valid order ID found.")
        return render(request, "profile.html", {"items": items, "status": None})
    
    try:
        status = OrderUpdate.objects.filter(order_id=int(rid))
    except ValueError:
        messages.error(request, "Invalid Order ID format.")
        return render(request, "profile.html", {"items": items, "status": None})


    for j in status:
        print(j.update_desc)
    
    context = {"items": items, "status": status}
    return render(request, "profile.html", context)
