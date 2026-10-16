"""Veil presentation. Palette edits never access Resolve until Apply."""
import json
import logging
import math
from pathlib import Path
from types import SimpleNamespace
import tkinter as tk
from tkinter import ttk, colorchooser, filedialog, messagebox, simpledialog

from palette_core import LABELS, DISPLAY_ORDER, STOCK, builtin_palettes, hex_color, validate_palette
from palette_names import validate_names
from resolve_actions import ResolveActions
from studio_model import (PaletteLibrary, fingerprint, load_preferences, save_preferences,
                          system_appearance, APPEARANCES)
from studio_version import VERSION
from resolve_worker import ResolveWorker, apply_palette, restore_palette, check_session

HERE=Path(__file__).resolve().parent
THEMES={
    'Dark':dict(bg='#17191D',sidebar='#111317',panel='#202328',field='#171A1F',
        border='#363B43',text='#F0F2F5',muted='#B5BDC8',hover='#30353D',
        accent='#E7EBF0',on_accent='#17191D',success='#87DBAE',error='#FFADB2'),
    'Light':dict(bg='#F3F4F6',sidebar='#EAECF0',panel='#FFFFFF',field='#F5F6F8',
        border='#CCD1D9',text='#20242B',muted='#555E6C',hover='#E1E5EB',
        accent='#272C35',on_accent='#FFFFFF',success='#206643',error='#A52032')}

def ink(color):
    try:
        rgb=[int(color[i:i+2],16) for i in (1,3,5)]
        linear=[x/3294.6 if x<=10 else ((x/255+.055)/1.055)**2.4 for x in rgb]
        light=sum(x*y for x,y in zip(linear,(.2126,.7152,.0722)))
        return '#000000' if light>.179 else '#FFFFFF'
    except (ValueError,TypeError):return '#FFFFFF'

class ScrollArea(tk.Frame):
    def __init__(self,parent,app):
        super().__init__(parent,bg=app.c['bg'])
        self.canvas=tk.Canvas(self,bg=app.c['bg'],highlightthickness=0)
        self.bar=ttk.Scrollbar(self,command=self.canvas.yview)
        self.canvas.configure(yscrollcommand=self.scroll_changed)
        self.columnconfigure(0,weight=1);self.rowconfigure(0,weight=1)
        self.canvas.grid(row=0,column=0,sticky='nsew')
        self.bar.grid(row=0,column=1,sticky='ns')
        self.body=tk.Frame(self.canvas,bg=app.c['bg'])
        self.window=self.canvas.create_window(0,0,anchor='nw',window=self.body)
        self.canvas.bind('<Configure>',lambda e:self.canvas.itemconfigure(self.window,width=e.width))
        self.body.bind('<Configure>',lambda e:self.canvas.configure(scrollregion=self.canvas.bbox('all')))
        app.scroll_areas.append(self)
    def scroll_changed(self,first,last):
        self.bar.set(first,last)
        if float(first)<=0 and float(last)>=1:self.bar.grid_remove()
        else:self.bar.grid()

class Surface(tk.Frame):
    """A native widget container with a restrained rounded decorative border."""
    def __init__(self,parent,app,padding=16):
        super().__init__(parent,bg=app.c['bg'],padx=app.p(padding),pady=app.p(padding-2))
        self.app=app;self.border=app.c['border']
        self.back=tk.Canvas(self,bg=app.c['bg'],highlightthickness=0)
        self.back.place(x=-app.p(padding),y=-app.p(padding-2),relwidth=1,relheight=1,
                        width=app.p(padding)*2,height=app.p(padding-2)*2)
        tk.Misc.lower(self.back)
        self.bind('<Configure>',self.draw)
        self.back.bind('<Configure>',self.draw)
    def draw(self,event=None):
        w,h=self.back.winfo_width()-1,self.back.winfo_height()-1;r=self.app.p(6)
        self.back.delete('all')
        self.back.create_polygon(r,1,w-r,1,w,1,w,r,w,h-r,w,h,w-r,h,r,h,1,h,1,h-r,1,r,1,1,
            smooth=True,splinesteps=24,fill=self.app.c['panel'],outline=self.border,width=1)
    def set_border(self,color):self.border=color;self.draw()

class App(ResolveActions):
    PAGES={'Home':'home','Palettes':'palette_page','Themes':'themes','Settings':'settings'}
    def __init__(self,root,demo=False):
        self.root=root; self.demo=demo
        self.session=None;self.menu_names=None;self.failed=False;self.refresh_job=None
        from media_pool_refresh import MediaPoolRefresh
        self.pool_refresh=MediaPoolRefresh(HERE)
        self.storage_error=None
        try:self.library=PaletteLibrary(HERE)
        except Exception as exc:
            self.storage_error=str(exc)
            self.library=None
        self.palettes=self.library.palettes if self.library else builtin_palettes()
        self.users=self.library.users if self.library else {}
        self.palette_names=self.library.names if self.library else {}
        self.user_path=HERE/'saved_palettes.json'
        self.preference_error=None
        try:mode=load_preferences(HERE)
        except Exception as exc:
            mode='Dark';self.preference_error=str(exc)
        self.appearance=tk.StringVar(root,value=mode)
        self.selection=tk.StringVar(root,value='Resolve Original')
        self.values={label:[tk.StringVar(root,value=v) for v in pair] for label,pair in zip(LABELS,STOCK)}
        self.names={label:tk.StringVar(root,value=label) for label in LABELS}
        self.baseline=self.raw_snapshot()
        self.applied=None;self.applied_name=None
        self.active_slot='Orange';self.loading=False
        self.current_page='Home';self.current_tab='Library';self.scroll_areas=[]
        self.filter=tk.StringVar(root,value='')
        self.connection=tk.StringVar(root,value='Disconnected')
        self.status=tk.StringVar(root,value='Choose a palette to edit. Connect when you are ready to apply.')
        self.status_kind='info';self.busy=False;self.operation_error=None;self.connection_problem=False;self.incompatible_version=None
        self.render_job=None;self.poll_count=0
        self.worker=ResolveWorker();self.closing=False;self.busy_label='Working…'
        root.after(40,self.drain_resolve_jobs)
        self.scale=max(1,float(root.winfo_fpixels('1i'))/96)
        root.title('Veil '+VERSION+(' · Preview only' if demo else ''))
        sw,sh=root.winfo_screenwidth(),root.winfo_screenheight()
        width=min(self.p(1220),sw-self.p(60));height=min(self.p(840),sh-self.p(90))
        root.geometry(f'{width}x{height}')
        root.minsize(min(self.p(900),sw-self.p(40)),min(self.p(640),sh-self.p(60)))
        root.protocol('WM_DELETE_WINDOW',self.close)
        self.logo=tk.PhotoImage(file=str(HERE/'veil-icon.png'))
        self.logo=self.logo.subsample(max(1,round(256/self.p(54))))
        for var in [v for pair in self.values.values() for v in pair]+list(self.names.values()):
            var.trace_add('write',self.edited)
        self.status.trace_add('write',lambda *a:self.root.after_idle(self.sync_chrome))
        self.connection.trace_add('write',lambda *a:self.root.after_idle(self.sync_chrome))
        self.appearance.trace_add('write',self.change_appearance)
        root.bind('<MouseWheel>',self.wheel,add='+')
        root.bind('<FocusIn>',self.focus_scroll,add='+')
        root.bind('<Control-s>',lambda e:self.shortcut(self.save))
        root.bind('<Control-Shift-S>',lambda e:self.shortcut(self.save_as))
        root.bind('<Control-o>',lambda e:self.shortcut(self.import_palette))
        for key,page in zip(('1','2','3','4'),self.PAGES):
            root.bind(f'<Alt-Key-{key}>',lambda e,n=page:self.shortcut(lambda:self.navigate(n)))
        self.build_shell()
        root.after(500,self.poll)
        if self.storage_error:self.set_status('Saved palettes could not be read: '+self.storage_error,'error')
        elif self.preference_error:self.set_status('Appearance preference could not be read; using Dark.','error')

    def p(self,value):return max(1,round(value*self.scale))
    def shortcut(self,action):
        action();return 'break'
    def raw_snapshot(self):
        return (tuple(tuple(v.get() for v in self.values[label]) for label in LABELS),
                tuple(self.names[label].get() for label in LABELS))
    @property
    def dirty(self):return self.raw_snapshot()!=self.baseline
    def editor(self):return validate_palette([[v.get() for v in self.values[label]] for label in LABELS])
    def display_names(self):return validate_names([self.names[label].get() for label in LABELS])
    def valid(self):
        try:self.editor();self.display_names();return True
        except ValueError:return False
    def effective_mode(self):
        return self.appearance.get()

    def styles(self):
        c=self.c;style=ttk.Style(self.root);style.theme_use('clam')
        style.configure('.',font=('Segoe UI',11),background=c['panel'],foreground=c['text'])
        for name in ('TButton','Nav.TButton','Tab.TButton'):
            style.configure(name,font=('Segoe UI',11),padding=(self.p(13),self.p(9)),
                            background=c['panel'],foreground=c['text'],borderwidth=1,
                            bordercolor=c['border'],lightcolor=c['panel'],darkcolor=c['panel'],
                            focuscolor=c['muted'])
            style.map(name,background=[('active',c['hover'])],foreground=[('disabled',c['muted'])])
        style.configure('Nav.TButton',anchor='w',background=c['sidebar'],borderwidth=0)
        style.configure('Selected.Nav.TButton',background=c['hover'],font=('Segoe UI Semibold',11))
        style.configure('Selected.Tab.TButton',background=c['hover'],font=('Segoe UI Semibold',11))
        style.configure('Primary.TButton',background=c['accent'],foreground=c['on_accent'],
                        font=('Segoe UI Semibold',11),padding=(self.p(18),self.p(10)))
        style.map('Primary.TButton',background=[('disabled',c['hover']),('active',c['accent'])],
                  foreground=[('disabled',c['muted']),('active',c['on_accent'])])
        style.configure('Compact.TButton',padding=(self.p(8),self.p(5)))
        style.configure('Card.TButton',font=('Segoe UI',10),padding=(self.p(7),self.p(6)))
        style.configure('TEntry',fieldbackground=c['field'],foreground=c['text'],
                        insertcolor=c['text'],bordercolor=c['border'],padding=self.p(7))
        style.map('TEntry',bordercolor=[('focus',c['muted'])])
        style.configure('TRadiobutton',background=c['panel'],foreground=c['text'],
                        padding=self.p(8),font=('Segoe UI',11))
        style.map('TRadiobutton',background=[('active',c['panel'])])
        style.configure('Vertical.TScrollbar',background=c['hover'],troughcolor=c['bg'],
                        bordercolor=c['bg'],arrowcolor=c['muted'],arrowsize=self.p(13))

    def frame(self,parent,bg=None,**kwargs):return tk.Frame(parent,bg=bg or self.c['bg'],**kwargs)
    def label(self,parent,text=None,var=None,size=11,bold=False,muted=False,bg=None,**kwargs):
        return tk.Label(parent,text=text,textvariable=var,bg=bg or self.c['bg'],
            fg=self.c['muted'] if muted else self.c['text'],font=('Segoe UI Semibold' if bold else 'Segoe UI',size),
            anchor='w',justify='left',**kwargs)
    def card(self,parent,padding=16):return Surface(parent,self,padding)
    def button(self,parent,text,command,primary=False,compact=False,**kwargs):
        return ttk.Button(parent,text=text,command=command,
            style='Primary.TButton' if primary else 'Compact.TButton' if compact else 'TButton',**kwargs)

    def build_shell(self):
        if hasattr(self,'shell'):self.shell.destroy()
        self.scroll_areas=[];self.slot_widgets={};self.library_controls={}
        self.c=THEMES[self.effective_mode()];self.rendered_mode=self.effective_mode()
        self.styles();c=self.c;self.root.configure(bg=c['bg'])
        self.shell=self.frame(self.root);self.shell.pack(fill='both',expand=True)
        sidebar=self.frame(self.shell,c['sidebar'],width=self.p(180));sidebar.pack(side='left',fill='y');sidebar.pack_propagate(False)
        brand=self.frame(sidebar,c['sidebar']);brand.pack(fill='x',padx=self.p(18),pady=(self.p(24),self.p(26)))
        tk.Label(brand,image=self.logo,bg=c['sidebar']).pack(anchor='w')
        self.label(brand,'Veil',size=16,bold=True,bg=c['sidebar']).pack(anchor='w',pady=(self.p(6),0))
        self.nav={}
        for page in self.PAGES:
            button=ttk.Button(sidebar,text=page,command=lambda n=page:self.navigate(n),style='Nav.TButton')
            button.pack(fill='x',padx=self.p(12),pady=self.p(3));self.nav[page]=button
        self.label(sidebar,VERSION,muted=True,bg=c['sidebar'],size=10).pack(side='bottom',anchor='w',padx=self.p(24),pady=self.p(20))
        main=self.frame(self.shell);main.pack(side='left',fill='both',expand=True)
        header=self.frame(main);header.pack(fill='x',padx=self.p(26),pady=(self.p(22),self.p(16)))
        self.page_title=self.label(header,self.current_page,size=23,bold=True);self.page_title.pack(side='left')
        self.connect_button=self.button(header,'Connect',self.connect);self.connect_button.pack(side='right')
        self.connection_badge=self.label(header,'● Disconnected',muted=True);self.connection_badge.pack(side='right',padx=self.p(14))
        divider=self.frame(main,c['border'],height=1);divider.pack(fill='x')
        footer=self.frame(main,c['panel'],padx=self.p(24),pady=self.p(13));footer.pack(side='bottom',fill='x')
        self.restore_button=self.button(footer,'Restore Resolve Defaults',self.restore);self.restore_button.pack(side='right',padx=self.p(10))
        self.draft_badge=self.label(footer,var=self.selection,bold=True,bg=c['panel']);self.draft_badge.pack(anchor='w')
        self.draft_state=self.label(footer,'Saved',muted=True,bg=c['panel'],size=10);self.draft_state.pack(anchor='w',pady=(self.p(3),0))
        self.feedback=self.label(main,var=self.status,muted=True,wraplength=self.p(650));self.feedback.pack(side='bottom',fill='x',padx=self.p(26),pady=(self.p(8),self.p(10)))
        self.page_content=self.frame(main);self.page_content.pack(fill='both',expand=True,padx=self.p(26),pady=self.p(18))
        self.show_page();self.sync_chrome()

    def navigate(self,page):
        self.current_page=page;self.show_page();self.sync_chrome()
    def show_page(self):
        if not hasattr(self,'page_content'):return
        for child in self.page_content.winfo_children():child.destroy()
        self.scroll_areas=[];self.slot_widgets={};self.library_controls={}
        self.page_title.configure(text=self.current_page)
        for name,button in self.nav.items():button.configure(style='Selected.Nav.TButton' if name==self.current_page else 'Nav.TButton')
        getattr(self,self.PAGES[self.current_page])()

    def state_label(self):
        if self.demo:return 'Preview only'
        if self.busy:return self.busy_label
        if self.incompatible_version:return f'Resolve {self.incompatible_version} · Apply unavailable'
        if self.failed or self.connection_problem:return 'Connection error'
        return 'Connected' if self.session else 'Disconnected'
    def sync_chrome(self):
        if not hasattr(self,'connection_badge') or not self.connection_badge.winfo_exists():return
        c=self.c
        state=self.state_label()
        self.connection_badge.configure(text='● '+state,fg=c['error'] if self.failed or self.connection_problem else c['success'] if self.session else c['muted'])
        self.connect_button.configure(state='disabled' if self.session or self.demo or self.busy or self.closing else 'normal')
        enabled=self.session and not self.failed and not self.busy and not self.demo and not self.closing
        self.restore_button.configure(state='normal' if enabled else 'disabled')
        for name,(button,tag) in self.library_controls.items():
            if button.winfo_exists():
                button.configure(state='normal' if enabled else 'disabled')
                tag.configure(text=self.library_tag(name))
        self.draft_state.configure(text=('Unsaved edits' if self.dirty else 'Saved palette')+' · '+
            ('Applied to Resolve' if self.matches_applied() else 'Editor only'))
        self.feedback.configure(fg=c['error'] if self.status_kind=='error' else c['success'] if self.status_kind=='success' else c['muted'])
        if hasattr(self,'home_connection') and self.home_connection.winfo_exists():
            self.home_connection.configure(text=state)
            self.home_active.configure(text=self.applied_name or ('Resolve defaults' if self.session else 'No palette applied'))
            self.home_strip(self.applied[0] if self.applied else STOCK)
        if hasattr(self,'validation') and self.validation.winfo_exists():
            try:self.editor();self.display_names();message=''
            except ValueError as exc:message=str(exc)
            self.validation.configure(text=message)
            if message:
                self.validation.pack(fill='x',pady=self.p(4),before=self.clip_label)
            else:self.validation.pack_forget()
        if hasattr(self,'save_button') and self.save_button.winfo_exists():
            self.save_button.configure(state='normal' if self.selection.get() in self.users and self.valid() else 'disabled')

    def matches_applied(self):
        try:return self.applied is not None and fingerprint(self.editor(),self.display_names())==self.applied
        except ValueError:return False
    def set_status(self,text,kind='info'):
        self.status_kind=kind;self.status.set(text);self.sync_chrome()
    def error(self,exc):
        self.operation_error=exc
        logging.error('Operation failed: %s',exc,exc_info=(type(exc),exc,exc.__traceback__))
        self.set_status(str(exc),'error')
    def change_appearance(self,*_):
        try:save_preferences(HERE,self.appearance.get())
        except Exception as exc:self.error(exc);return
        self.build_shell()

    def strip(self,parent,colors,height=28):
        canvas=tk.Canvas(parent,height=self.p(height),bg=self.c['panel'],highlightthickness=0)
        def draw(event=None):
            canvas.delete('all');w=canvas.winfo_width();h=self.p(height)
            for i,label in enumerate(DISPLAY_ORDER):
                pair=colors[LABELS.index(label)]
                canvas.create_rectangle(i*w/16,0,(i+1)*w/16,h,fill=pair[1],outline='')
        canvas.bind('<Configure>',draw);canvas.pack(fill='x',pady=(self.p(12),self.p(8)))
        return lambda new:(colors.__setitem__(slice(None),[list(pair) for pair in new]),draw())

    def home(self):
        area=ScrollArea(self.page_content,self);area.pack(fill='both',expand=True);body=area.body
        self.label(body,'Your creative workspace',size=15,bold=True).pack(anchor='w')
        self.label(body,'Continue with a palette, or explore what’s next.',muted=True).pack(anchor='w',pady=(self.p(6),self.p(20)))
        connection=self.card(body);connection.pack(fill='x',pady=(0,self.p(14)))
        self.label(connection,'DaVinci Resolve',bold=True,bg=self.c['panel']).pack(anchor='w')
        self.home_connection=self.label(connection,self.state_label(),size=16,bold=True,bg=self.c['panel']);self.home_connection.pack(anchor='w',pady=self.p(6))
        self.label(connection,'Open Resolve and a timeline, then use Connect above.' if not self.session else 'Ready for palette changes.',muted=True,bg=self.c['panel']).pack(anchor='w')
        active=self.card(body);active.pack(fill='x',pady=(0,self.p(14)))
        self.label(active,'Applied to Resolve',muted=True,bg=self.c['panel']).pack(anchor='w')
        self.home_active=self.label(active,self.applied_name or 'No palette applied',size=16,bold=True,bg=self.c['panel']);self.home_active.pack(anchor='w',pady=(self.p(6),0))
        self.home_strip=self.strip(active,[list(x) for x in (self.applied[0] if self.applied else STOCK)],34)
        self.label(active,'16 existing slots · custom names · two shades per slot',muted=True,bg=self.c['panel']).pack(anchor='w')
        edit=self.card(body);edit.pack(fill='x')
        self.label(edit,'In the editor',muted=True,bg=self.c['panel']).pack(anchor='w')
        self.label(edit,var=self.selection,size=16,bold=True,bg=self.c['panel']).pack(anchor='w',pady=(self.p(6),self.p(12)))
        self.button(edit,'Continue editing',self.continue_editing,primary=True).pack(anchor='w')
    def continue_editing(self):
        self.current_tab='Editor';self.navigate('Palettes')

    def palette_page(self):
        tabs=self.frame(self.page_content);tabs.pack(fill='x',pady=(0,self.p(18)))
        for name in ('Library','Editor'):
            ttk.Button(tabs,text=name,command=lambda n=name:self.change_tab(n),
                style='Selected.Tab.TButton' if self.current_tab==name else 'Tab.TButton').pack(side='left',padx=(0,self.p(6)))
        if self.current_tab=='Library':self.library_page()
        else:self.editor_page()
    def change_tab(self,name):self.current_tab=name;self.show_page();self.sync_chrome()

    def library_page(self):
        row=self.frame(self.page_content);row.pack(fill='x',pady=(0,self.p(12)))
        self.label(row,'Saved palettes',size=15,bold=True).pack(side='left')
        self.button(row,'Import…',self.import_palette).pack(side='right')
        search=ttk.Entry(row,textvariable=self.filter,width=20);search.pack(side='right',padx=self.p(10))
        self.label(row,'Search',muted=True).pack(side='right')
        search.bind('<KeyRelease>',lambda e:self.render_library())
        self.label(self.page_content,'Edit a palette, or apply a saved palette directly to Resolve.',muted=True,wraplength=self.p(750)).pack(anchor='w',pady=(0,self.p(14)))
        self.library_area=ScrollArea(self.page_content,self);self.library_area.pack(fill='both',expand=True)
        self.library_area.canvas.bind('<Configure>',self.library_resize,add='+')
        self.library_columns=0;self.render_library()
    def library_resize(self,event):
        cols=max(1,min(3,event.width//self.p(340)))
        if cols!=self.library_columns:self.library_columns=cols;self.render_library()
    def render_library(self):
        if not hasattr(self,'library_area') or not self.library_area.winfo_exists():return
        host=self.library_area.body
        for child in host.winfo_children():child.destroy()
        self.library_controls={}
        cols=self.library_columns or 2
        for col in range(3):host.columnconfigure(col,weight=1 if col<cols else 0,uniform='library' if col<cols else '')
        names=[name for name in self.palettes if self.filter.get().casefold() in name.casefold()]
        if not names:self.label(host,'No matching palettes. Try another name.',muted=True).grid(sticky='w')
        for index,name in enumerate(names):
            card=self.card(host);card.grid(row=index//cols,column=index%cols,sticky='nsew',padx=(0,self.p(10)),pady=(0,self.p(10)))
            heading=self.frame(card,self.c['panel']);heading.pack(fill='x')
            title=self.label(heading,name,size=12,bold=True,bg=self.c['panel'],wraplength=self.p(270))
            title.configure(anchor='center',justify='center');title.pack(fill='x')
            self.strip(card,[list(x) for x in self.palettes[name]],26)
            tag=self.label(card,self.library_tag(name),size=10,muted=True,bg=self.c['panel'])
            tag.configure(anchor='center',justify='center');tag.pack(fill='x',pady=(0,self.p(9)))
            actions=self.frame(card,self.c['panel']);actions.pack(anchor='center')
            ttk.Button(actions,text='Edit palette',command=lambda n=name:self.choose_palette(n),width=0,style='Card.TButton').pack(side='left')
            apply_button=ttk.Button(actions,text='Apply palette',command=lambda n=name:self.apply_saved(n),width=0,style='Card.TButton')
            apply_button.pack(side='left',padx=(self.p(6),0))
            if name in self.users:
                ttk.Button(actions,text='Delete',command=lambda n=name:self.delete_palette(n),width=0,style='Card.TButton',
                    state='disabled' if self.busy or self.storage_error else 'normal').pack(side='left',padx=(self.p(6),0))
            self.library_controls[name]=(apply_button,tag)
        self.sync_chrome()

    def library_tag(self,name):
        edited=name==self.selection.get()
        applied=self.applied is not None and fingerprint(self.palettes[name],self.palette_names.get(name,list(LABELS)))==self.applied
        return ('Editing'+(' · Unsaved' if self.dirty else '') if edited else 'Built-in' if name in builtin_palettes() else 'Imported')+(' · Applied' if applied else '')

    def delete_palette(self,name):
        if self.busy:return
        try:
            if self.storage_error:raise RuntimeError('Saved palette storage needs attention: '+self.storage_error)
            if name not in self.users:raise ValueError('Only user-saved palettes can be deleted.')
            if not messagebox.askyesno('Delete palette',f'Delete “{name}” from your Library?\n\nThe palette currently applied to Resolve will stay active.',parent=self.root):return
            selected=self.selection.get()==name
            keep_draft=selected and self.dirty
            self.library.delete(name)
            self.palettes,self.users,self.palette_names=self.library.palettes,self.library.users,self.library.names
            if selected:
                if keep_draft:
                    self.selection.set('Unsaved palette');self.baseline=None
                else:
                    self.loading=True;self.selection.set('Resolve Original');self.show_palette(STOCK)
                    for label in LABELS:self.names[label].set(label)
                    self.loading=False;self.baseline=self.raw_snapshot()
            if self.applied_name in (name,name+' (edited)'):
                self.applied_name+=' (deleted from Library)'
            self.show_page()
            self.set_status('Deleted '+name+' from Library.'+(' Your unsaved editor draft is kept.' if keep_draft else ''),'success')
        except Exception as exc:self.error(exc)

    def confirm_discard(self):
        if not self.dirty:return True
        answer=messagebox.askyesnocancel('Unsaved palette edits','Save your edits before opening another palette?',parent=self.root)
        if answer is None:return False
        if answer:return self.save() if self.selection.get() in self.users else self.save_as()
        return True
    def choose_palette(self,name):
        if name!=self.selection.get() and not self.confirm_discard():return
        if name==self.selection.get():self.continue_editing();return
        self.loading=True;self.selection.set(name);self.show_palette(self.palettes[name])
        for label,alias in zip(LABELS,self.palette_names.get(name,LABELS)):self.names[label].set(alias)
        self.loading=False;self.baseline=self.raw_snapshot()
        self.continue_editing();self.set_status('Editing '+name+'. Save, then apply it from the Library.')
    def show_palette(self,palette):
        for label,pair in zip(LABELS,validate_palette(palette)):
            for variable,color in zip(self.values[label],pair):variable.set(color)

    def editor_page(self):
        header=self.frame(self.page_content);header.pack(fill='x')
        self.label(header,var=self.selection,size=16,bold=True).pack(side='left')
        self.button(header,'Export…',self.export_palette,width=7).pack(side='right')
        self.button(header,'Import…',self.import_palette,width=7).pack(side='right',padx=self.p(6))
        self.button(header,'Save As…',self.save_as,width=8).pack(side='right',padx=self.p(6))
        self.save_button=self.button(header,'Save',self.save,width=6);self.save_button.pack(side='right')
        self.editor_strip=self.strip(self.page_content,self.preview_colors(),24)
        self.label(self.page_content,'Select a slot to edit its name and two shades. Saving keeps your palette; applying updates Resolve.',muted=True,wraplength=self.p(850)).pack(anchor='w',pady=(0,self.p(12)))
        body=self.frame(self.page_content);body.pack(fill='both',expand=True)
        self.slots_area=ScrollArea(body,self);self.slots_area.pack(side='left',fill='both',expand=True,padx=(0,self.p(16)))
        self.detail_area=ScrollArea(body,self);self.detail_area.configure(width=self.p(270));self.detail_area.pack(side='right',fill='y');self.detail_area.grid_propagate(False)
        self.slots_area.canvas.bind('<Configure>',self.slot_resize,add='+')
        self.slot_columns=0
        for position,label in enumerate(DISPLAY_ORDER):
            card=self.card(self.slots_area.body,padding=12)
            title=tk.Button(card,text=f'{position+1:02d}  {self.names[label].get()}',command=lambda n=label:self.select_slot(n),
                bg=self.c['panel'],fg=self.c['text'],activebackground=self.c['hover'],activeforeground=self.c['text'],
                relief='flat',bd=0,highlightthickness=1,highlightbackground=self.c['panel'],highlightcolor=self.c['muted'],
                anchor='w',justify='left',font=('Segoe UI Semibold',11),wraplength=self.p(145),cursor='hand2')
            title.pack(fill='x')
            swatch=tk.Canvas(card,height=self.p(30),bg=self.c['panel'],highlightthickness=0);swatch.pack(fill='x',pady=(self.p(6),self.p(2)))
            self.slot_widgets[label]=(card,title,swatch,position)
            swatch.bind('<Configure>',lambda e,n=label:self.draw_slot(n))
            swatch.bind('<Button-1>',lambda e,n=label:self.select_slot(n))
        self.slot_resize(None);self.select_slot(self.active_slot)
    def slot_resize(self,event):
        width=event.width if event else self.slots_area.canvas.winfo_width()
        cols=max(1,min(4,width//self.p(155)))
        if cols==self.slot_columns:return
        self.slot_columns=cols
        for col in range(4):self.slots_area.body.columnconfigure(col,weight=1 if col<cols else 0,uniform='slot' if col<cols else '')
        for card,title,swatch,index in self.slot_widgets.values():
            card.grid(row=index//cols,column=index%cols,sticky='nsew',padx=(0,self.p(8)),pady=(0,self.p(8)))
    def preview_colors(self):
        return [[self.safe_color(v.get()) for v in self.values[label]] for label in LABELS]
    def safe_color(self,value):
        try:return hex_color(value)
        except ValueError:return self.c['border']
    def draw_slot(self,label):
        if label not in self.slot_widgets:return
        card,title,canvas,index=self.slot_widgets[label]
        card.set_border(self.c['muted'] if label==self.active_slot else self.c['border'])
        title.configure(text=f'{index+1:02d}  {self.names[label].get()}')
        canvas.delete('all');w=canvas.winfo_width();h=self.p(30)
        for i,var in enumerate(self.values[label]):
            color=self.safe_color(var.get())
            canvas.create_rectangle(i*w/2,0,(i+1)*w/2,h,fill=color,outline='')
            canvas.create_text((i+.5)*w/2,h/2,text=str(i+1),fill=ink(color),font=('Segoe UI',10))

    def select_slot(self,label):
        self.active_slot=label
        for name in self.slot_widgets:self.draw_slot(name)
        parent=self.detail_area.body
        for child in parent.winfo_children():child.destroy()
        panel=self.card(parent,padding=12);panel.pack(fill='x')
        index=DISPLAY_ORDER.index(label)+1
        self.label(panel,f'Slot {index} · {label}',muted=True,bg=self.c['panel']).pack(anchor='w')
        self.label(panel,'Display name',bold=True,bg=self.c['panel']).pack(anchor='w',pady=(self.p(8),self.p(4)))
        ttk.Entry(panel,textvariable=self.names[label],width=21).pack(fill='x')
        for i in range(2):
            self.label(panel,f'Shade {i+1}',bold=True,bg=self.c['panel']).pack(anchor='w',pady=(self.p(10),self.p(4)))
            row=self.frame(panel,self.c['panel']);row.pack(fill='x')
            self.button(row,'Pick…',lambda n=label,j=i:self.pick(n,j),width=6,compact=True).pack(side='left')
            ttk.Entry(row,textvariable=self.values[label][i],width=10,font=('Consolas',11)).pack(side='left',fill='x',expand=True,padx=(self.p(8),0))
        self.validation=self.label(panel,'',size=10,bg=self.c['panel'],wraplength=self.p(225));self.validation.configure(fg=self.c['error'])
        self.clip_label=self.label(panel,'Clip preview',bold=True,bg=self.c['panel']);self.clip_label.pack(anchor='w',pady=(self.p(12),self.p(6)))
        self.clip_preview=tk.Canvas(panel,height=self.p(80),bg=self.c['field'],highlightthickness=0);self.clip_preview.pack(fill='x')
        self.clip_preview.bind('<Configure>',lambda e:self.draw_clip())
        self.label(panel,'Illustration only. Save, then apply from the Library.',size=10,muted=True,bg=self.c['panel'],wraplength=self.p(220)).pack(anchor='w',pady=(self.p(6),0))
        self.draw_clip();self.sync_chrome()
    def draw_clip(self):
        if not hasattr(self,'clip_preview') or not self.clip_preview.winfo_exists():return
        canvas=self.clip_preview;canvas.delete('all');w=canvas.winfo_width();h=self.p(80)
        for i,var in enumerate(self.values[self.active_slot]):
            color=self.safe_color(var.get());y=self.p(6+36*i)
            canvas.create_rectangle(self.p(8),y,w-self.p(8),y+self.p(30),fill=color,outline='')
            canvas.create_text(self.p(16),y+self.p(10),anchor='w',text=f'Shade {i+1}',fill=ink(color),font=('Segoe UI Semibold',10))
            for x in range(self.p(16),max(self.p(17),w-self.p(16)),self.p(5)):
                height=self.p(1+2*(1+math.sin(x*.17)))
                canvas.create_line(x,y+self.p(22)-height,x,y+self.p(22)+height,fill=ink(color))
    def pick(self,label,index):
        _,color=colorchooser.askcolor(self.safe_color(self.values[label][index].get()),parent=self.root,title=f'{self.names[label].get()} · Shade {index+1}')
        if color:self.values[label][index].set(color.upper())
    def edited(self,*_):
        if self.loading:return
        if self.render_job:self.root.after_cancel(self.render_job)
        self.render_job=self.root.after(50,self.refresh_editor)
    def refresh_editor(self):
        self.render_job=None
        if hasattr(self,'editor_strip') and self.current_page=='Palettes' and self.current_tab=='Editor':
            self.editor_strip(self.preview_colors())
            for label in self.slot_widgets:self.draw_slot(label)
            self.draw_clip()
        self.sync_chrome()

    def save(self):
        if self.selection.get() not in self.users:return self.save_as()
        return self.save_named(self.selection.get())
    def save_as(self):
        if not self.valid():self.set_status('Fix the highlighted name or hex value before saving.','error');return False
        name=simpledialog.askstring('Save palette as','Palette name (1–60 characters):',initialvalue=self.selection.get()+' copy',parent=self.root)
        if name is None:return False
        name=name.strip()
        if name in self.users and not messagebox.askyesno('Replace saved palette',f'Replace “{name}”?',parent=self.root):return False
        return self.save_named(name)
    def save_named(self,name):
        try:
            if self.storage_error:raise RuntimeError('Saved palette storage needs attention: '+self.storage_error)
            name=self.library.save(name,self.editor(),self.display_names())
            self.palettes,self.users,self.palette_names=self.library.palettes,self.library.users,self.library.names
            self.selection.set(name);self.baseline=self.raw_snapshot()
            if self.matches_applied():self.applied_name=name
            self.set_status('Saved '+name+'. Apply it from the Library to update Resolve.','success')
            if self.current_page=='Palettes' and self.current_tab=='Library':self.render_library()
            self.sync_chrome();return True
        except Exception as exc:self.error(exc);return False
    def export_palette(self):
        try:
            self.editor();self.display_names()
            path=filedialog.asksaveasfilename(parent=self.root,title='Export palette',initialfile=self.selection.get()+'.json',defaultextension='.json',filetypes=[('Palette JSON','*.json')])
            if path:
                from palette_core import atomic_json
                from palette_names import encode
                atomic_json(path,encode(self.selection.get(),self.editor(),self.display_names()))
                self.set_status('Palette exported.','success')
        except Exception as exc:self.error(exc)
    def import_palette(self):
        try:
            path=filedialog.askopenfilename(parent=self.root,title='Import palette',filetypes=[('Palette files','*.json *.hex'),('Hex palette','*.hex'),('Palette JSON','*.json')])
            if not path:return
            # Validate before asking to replace the existing draft.
            name,colors,names=PaletteLibrary.read_import(self.library,path)
            if not self.confirm_discard():return
            self.loading=True;self.show_palette(colors)
            for label,name in zip(LABELS,names):self.names[label].set(name)
            self.selection.set(name)
            self.loading=False;self.baseline=None
            detail=' Hex colors use Shade 2; Shade 1 is generated darker. Slot names are editable.' if Path(path).suffix.lower()=='.hex' else ''
            self.continue_editing();self.set_status('Imported into the editor. Save As, then apply from the Library.'+detail)
        except Exception as exc:
            self.loading=False;self.error(exc)

    def themes(self):
        card=self.card(self.page_content);card.pack(fill='x')
        self.label(card,'Resolve themes',size=18,bold=True,bg=self.c['panel']).pack(anchor='w')
        self.label(card,'Coming soon',size=12,muted=True,bg=self.c['panel']).pack(anchor='w',pady=self.p(12))
        self.label(card,'A new way to shape your creative workspace. Future themes will customize Resolve’s interface.',bg=self.c['panel'],wraplength=self.p(700)).pack(anchor='w')
        self.label(card,'For Veil’s own dark or light appearance, visit Settings.',muted=True,bg=self.c['panel'],wraplength=self.p(700)).pack(anchor='w',pady=(self.p(14),self.p(16)))
        self.button(card,'Open Settings',lambda:self.navigate('Settings')).pack(anchor='w')
    def settings(self):
        area=ScrollArea(self.page_content,self);area.pack(fill='both',expand=True)
        card=self.card(area.body);card.pack(fill='x',pady=(0,self.p(16)))
        self.label(card,'Appearance',size=16,bold=True,bg=self.c['panel']).pack(anchor='w')
        self.label(card,'Choose how Veil looks. Your preference is remembered.',muted=True,bg=self.c['panel'],wraplength=self.p(700)).pack(anchor='w',pady=self.p(10))
        for mode in APPEARANCES:ttk.Radiobutton(card,text=mode,value=mode,variable=self.appearance).pack(anchor='w')
        card=self.card(area.body);card.pack(fill='x',pady=(0,self.p(16)))
        self.label(card,'Compatibility & recovery',size=16,bold=True,bg=self.c['panel']).pack(anchor='w')
        self.label(card,'Experimental preview · DaVinci Resolve Studio 21.1.0.14',bg=self.c['panel']).pack(anchor='w',pady=self.p(10))
        self.label(card,'Palettes replace the 16 existing slots. Assigned identities stay the same. Unassigned audio and video follow slots 6 and 9. Normal close restores Resolve’s original colors and menu names.',muted=True,bg=self.c['panel'],wraplength=self.p(700)).pack(anchor='w')
        self.label(card,'Run Check Connection.cmd for the read-only connection checks. If recovery needs attention, close the Clip Color menu and restart Resolve before reconnecting.',muted=True,bg=self.c['panel'],wraplength=self.p(700)).pack(anchor='w',pady=(self.p(10),0))
        card=self.card(area.body);card.pack(fill='x')
        self.label(card,'Keyboard shortcuts',size=16,bold=True,bg=self.c['panel']).pack(anchor='w')
        self.label(card,'Ctrl+S  Save    ·    Ctrl+Shift+S  Save As    ·    Ctrl+O  Import\nAlt+1–4  Navigate    ·    Tab / Shift+Tab  Move focus',muted=True,bg=self.c['panel'],wraplength=self.p(700)).pack(anchor='w',pady=self.p(10))

    def connect(self):
        if self.demo or self.busy or self.worker.jobs or self.closing:return
        self.operation_error=None;self.connection_problem=False;self.incompatible_version=None;self.set_status('Connecting to Resolve…')
        self.root.update_idletasks();ResolveActions.connect(self)
        if self.session:
            self.applied=fingerprint(STOCK,LABELS) if not self.session.recovered else None
            self.applied_name='Resolve Original' if not self.session.recovered else 'Recovered session'
            self.set_status('Connected. Apply a saved palette from the Library.','success')
        elif not self.incompatible_version:self.connection_problem=True
        self.sync_chrome()
    def apply(self):
        try:
            self.apply_payload(self.editor(),self.display_names(),self.selection.get()+(' (edited)' if self.dirty else ''))
        except Exception as exc:self.error(exc)

    def apply_saved(self,name):
        try:
            self.apply_payload(self.palettes[name],self.palette_names.get(name,list(LABELS)),name)
        except Exception as exc:self.error(exc)

    def apply_payload(self,colors,names,name):
        if self.busy or self.closing:return
        if self.demo or not self.session:
            self.set_status('Connect to Resolve before applying a palette.');return
        if self.failed:
            self.set_status('Restart Resolve before applying a palette.','error');return
        colors=validate_palette(colors);names=validate_names(list(names))
        self.operation_error=None;self.busy=True;self.busy_label='Applying…'
        self.set_status('Applying '+name+'…')
        session,menu=self.session,self.menu_names
        def complete(value,error):
            self.busy=False
            if error:self.error(error)
            else:
                self.applied=fingerprint(colors,names);self.applied_name=name
                self.set_status('Applied '+name+' to Resolve.','success')
                self.schedule_refresh()
            self.sync_chrome()
        self.begin_resolve_operation('apply',session,lambda:apply_palette(session,menu,colors,names),complete)
    def restore(self):
        if self.busy or self.closing:return
        if not self.session or self.failed:
            self.set_status('Connect to a verified Resolve session before restoring.','error');return
        self.operation_error=None;self.busy=True;self.busy_label='Restoring…'
        self.set_status('Restoring Resolve defaults…')
        session,menu=self.session,self.menu_names
        def complete(value,error):
            self.busy=False
            if error:self.error(error)
            else:
                self.applied=fingerprint(STOCK,LABELS);self.applied_name='Resolve Original'
                self.set_status('Resolve defaults restored and verified. Your editor draft is kept.','success')
                self.schedule_refresh()
            self.sync_chrome()
        self.begin_resolve_operation('restore',session,lambda:restore_palette(session,menu),complete)
    def begin_resolve_operation(self,label,session,work,complete):
        # Wait in Tk rather than queue writes behind a check: its result may
        # invalidate / close the handle before this operation can safely start.
        if self.worker.jobs:
            self.root.after(40,lambda:self.begin_resolve_operation(label,session,work,complete));return
        if self.failed or self.session is not session:
            complete(None,RuntimeError('Resolve connection changed; reconnect before continuing.'));return
        self.worker.submit(label,work,complete)
    def drain_resolve_jobs(self):
        self.worker.drain()
        if self.closing and not self.worker.jobs and not getattr(self,'finishing_close',False):
            if not self.busy:
                self.closing=False;self.root.after_idle(self.close)
        self.root.after(40,self.drain_resolve_jobs)
    def repaint_media_pool(self):
        self.refresh_job=None
        if self.closing:return
        if self.busy or self.worker.jobs:
            self.refresh_job=self.root.after(150,self.repaint_media_pool);return
        if not self.session:return
        session=self.session
        def work():
            if session.alive():return self.pool_refresh.repaint(session.pid)
        def complete(value,error):
            if error:
                logging.warning('Media Pool repaint skipped: %s',error)
                if not self.busy:self.set_status('Media Pool repaint skipped: '+str(error))
        self.worker.submit('Media Pool repaint',work,complete)
    def poll(self):
        if self.session and not self.busy and not self.worker.jobs and not self.closing:
            session,menu=self.session,self.menu_names
            validate=not self.failed
            def complete(changed,error):
                if self.session is not session:return
                if error:
                    if not session.alive():
                        session.close();self.session=None;self.menu_names=None
                        self.applied=None;self.applied_name=None
                        self.failed=False;self.connection_problem=False;self.operation_error=None
                        if self.refresh_job:
                            self.root.after_cancel(self.refresh_job);self.refresh_job=None
                        self.connection.set('Disconnected')
                        self.set_status('Open Resolve, then Connect.');self.sync_chrome();return
                    else:
                        self.failed=True;self.connection.set('Connection changed · restart Resolve before continuing')
                    self.error(error)
                elif changed:self.schedule_refresh()
                self.sync_chrome()
            def work():
                changed=check_session(session,menu,validate=validate)
                return changed or (validate and self.pool_refresh.refresh_pending(session.pid))
            self.worker.submit('connection check',work,complete)
        self.poll_count+=1
        self.sync_chrome()
        self.root.after(500,self.poll)
    def close(self):
        if getattr(self,'finishing_close',False):return
        if self.busy or self.worker.jobs:
            self.closing=True
            self.set_status('Waiting for the current Resolve operation before restoring and closing…');return
        # Modal dialogs pump Tk events. Pause new jobs until close succeeds or
        # is cancelled, so no handle checks race with exit restoration.
        self.closing=True;self.finishing_close=True;self.sync_chrome()
        try:
            if self.dirty:
                answer=messagebox.askyesnocancel('Unsaved palette edits','Save your edits before closing Veil? Resolve defaults are restored on normal close.',parent=self.root)
                if answer is None:return
                if answer and not self.save():return
            ResolveActions.close(self)
            if not self.session:self.worker.shutdown()
        finally:
            self.finishing_close=False;self.closing=False
            try:self.sync_chrome()
            except tk.TclError:pass # Successful close destroyed the window.
    def wheel(self,event):
        for area in self.scroll_areas:
            if area.winfo_exists() and str(event.widget).startswith(str(area)):
                area.canvas.yview_scroll(-int(event.delta/120),'units');return 'break'
    def focus_scroll(self,event):
        for area in self.scroll_areas:
            if not area.winfo_exists() or not str(event.widget).startswith(str(area.body)):continue
            self.root.update_idletasks()
            y=event.widget.winfo_rooty()-area.body.winfo_rooty()
            total=max(1,area.body.winfo_height());top=area.canvas.canvasy(0);height=area.canvas.winfo_height()
            if y<top:area.canvas.yview_moveto(max(0,y/total))
            elif y+event.widget.winfo_height()>top+height:area.canvas.yview_moveto(max(0,(y+event.widget.winfo_height()-height)/total))
