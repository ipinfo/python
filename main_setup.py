#pip install ipinfo
import ipinfo
import pprint
access_token = str(input("your token from ipinfo.io : "))
handler = ipinfo.getHandler(access_token)
ip_address = str(input("your ipaddress : "))
details = handler.getDetails(ip_address)
pprint.pprint(details.all)
