"""Regression tests for kitchen roles, temperature provenance and complete backups.

Reads Python functions out of the actual assembled release using AST. All
database calls use deterministic in-memory stubs; never contacts a real DB.
"""
import ast
import copy
import json
from pathlib import Path
from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo

APP=Path("app")


def fn(path,name,namespace):
    source=Path(path).read_text(encoding="utf-8")
    tree=ast.parse(source)
    node=next((n for n in tree.body if isinstance(n,(ast.FunctionDef,ast.AsyncFunctionDef)) and n.name==name),None)
    assert node is not None,(path,name)
    ns=dict(namespace)
    exec(compile(ast.Module(body=[node],type_ignores=[]),str(path),"exec"),ns)
    return ns[name]


def safety_guards():
    src=APP/"auth_controls.py"
    canon=lambda v:json.dumps(v,ensure_ascii=False,sort_keys=True,separators=(',',':'))
    protected=fn(src,"_cdc_protected_state_change",{"_canon":canon})
    original={
        "managerSignoffs":[{"id":"sig1","by":"Manager","date":"2026-10-13"}],
        "recipes":[
            {"id":"r1","name":"Fish Pie","method":"Heat", "allergens":"Milk",
             "allergenVerified":False,"allergenReviewRequired":True,
             "ingredients":[{"name":"Milk","qty":100,"unit":"ml","stockId":"s1",
                             "allergens":["Milk"],"allergenVerified":True,"allergenSource":"manager-edit"},
                            {"name":"Potatoes","qty":400,"unit":"g","allergenVerified":False}]},
            {"id":"r2","name":"Soup","method":"Heat","ingredients":[{"name":"Carrots","qty":10,"unit":"g"}]}
        ],
        "stock":[{"id":"s1","item":"Milk","qtyKnown":False,"allergenVerified":False}]
    }
    clean=copy.deepcopy(original)
    clean["stock"][0]["qtyKnown"]=True
    clean["stock"][0]["qty"]=6
    clean["recipes"][1]["method"]="Simmer gently"
    assert protected(original,clean)=="", "Unrelated stock count and draft recipe work should be allowed"
    mutations=[
        lambda d:d["managerSignoffs"].clear(),
        lambda d:d["recipes"][0]["ingredients"][0].update({"allergens":[]}),
        lambda d:d["recipes"][0]["ingredients"].pop(0),
        lambda d:d["recipes"][0].update({"allergenVerified":True}),
        lambda d:d["recipes"][0].update({"allergens":"Milk, Nuts"}),
        lambda d:d["stock"][0].update({"allergenVerified":True}),
        lambda d:d["recipes"][1]["ingredients"][0].update({"allergenSource":"manager-edit","allergenVerified":True})
    ]
    for change in mutations:
        tampered=copy.deepcopy(original)
        change(tampered)
        reason=protected(original,tampered)
        assert reason and "manager" in reason.lower(),(change,reason)
    auth=src.read_text()
    assert "if user.get('role') != 'manager':\n                protected_error=_cdc_protected_state_change" in auth
    assert "if user.get('role')=='manager' else 0" in auth
    assert "incoming['users']=current['state'].get('users',[])" in auth
    print("PASS: server rejects forged allergen approvals and manager sign-offs; normal staff data remains editable")


class FakeCur:
    def __init__(self,rows=None):
        self.queries=[]
        self.rows=rows
        self.nextrow=None
        self.inserts=[]
    def __enter__(self):return self
    def __exit__(self,*args):pass
    def execute(self,sql,args=None):
        self.queries.append((sql,args))
        if "FROM tenant_temperature_readings" in sql and sql.lstrip().upper().startswith("SELECT"):
            self.nextrow=None
        if "INSERT INTO tenant_temperature_readings" in sql:
            venue,id,app_id,val,ts,period,by,source,payload=args
            self.inserts.append(json.loads(payload))
            self.nextrow={"id":id,"app_id":app_id,"value":val,"ts":datetime.fromisoformat(ts.replace("Z","+00:00")),
                          "period":period,"recorded_by":by,"source":source,"payload":json.loads(payload)}
    def fetchone(self):
        return self.nextrow
    def fetchall(self):return self.rows or []


class FakeConn:
    def __init__(self,rows=None):
        self.cursor_instance=FakeCur(rows)
    def __enter__(self):return self
    def __exit__(self,*args):pass
    def cursor(self):return self.cursor_instance
    def commit(self):pass
    def rollback(self):pass


class FakeApp:
    def __init__(self,rows=None):
        self.conn=FakeConn(rows)
    def connect(self):return self.conn


class Handler:
    def __init__(self,role):
        self.role=role;self.response=None
    def require_user(self):
        return {"state":{"appliances":[{"id":"fridge_1"}]},"revision":1}, \
               {"role":self.role,"username":"staff1" if self.role=="staff" else "chef","tenantId":"venue_1"}
    def send_json(self,value,status=200):
        self.response=(status,value)


def temp_guards():
    src=APP/"temperature_store.py"
    txt=src.read_text()
    tz=ZoneInfo("Europe/London")
    env={"datetime":datetime,"_LONDON":tz,"json":json,
         "VALID_EQUIPMENT_STATUSES":{"reading","out_of_order","not_in_use","defrosting","awaiting_repair"},
         "_slot_day":lambda v:datetime.fromisoformat(str(v).replace("Z","+00:00")).astimezone(tz).date().isoformat(),
         "_public_row":lambda r:{"id":r["id"],"value":r["value"],"source":r["source"],"by":r["recorded_by"]}}
    def make(role,when,id="temperature_1"):
        app=FakeApp()
        namespace={**env,"app":app}
        method=fn(src,"append_readings",namespace)
        h=Handler(role)
        row={"id":id,"appId":"fridge_1","ts":when.isoformat(),
             "period":"AM" if when.hour<12 else "PM",
             "value":4.0,"source":"manager-backfill","by":"spoofed_other_user"}
        method(h,{"readings":[row]})
        return h,app
    last_week=datetime.now(tz)-timedelta(days=7)
    h,app=make("staff",last_week)
    assert h.response[0]==403 and not app.conn.cursor_instance.inserts
    h,app=make("manager",last_week)
    assert h.response[0]==200 and len(app.conn.cursor_instance.inserts)==1
    current=datetime.now(tz)-timedelta(minutes=1)
    h,app=make("staff",current)
    assert h.response[0]==200 and len(app.conn.cursor_instance.inserts)==1,h.response
    saved=app.conn.cursor_instance.inserts[0]
    assert saved["by"]=="staff1" and saved["source"]=="manual",saved
    h=Handler("staff");app=FakeApp()
    deleter=fn(src,"delete_reading",{**env,"app":app})
    deleter(h,{"id":"temp_1"})
    assert h.response[0]==403 and not app.conn.cursor_instance.queries
    assert "if user.get('role') != 'manager':" in txt and "correct_round" in txt
    print("PASS: staff can log today's reading, cannot backdate/delete, and cannot spoof recorded by/source")


def backups():
    src=Path("supabase_storage_override_mt.py")
    when=datetime(2026,10,19,8,0,tzinfo=timezone.utc)
    sample=[
        {"id":"t1","app_id":"fridge_1","value":4.3,"ts":when,"period":"AM","recorded_by":"chef",
         "source":"manual","payload":{"equipmentStatus":"reading","notes":""}},
        {"id":"t2","app_id":"fridge_1","value":None,"ts":when+timedelta(hours=8),"period":"PM",
         "recorded_by":"chef","source":"manual-status","payload":{"equipmentStatus":"awaiting_repair","notes":"Engineer booked"}}
    ]
    app=FakeApp(sample)
    backup=fn(src,"_backup_payload",{"app":app,"json":json,"datetime":datetime,"timezone":timezone})
    old={"settings":{"venueId":"venue_1"},"tempReadings":[],"recipes":[{"id":"r1","name":"Soup"}]}
    saved=json.loads(backup(old,42))
    assert old["tempReadings"]==[],"Backup hydration must not mutate live state"
    assert saved["revision"]==42 and saved["backupFormat"]==2
    assert saved["temperatureReadingCount"]==2
    assert saved["state"]["recipes"]==old["recipes"]
    assert saved["state"]["tempReadings"][0]["value"]==4.3
    assert saved["state"]["tempReadings"][1]["value"] is None
    assert saved["state"]["tempReadings"][1]["equipmentStatus"]=="awaiting_repair"
    assert app.conn.cursor_instance.queries[0][1]==("venue_1",)
    print("PASS: complete venue backups include both measured and status-only authoritative temperatures")


if __name__=="__main__":
    safety_guards()
    temp_guards()
    backups()
