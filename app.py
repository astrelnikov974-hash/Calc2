import os, sys, json, sqlite3, hashlib, secrets, threading, queue, datetime as dt, time, shutil, re, xml.etree.ElementTree as ET
from pathlib import Path
import tkinter as tk
from tkinter import ttk, messagebox, filedialog

BASE=Path(__file__).resolve().parent
DB=BASE/"axus_treolan.db"
SEED=BASE/"seed_catalog.json"
EXPORT_SOURCE=BASE/"data.xlsx"
SETTINGS=BASE/"settings.json"
BACKUPS=BASE/"backups"; BACKUPS.mkdir(exist_ok=True)

DEFAULT_SETTINGS={"treolan_login":"","treolan_password":"","wsdl":"https://api.treolan.ru/webservices/treolan.wsdl","interval":60,"last_sync":""}

def now(): return dt.datetime.now().strftime("%d.%m.%Y %H:%M:%S")
def norm(x): return "" if x is None else str(x).strip()

def db():
    c=sqlite3.connect(DB,check_same_thread=False)
    c.row_factory=sqlite3.Row
    return c

def init_db():
    c=db()
    c.execute("""CREATE TABLE IF NOT EXISTS users(
      id INTEGER PRIMARY KEY, login TEXT UNIQUE NOT NULL, salt TEXT NOT NULL, pwd_hash TEXT NOT NULL
    )""")
    c.execute("""CREATE TABLE IF NOT EXISTS products(
      id INTEGER PRIMARY KEY, sheet TEXT, model TEXT, vendor TEXT, type TEXT, color TEXT,
      article TEXT UNIQUE, brand TEXT, resource TEXT, price TEXT, stock TEXT, transit TEXT,
      updated_at TEXT
    )""")
    c.execute("""CREATE TABLE IF NOT EXISTS sync_log(
      id INTEGER PRIMARY KEY, started_at TEXT, finished_at TEXT, status TEXT, updated INTEGER, missed INTEGER, error TEXT
    )""")
    if c.execute("SELECT COUNT(*) FROM users").fetchone()[0]==0:
        salt=secrets.token_hex(16); pwd=hashlib.pbkdf2_hmac("sha256",b"admin",salt.encode(),200_000).hex()
        c.execute("INSERT INTO users(login,salt,pwd_hash) VALUES(?,?,?)",("admin",salt,pwd))
    if c.execute("SELECT COUNT(*) FROM products").fetchone()[0]==0 and SEED.exists():
        data=json.loads(SEED.read_text(encoding="utf-8"))
        c.executemany("""INSERT OR IGNORE INTO products
          (sheet,model,vendor,type,color,article,brand,resource,price,stock,transit,updated_at)
          VALUES(?,?,?,?,?,?,?,?,?,?,?,?)""",
          [(x.get("sheet",""),x.get("model",""),x.get("vendor",""),x.get("type",""),x.get("color",""),
            x.get("article",""),x.get("brand",""),x.get("resource",""),x.get("price",""),x.get("stock",""),
            x.get("transit",""),now()) for x in data])
    c.commit(); c.close()

def load_settings():
    if SETTINGS.exists():
        try: return {**DEFAULT_SETTINGS,**json.loads(SETTINGS.read_text(encoding="utf-8"))}
        except: pass
    return DEFAULT_SETTINGS.copy()
def save_settings(s): SETTINGS.write_text(json.dumps(s,ensure_ascii=False,indent=2),encoding="utf-8")

def verify_user(login,password):
    c=db(); r=c.execute("SELECT salt,pwd_hash FROM users WHERE login=?",(login,)).fetchone(); c.close()
    if not r:return False
    h=hashlib.pbkdf2_hmac("sha256",password.encode(),r["salt"].encode(),200_000).hex()
    return secrets.compare_digest(h,r["pwd_hash"])

class Login(tk.Toplevel):
    def __init__(self,parent,on_ok):
        super().__init__(parent); self.on_ok=on_ok; self.title("AXUS GROUP • Вход"); self.geometry("430x330"); self.resizable(False,False)
        self.configure(bg="#f3f5f7"); self.protocol("WM_DELETE_WINDOW",parent.destroy)
        f=tk.Frame(self,bg="white",padx=35,pady=30); f.place(relx=.5,rely=.5,anchor="center",width=370,height=260)
        tk.Label(f,text="AXUS GROUP",font=("Arial",18,"bold"),bg="white",fg="#101820").pack(anchor="w")
        tk.Label(f,text="Treolan Manager",font=("Arial",10),bg="white",fg="#69737d").pack(anchor="w",pady=(2,24))
        tk.Label(f,text="Логин",bg="white",fg="#4c5660").pack(anchor="w"); self.login=ttk.Entry(f); self.login.pack(fill="x",pady=(4,12)); self.login.insert(0,"admin")
        tk.Label(f,text="Пароль",bg="white",fg="#4c5660").pack(anchor="w"); self.pwd=ttk.Entry(f,show="•"); self.pwd.pack(fill="x",pady=(4,16)); self.pwd.bind("<Return>",lambda e:self.go())
        ttk.Button(f,text="Войти",command=self.go).pack(fill="x")
        self.transient(parent); self.grab_set(); self.login.focus()
    def go(self):
        if verify_user(self.login.get().strip(),self.pwd.get()):
            self.destroy(); self.on_ok(self.login.get().strip())
        else: messagebox.showerror("Вход","Неверный логин или пароль",parent=self)

class App(tk.Tk):
    def __init__(self):
        super().__init__(); self.withdraw(); self.title("AXUS GROUP • Treolan Manager"); self.geometry("1240x760"); self.minsize(1000,650)
        self.q=queue.Queue(); self.settings=load_settings(); init_db()
        self.after(100,self.login)
    def login(self):
        Login(self,lambda user:self.show_main(user))
    def show_main(self,user):
        self.deiconify(); self.user=user; self.build(); self.refresh(); self.after(1000,self.poll); self.after(5000,self.auto_sync)
    def build(self):
        style=ttk.Style(self); style.theme_use("clam")
        style.configure("Treeview",rowheight=30,font=("Arial",10),background="white",fieldbackground="white")
        style.configure("Treeview.Heading",font=("Arial",10,"bold"),background="#101820",foreground="white")
        style.configure("TButton",padding=(12,8))
        self.grid_columnconfigure(1,weight=1); self.grid_rowconfigure(1,weight=1)
        side=tk.Frame(self,bg="#fff",width=235); side.grid(row=0,column=0,rowspan=2,sticky="nsew"); side.grid_propagate(False)
        tk.Label(side,text="AXUS GROUP",font=("Arial",18,"bold"),bg="white",fg="#101820").pack(anchor="w",padx=24,pady=(28,2))
        tk.Label(side,text="TREOLAN MANAGER",font=("Arial",9,"bold"),bg="white",fg="#0b63f6").pack(anchor="w",padx=24,pady=(0,30))
        self.nav=[]
        for name,cmd in [("Обзор",self.dashboard),("Каталог",self.catalog),("Синхронизация",self.sync_page),("Настройки",self.settings_page)]:
            b=tk.Button(side,text=name,command=cmd,anchor="w",bd=0,bg="white",fg="#505a64",font=("Arial",10),padx=24,pady=11,activebackground="#edf4ff")
            b.pack(fill="x"); self.nav.append(b)
        tk.Label(side,text=f"Вход: {self.user}",bg="white",fg="#8a929a",font=("Arial",9)).pack(side="bottom",anchor="w",padx=24,pady=20)
        self.main=tk.Frame(self,bg="#f4f6f8"); self.main.grid(row=0,column=1,rowspan=2,sticky="nsew"); self.main.grid_columnconfigure(0,weight=1); self.main.grid_rowconfigure(1,weight=1)
        self.status=tk.StringVar(value="Готово")
        self.dashboard()
    def clear(self):
        for w in self.main.winfo_children(): w.destroy()
    def header(self,title,sub):
        f=tk.Frame(self.main,bg="#f4f6f8"); f.grid(row=0,column=0,sticky="ew",padx=30,pady=(25,15))
        tk.Label(f,text=title,font=("Arial",26,"bold"),bg="#f4f6f8",fg="#101820").pack(anchor="w")
        tk.Label(f,text=sub,font=("Arial",10),bg="#f4f6f8",fg="#737d87").pack(anchor="w",pady=(4,0))
    def card(self,parent,title,value):
        f=tk.Frame(parent,bg="white",highlightbackground="#e2e6ea",highlightthickness=1); f.pack(side="left",fill="both",expand=True,padx=(0,12))
        tk.Label(f,text=title,bg="white",fg="#7a838c",font=("Arial",9)).pack(anchor="w",padx=16,pady=(15,4))
        tk.Label(f,text=value,bg="white",fg="#101820",font=("Arial",20,"bold")).pack(anchor="w",padx=16,pady=(0,15))
    def dashboard(self):
        self.clear(); self.header("Treolan Manager","Управление каталогом AXUS GROUP")
        stats=tk.Frame(self.main,bg="#f4f6f8"); stats.grid(row=1,column=0,sticky="new",padx=30)
        c=db(); total=c.execute("SELECT COUNT(*) FROM products").fetchone()[0]; price=c.execute("SELECT COUNT(*) FROM products WHERE TRIM(COALESCE(price,''))<>''").fetchone()[0]; stock=c.execute("SELECT COUNT(*) FROM products WHERE TRIM(COALESCE(stock,'')) NOT IN ('','0','0.0')").fetchone()[0]; last=self.settings.get("last_sync") or "—"; c.close()
        self.card(stats,"ТОВАРОВ",f"{total:,}".replace(","," ")); self.card(stats,"С ЦЕНОЙ",f"{price:,}".replace(","," ")); self.card(stats,"В НАЛИЧИИ",f"{stock:,}".replace(","," ")); self.card(stats,"ПОСЛЕДНЕЕ ОБНОВЛЕНИЕ",last)
        p=tk.Frame(self.main,bg="white",highlightbackground="#e2e6ea",highlightthickness=1); p.grid(row=2,column=0,sticky="nsew",padx=30,pady=(15,30)); self.main.grid_rowconfigure(2,weight=1)
        tk.Label(p,text="Состояние",font=("Arial",14,"bold"),bg="white").pack(anchor="w",padx=20,pady=(18,5))
        tk.Label(p,text="Приложение работает локально. Treolan-логин и пароль хранятся на этом компьютере и не выводятся в интерфейс.",font=("Arial",10),bg="white",fg="#68737d",wraplength=850).pack(anchor="w",padx=20,pady=5)
        ttk.Button(p,text="Обновить сейчас",command=self.start_sync).pack(anchor="w",padx=20,pady=18)
    def catalog(self):
        self.clear(); self.header("Каталог","Поиск по 2 500+ позициям из исходного Excel и данным Treolan")
        top=tk.Frame(self.main,bg="#f4f6f8"); top.grid(row=1,column=0,sticky="ew",padx=30); self.main.grid_rowconfigure(1,weight=1)
        q=tk.StringVar(); e=ttk.Entry(top,textvariable=q); e.pack(side="left",fill="x",expand=True); e.insert(0,""); ttk.Button(top,text="Найти",command=lambda:fill()).pack(side="left",padx=8); ttk.Button(top,text="Экспорт Excel",command=self.export_excel).pack(side="left")
        frame=tk.Frame(self.main,bg="white",highlightbackground="#e2e6ea",highlightthickness=1); frame.grid(row=2,column=0,sticky="nsew",padx=30,pady=(12,25)); frame.grid_rowconfigure(0,weight=1); frame.grid_columnconfigure(0,weight=1)
        cols=("model","vendor","type","color","article","brand","resource","price","stock","transit")
        tree=ttk.Treeview(frame,columns=cols,show="headings"); tree.grid(row=0,column=0,sticky="nsew"); sb=ttk.Scrollbar(frame,orient="vertical",command=tree.yview); sb.grid(row=0,column=1,sticky="ns"); tree.configure(yscrollcommand=sb.set)
        names=["Модель","Производитель","Тип","Цвет","Артикул","Бренд","Ресурс","Цена","Остаток","Транзит"]
        for c,n in zip(cols,names): tree.heading(c,text=n); tree.column(c,width=110,anchor="w")
        tree.column("article",width=140); tree.column("model",width=180); tree.column("vendor",width=140)
        def fill():
            for x in tree.get_children(): tree.delete(x)
            term=q.get().strip().lower(); c=db()
            if term:
                rows=c.execute("""SELECT * FROM products WHERE lower(model||' '||vendor||' '||type||' '||color||' '||article||' '||brand) LIKE ? LIMIT 1000""",(f"%{term}%",)).fetchall()
            else: rows=c.execute("SELECT * FROM products LIMIT 1000").fetchall()
            for r in rows: tree.insert("", "end",values=tuple(r[k] for k in cols))
            c.close()
        fill()
    def sync_page(self):
        self.clear(); self.header("Синхронизация","Фоновое обновление цен, наличия и транзита через Treolan API")
        p=tk.Frame(self.main,bg="white",highlightbackground="#e2e6ea",highlightthickness=1); p.grid(row=1,column=0,sticky="nsew",padx=30,pady=(0,30)); p.grid_rowconfigure(1,weight=1); p.grid_columnconfigure(0,weight=1)
        self.progress=ttk.Progressbar(p,mode="indeterminate"); self.progress.grid(row=0,column=0,sticky="ew",padx=20,pady=(20,10)); ttk.Button(p,text="Запустить синхронизацию",command=self.start_sync).grid(row=0,column=1,padx=20,pady=20)
        self.log=tk.Text(p,bg="#101820",fg="#dce5ed",font=("Consolas",10),bd=0,padx=14,pady=14); self.log.grid(row=1,column=0,columnspan=2,sticky="nsew",padx=20,pady=(0,20)); self.log.insert("end","Готово.\\n")
    def settings_page(self):
        self.clear(); self.header("Настройки","Доступ к Treolan хранится локально в защищённом файле настроек")
        f=tk.Frame(self.main,bg="white",highlightbackground="#e2e6ea",highlightthickness=1); f.grid(row=1,column=0,sticky="nw",padx=30,pady=0); 
        fields=[("Treolan login","treolan_login",False),("Treolan password","treolan_password",True),("WSDL","wsdl",False),("Интервал, минут","interval",False)]
        self.vars={}
        for i,(lab,key,pwd) in enumerate(fields):
            tk.Label(f,text=lab,bg="white",fg="#56616b").grid(row=i,column=0,sticky="w",padx=20,pady=(18,5))
            v=tk.StringVar(value=str(self.settings.get(key,""))); self.vars[key]=v
            ent=ttk.Entry(f,textvariable=v,show="•" if pwd else ""); ent.grid(row=i,column=1,sticky="ew",padx=(0,20),pady=(18,5),ipadx=100)
        ttk.Button(f,text="Сохранить",command=self.save_cfg).grid(row=5,column=1,sticky="e",padx=20,pady=22)
        tk.Label(f,text="По умолчанию WSDL: https://api.treolan.ru/webservices/treolan.wsdl",bg="white",fg="#7a838c").grid(row=6,column=0,columnspan=2,sticky="w",padx=20,pady=(0,20))
    def save_cfg(self):
        for k,v in self.vars.items(): self.settings[k]=v.get()
        self.settings["interval"]=int(self.settings.get("interval") or 60); save_settings(self.settings); messagebox.showinfo("AXUS","Настройки сохранены")
    def start_sync(self):
        if not self.settings.get("treolan_login") or not self.settings.get("treolan_password"):
            messagebox.showwarning("Treolan","Сначала укажите логин и пароль Treolan в разделе «Настройки»."); return
        if hasattr(self,"progress"): self.progress.start(10)
        threading.Thread(target=self.sync_worker,daemon=True).start()
    def sync_worker(self):
        started=now(); self.q.put(("log",f"[{started}] Синхронизация запущена"))
        try:
            from zeep import Client
            from zeep.transports import Transport
            import requests
            client=Client(self.settings["wsdl"],transport=Transport(session=requests.Session(),timeout=300))
            c=db(); articles=[r["article"] for r in c.execute("SELECT article FROM products WHERE article<>''").fetchall()]; c.close()
            self.q.put(("log",f"Артикулов: {len(articles)}"))
            found={}; batches=[articles[i:i+25] for i in range(0,len(articles),25)]
            for n,batch in enumerate(batches,1):
                result=client.service.GenCatalogV2(
                    login=self.settings["treolan_login"],password=self.settings["treolan_password"],
                    category="",vendorid="0",keywords=" ".join(batch),criterion=1,
                    inArticul=True,inName=False,inMark=False,showNc=1)
                xml=result["Result"] if isinstance(result,dict) and "Result" in result else getattr(result,"Result",result)
                root=ET.fromstring(str(xml))
                for el in root.iter():
                    d={ch.tag.split("}")[-1].lower(): (ch.text or "").strip() for ch in list(el)}
                    art=d.get("articul") or d.get("article") or d.get("sku")
                    if art: found[art.lower()]=d
                self.q.put(("log",f"Пакет {n}/{len(batches)} обработан"))
            c=db(); updated=missed=0
            for r in c.execute("SELECT id,article FROM products").fetchall():
                d=found.get(r["article"].lower())
                if not d: missed+=1; continue
                def pick(*ks):
                    for k in ks:
                        if d.get(k,"")!="": return d[k]
                    return ""
                c.execute("UPDATE products SET price=COALESCE(NULLIF(? ,''),price),stock=COALESCE(NULLIF(?,''),stock),transit=COALESCE(NULLIF(?,''),transit),updated_at=? WHERE id=?",
                    (pick("price","cost","priceusd"),pick("free","stock","quantity","available"),pick("transit","free_transit","transitquantity"),now(),r["id"]))
                updated+=1
            c.commit(); c.close()
            # Backup original workbook before updating it with DB values.
            if EXPORT_SOURCE.exists():
                shutil.copy2(EXPORT_SOURCE,BACKUPS/f"data-{dt.datetime.now():%Y%m%d-%H%M%S}.xlsx")
            self.settings["last_sync"]=now(); save_settings(self.settings)
            self.q.put(("done",f"Готово. Обновлено: {updated}. Не найдено: {missed}."))
        except Exception as e:
            self.q.put(("error",str(e)))
    def export_excel(self):
        from openpyxl import load_workbook
        target=filedialog.asksaveasfilename(defaultextension=".xlsx",filetypes=[("Excel","*.xlsx")],initialfile="AXUS-Treolan-catalog.xlsx")
        if not target:return
        wb=load_workbook(EXPORT_SOURCE)
        c=db()
        for sname in ("Оригинал","Совместимая"):
            ws=wb[sname]; heads={norm(ws.cell(1,col).value):col for col in range(1,ws.max_column+1)}
            for row in range(2,ws.max_row+1):
                art=norm(ws.cell(row,heads["Артикул"]).value) if "Артикул" in heads else ""
                if not art:continue
                r=c.execute("SELECT price,stock,transit FROM products WHERE article=?",(art,)).fetchone()
                if not r:continue
                for key in ("price","stock","transit"):
                    if key in heads: ws.cell(row,heads[key]).value=r[key]
        c.close(); wb.save(target); messagebox.showinfo("AXUS",f"Excel сохранён:\\n{target}")
    def poll(self):
        try:
            while True:
                typ,msg=self.q.get_nowait()
                if hasattr(self,"log"):
                    self.log.insert("end",msg+"\\n"); self.log.see("end")
                if typ=="done" or typ=="error":
                    if hasattr(self,"progress"): self.progress.stop()
                    if typ=="done": self.refresh()
                    else: messagebox.showerror("Синхронизация",msg)
        except queue.Empty: pass
        self.after(1000,self.poll)
    def auto_sync(self):
        # Auto sync after interval, only if credentials exist.
        interval=max(5,int(self.settings.get("interval",60)))*60*1000
        if self.settings.get("treolan_login") and self.settings.get("treolan_password"):
            self.start_sync()
        self.after(interval,self.auto_sync)
    def refresh(self): self.dashboard()

if __name__=="__main__":
    App().mainloop()
