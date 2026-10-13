"""Master data shared by validation, installation and migration."""
DEFAULT_DEPARTMENTS=['Digital & IT','Warehouse','Production','Quality','HR','Engineering']
KINDS={'department','vendor','resource'}
def catalog_rows(s):
    if 'catalogs' in s: return s['catalogs']
    values={'department':DEFAULT_DEPARTMENTS+[x.get('primaryDepartment') for x in s.get('masterProjects',[])]+[x['department'] for x in s.get('users',[])]+[x['department'] for x in s.get('projects',[])], 'vendor':[x['vendor'] for x in s.get('pos',[])], 'resource':['Unassigned']+[x['resource'] for x in s.get('tasks',[])]}
    return [dict(id=f'{kind}-{i+1}',kind=kind,name=name,active=True) for kind,names in values.items() for i,name in enumerate(dict.fromkeys(n for n in names if n))]
def allowed(s,kind,name,current=None):
    return isinstance(name,str) and bool(name) and (name==current or any(x['kind']==kind and x['active'] and x['name']==name for x in catalog_rows(s)))
