from .catalogs import catalog_rows
DEFAULT_MASTER_ID='bia-digital-transformation'
def default_master():
    return dict(id=DEFAULT_MASTER_ID,title='BIA Digital Transformation',primaryDepartment='Digital & IT',owner='Transformation office',description='Digital transformation programmes and workstreams.')
def with_masters(s):
    department=next((d['name'] for d in catalog_rows(s) if d['kind']=='department' and d['id']=='department-1'),'Digital & IT')
    masters=[{**m,'primaryDepartment':m.get('primaryDepartment') or (department if m['id']==DEFAULT_MASTER_ID else None)} for m in s.get('masterProjects',[default_master()])]
    return {**s,'masterProjects':masters,'projects':[{**p,'masterId':p.get('masterId') or DEFAULT_MASTER_ID} for p in s['projects']]}
