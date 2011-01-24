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

#Chrome extension
chrome_extension_version = "0.3.5"

if USING_SDK:
    debug_mode = True
else:
    debug_mode = False
    
ranks_page_size = 10
ranks_limit = 10000
short_url_lifespan = 10*60
question_batch_size = 25