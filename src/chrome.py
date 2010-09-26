import os, globals, logging
from google.appengine.ext import webapp
from google.appengine.ext.webapp import template
from google.appengine.ext.webapp.util import run_wsgi_app
from google.appengine.ext.db import GqlQuery
from array import array
from StringIO import StringIO
from zipfile import ZipFile, ZIP_DEFLATED
from tlslite.utils.cryptomath import bytesToString
import urllib
import cgi
from short_urls import ShortUrls
from rsa_key import RSAKey
	
class ChromeHandler(webapp.RequestHandler):
	def get(self, user_secret):		
		def generate_update_xml(appid, codebase):
			path = os.path.join(os.path.dirname(__file__), './static/chrome/update.xml')
			template_values = { 
								'version': globals.chrome_extension_version, 
								'url': codebase,
								'appid': appid
								}
			
			manifest = template.render(path, template_values) 
			return manifest
				
		def build_zip(domain):
			def generate_manifest():
				path = os.path.join(os.path.dirname(__file__), './static/chrome/manifest.json')
				#q&d
				index1 = domain.rfind('://')
				index2 = domain.rfind(':')
				naked_domain = domain[:index2] if index1 != index2 else domain
				
				if naked_domain[:-1] != '/':
					naked_domain += '/'
					
				template_values = { 
									'version': globals.chrome_extension_version, 
									'update_url': self.request.url,
									'base_url': naked_domain 
									}
				
				manifest = template.render(path, template_values) 
				return manifest
		
			def generate_followLink():
				path = os.path.join(os.path.dirname(__file__), './static/chrome/followLink.js')
				template_values = { 
									'domain': domain, 
									'token': user_secret
									}
				
				manifest = template.render(path, template_values) 
				return manifest
				
			path = os.path.join(os.path.dirname(__file__), "./static/chrome/")
			zip_data = StringIO()
			try:
				zip = ZipFile(zip_data, "w", ZIP_DEFLATED)
		
				zip.write(os.path.join(path, "icon48.png"), "icon48.png")
				zip.write(os.path.join(path, "icon16.png"), "icon16.png")
				zip.write(os.path.join(path, "icon128.png"), "icon128.png")
				zip.write(os.path.join(path, "icon32.png"), "icon32.png")
				zip.write(os.path.join(path, "jquery.min.js"), "jquery.min.js")
		
				zip.writestr("followLink.js", generate_followLink())				
				zip.writestr("manifest.json", generate_manifest())
	
				zip.close()
				
				return zip_data.getvalue()
			finally:
				zip_data.close();
	
		
		def sign_zip(zip):	
			private_key = RSAKey.get_private_key()
			return private_key.hashAndSign(zip) 
				
		def build_header(signature, derkey):
			logging.info("der key size %d", len(derkey))
			header = array("i");
			header.append(2); # Version 2
			header.append(len(derkey));
			header.append(len(signature));
			return header.tostring()
		
		query = GqlQuery("SELECT * FROM FollowerId WHERE secret = :1", user_secret).fetch(1)
				
		if len(query) == 0:
			self.response.out.write("invalid token");
			self.response.set_status(401)
			return
		
		follower_id = query[0]

		update_check = True if "x" in self.request.GET else False   
		
		domain = self.request.url[:self.request.url.find(self.request.path)]
					
		if update_check:
			update_params = urllib.unquote(self.request.GET["x"])
			update_params = cgi.parse_qs(update_params)
			
			codebase = domain + ShortUrls.build_full_url(follower_id)
			
			update_xml = generate_update_xml(update_params["id"][0], codebase)
			self.response.headers['Content-Type'] = 'text/xml'
			self.response.out.write(update_xml);
			return
		
		zip_only = True if "zip" in self.request.GET else False
	
		zip = build_zip(domain)
		if zip_only:
			self.response.headers['Content-Type'] = 'application/octet-stream'
			self.response.headers['Content-disposition'] = '"inline; filename=stackguru.zip'	
		else:
			derkey = RSAKey.get_public_as_der()
			signed_zip = bytesToString(sign_zip(zip))		
			self.response.headers['Content-Type'] = 'application/x-chrome-extension'
			self.response.headers['Content-disposition'] = '"inline; filename=stackguru.crx'
		
			self.response.out.write("Cr24") # Extension file magic number
			self.response.out.write(build_header(signed_zip, derkey))
			self.response.out.write(derkey);
			self.response.out.write(signed_zip);
			
		self.response.out.write(zip);
		
application = webapp.WSGIApplication([("/chrome/(.*)", ChromeHandler)], debug=globals.debug_mode)

def main():
	run_wsgi_app(application)

if __name__ == "__main__":
	main()
