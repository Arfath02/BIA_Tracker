#!/usr/bin/env python3
"""Run explicit schema migration with a separate, short-lived DDL login."""
import getpass,json,os,subprocess
from pathlib import Path
from urllib.parse import urlsplit,urlunsplit,quote

def main():
    os.chdir(Path(__file__).resolve().parent.parent)
    compose=['docker','compose','--env-file','deploy/.env','-f','deploy/compose.yaml']
    config=json.loads(subprocess.check_output(compose+['config','--format','json'],text=True))
    runtime=urlsplit(config['services']['api']['environment']['DATABASE_URL'])
    print('Schema installation/upgrade targets the configured dedicated BIA database.')
    username=input('Migration SQL login (DDL permissions): ').strip();password=getpass.getpass('Migration SQL password: ')
    if not username or not password: raise SystemExit('Both credentials are required. No schema changes made.')
    host=runtime.netloc.rsplit('@',1)[-1]
    url=urlunsplit(runtime._replace(netloc=quote(username,safe='')+':'+quote(password,safe='')+'@'+host))
    env=os.environ.copy();env['DATABASE_URL']=url
    subprocess.run(compose+['run','--rm','-e','DATABASE_URL','api','python','-m','production.manage','upgrade'],env=env,check=True)
if __name__=='__main__': main()
