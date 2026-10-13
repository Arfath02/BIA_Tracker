#!/usr/bin/env python3
"""Create a private Compose environment file; no database/network operations."""
import getpass,ipaddress,os,re
from pathlib import Path
from urllib.parse import quote,urlencode,urlsplit

def connection_url(server,port,database,username,password):
    host='['+server+']' if ':' in server else server
    return f'mssql+pyodbc://{quote(username,safe="")}:{quote(password,safe="")}@{host}:{port}/{quote(database,safe="")}?'+urlencode({'driver':'ODBC Driver 18 for SQL Server','Encrypt':'yes','TrustServerCertificate':'no','Connection Timeout':'15'})
def ask(label,default=None):
    while True:
        value=input(label+(f' [{default}]' if default else '')+': ').strip() or default
        if value and not any(c in value for c in '\n\r\x00'): return value
        print('Enter a value.')
def main():
    destination=Path(__file__).resolve().parent/'.env'
    if destination.exists(): raise SystemExit('deploy/.env already exists. Keep it, or move it to a secure backup before configuring again.')
    print('BIA setup — writes local configuration only. Use a dedicated application database.')
    server=ask('SQL Server DNS name (must match its TLS certificate)');port=ask('SQL TCP port','1433')
    if not port.isdigit() or not 1<=int(port)<=65535: raise SystemExit('Invalid SQL port.')
    if not re.fullmatch(r'[A-Za-z0-9.:-]+',server): raise SystemExit('Use a DNS name or IP, without a SQL instance suffix. Enter the instance TCP port separately.')
    database=ask('Database','BIA_Transformation');username=ask('Runtime SQL login');password=getpass.getpass('Runtime SQL password: ')
    if not password or '\n' in password or '\r' in password: raise SystemExit('Invalid password.')
    origin=ask('Application HTTPS origin','https://bia.internal:8443').rstrip('/');parts=urlsplit(origin)
    if parts.scheme!='https' or not parts.hostname or parts.path or parts.query or parts.fragment or parts.username: raise SystemExit('Enter only an HTTPS origin, e.g. https://bia.company.local:8443')
    app_port=parts.port or 443
    bind=ask('Listen IPv4 (use LAN IP only when ready to enable LAN access)','127.0.0.1');ipaddress.IPv4Address(bind)
    tls=Path(ask('Absolute TLS directory containing fullchain.pem and privkey.pem')).expanduser()
    if not tls.is_absolute() or not all((tls/name).is_file() for name in ['fullchain.pem','privkey.pem']): raise SystemExit('TLS files not found. Obtain your application certificate before configuring.')
    values={'DATABASE_URL':connection_url(server,port,database,username,password),'TRUSTED_ORIGINS':origin,'BIND_IP':bind,'APP_PORT':str(app_port),'TLS_DIRECTORY':str(tls)}
    # Single-quoted Compose .env values are literal. Never interpret a password as shell code.
    content='\n'.join(k+"='"+v.replace('\\','\\\\').replace("'","\\'")+"'" for k,v in values.items())+'\n'
    fd=os.open(destination,os.O_WRONLY|os.O_CREAT|os.O_EXCL,0o600)
    with os.fdopen(fd,'w') as file:file.write(content)
    print('Configuration saved. Continue with: bash deploy/setup.sh')
if __name__=='__main__': main()
