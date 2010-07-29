import os

server_software = os.getenv('SERVER_SOFTWARE')
USING_SDK = not server_software or server_software.startswith('Dev')
del server_software

if USING_SDK:
    default_domain = 'meta.stackoverflow.com'
else:
    default_domain = 'stackoverflow.com'
    
#You need to get a bit.ly api key at http://bit.ly/a/your_api_key
bitly_api_key = PUT-YOUR-BIT.LY-API-KEY-HERE
bitly_login = PUT-YOUR-BIT.LY-LOGIN-NAME-HERE

#You need to get a Google API Key at http://code.google.com/apis/ajaxsearch/signup.html
google_api_key = PUT-YOUR-GOOGLE-API-KEY-HERE
#You need to get stack apps api key at http://stackapps.com/apps/register
stack_api_key = PUT-YOU-STACK-APPS-KEY-HERE
max_follow_tags = 10

if USING_SDK:
    debug_mode = True
else:
    debug_mode = False
    
ranks_page_size = 10
ranks_limit = 10000

domain_alias = {
                'so': 'stackoverflow.com', 
                'sf': 'serverfault.com', 
                'su': 'superuser.com',
                'meta': 'meta.stackoverflow.com',
                'stackoverflow': 'stackoverflow.com', 
                'stackoverflow.com': 'stackoverflow.com',
                'www.stackoverflow.com': 'stackoverflow.com',
                'serverfault': 'serverfault.com', 
                'serverfault.com': 'serverfault.com',
                'www.serverfault.com': 'serverfault.com',
                'superuser': 'superuser.com', 
                'superuser.com': 'superuser.com',
                'www.superuser.com': 'superuser.com',
                'meta.stackoverflow.com': 'meta.stackoverflow.com',
                'stackapps': 'stackapps.com', 
                'stackapps.com': 'stackapps.com',
                'www.stackapps.com': 'stackapps.com',
                }