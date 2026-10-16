"""Monochrome Omen workspace; Resolve transactions remain in studio_legacy."""
import tkinter as tk
import time
from tkinter import ttk, messagebox, filedialog
from pathlib import Path
import studio_legacy as legacy
from studio_legacy import App as LegacyApp,ScrollArea as LegacyScrollArea,Surface,ink
from studio_controls import Button,Field,Pill,ColorChip,image,Scrollbar
from palette_core import LABELS,DISPLAY_ORDER,STOCK,builtin_palettes
from studio_model import fingerprint,APPEARANCES,PaletteLibrary
from studio_version import VERSION
from studio_menu import RoundedMenu
from studio_fonts import load_fonts,REGULAR,MEDIUM,SEMIBOLD
import veil_update_ui

HERE=Path(__file__).resolve().parent
THEMES={
 'Dark':dict(bg='#191919',sidebar='#222222',panel='#222222',field='#303030',control='#333333',selected='#454545',border='#3D3D3D',text='#EFEFEF',muted='#B8B8B8',disabled='#999999',hover='#404040',accent='#DADADA',on_accent='#191919',focus='#E5E5E5',success='#D4D4D4',error='#EFEFEF'),
 'Light':dict(bg='#DADADA',sidebar='#E5E5E5',panel='#E5E5E5',field='#ECECEC',control='#CCCCCC',selected='#B9B9B9',border='#B5B5B5',text='#222222',muted='#535353',disabled='#646464',hover='#BFBFBF',accent='#303030',on_accent='#ECECEC',focus='#353535',success='#303030',error='#222222')}
legacy.THEMES=THEMES
class NullControl:
    def configure(self,**kwargs):pass
class ScrollArea(LegacyScrollArea):
    def __init__(self,parent,app):
        super().__init__(parent,app)
        self.bar.destroy()
        self.bar=Scrollbar(self,app,self.canvas.yview)
        self.bar.grid(row=0,column=1,sticky='ns')

class Panel(Surface):
    def __init__(self,*args,**kwargs):
        self.active=False;self.selected=False;self.editor_surface=kwargs.pop('editor_surface',False)
        super().__init__(*args,**kwargs)
        self.bind('<Destroy>',lambda e:setattr(self,'photos',[]),add='+')
    def set_active(self,active):
        if active!=self.active:self.active=active;self.draw()
    def set_selected(self,selected):
        self.selected=selected
        fill=self.app.c['selected'] if selected else self.app.c['panel']
        for child in self.winfo_children():
            if child is not self.back:child.configure(bg=fill)
        self.draw()
    def draw(self,event=None):
        w,h=max(2,self.back.winfo_width()),max(2,self.back.winfo_height())
        self.back.delete('all');self.photos=[]
        inset=self.app.p(2) if self.active else self.app.p(1) if self.editor_surface else 0
        if self.editor_surface and not self.active:
            self.photos.append(image(w,h,self.app.c['border'],radius=self.app.p(14)));self.back.create_image(0,0,image=self.photos[-1],anchor='nw')
        if self.active:
            color='#DADADA' if self.app.effective_mode()=='Dark' else '#454545'
            self.photos.append(image(w,h,color,radius=self.app.p(14)))
            self.back.create_image(0,0,image=self.photos[-1],anchor='nw')
        self.photos.append(image(max(2,w-2*inset),max(2,h-2*inset),self.app.c['selected'] if self.selected else self.app.c['panel'],radius=self.app.p(14)-inset))
        self.back.create_image(inset,inset,image=self.photos[-1],anchor='nw')

class App(LegacyApp):
    PAGES={'Dashboard':'home','Palettes':'palette_page','Themes':'themes','Settings':'settings'}
    def visible_palettes(self):
        return {name:colors for name,colors in self.palettes.items() if name not in builtin_palettes()}
    def __init__(self,root,demo=False):
        load_fonts(root)
        super().__init__(root,demo)
        name=next(iter(self.visible_palettes()),None)
        self.loading=True;self.selection.set(name or 'New Palette')
        if name:
            self.show_palette(self.palettes[name])
            for label,alias in zip(LABELS,self.palette_names.get(name,LABELS)):self.names[label].set(alias)
        self.loading=False;self.baseline=self.raw_snapshot()
        self.reset_undo()
        root.bind('<Control-z>',self.undo_shortcut)
        root.bind('<Control-Z>',self.redo_shortcut)
        root.bind('<Control-Shift-z>',self.redo_shortcut)
        root.bind('<Control-Shift-Z>',self.redo_shortcut)
        root.bind('<Control-Shift-s>',lambda e:self.shortcut(self.save_as))
        if not demo:
            self.root.after(1800,lambda:veil_update_ui.check_in_background(self))
    def styles(self):
        super().styles()
        s=ttk.Style(self.root)
        s.configure('.',font=(REGULAR,11))
        for name in ('TButton','Compact.TButton','Nav.TButton','Tab.TButton','Card.TButton','TEntry','TCombobox'):
            s.configure(name,font=(REGULAR,11))
        for name in ('Selected.Nav.TButton','Selected.Tab.TButton','Primary.TButton'):
            s.configure(name,font=(SEMIBOLD,11))
        s.configure('TCombobox',fieldbackground=self.c['field'],background=self.c['control'],foreground=self.c['text'],padding=self.p(7),arrowsize=self.p(12))
        s.map('TCombobox',fieldbackground=[('readonly',self.c['field'])],foreground=[('readonly',self.c['text'])])
    def label(self,parent,text=None,var=None,size=11,bold=False,muted=False,bg=None,**kwargs):
        anchor=kwargs.pop('anchor_override','w')
        family=REGULAR if not bold else SEMIBOLD
        face=(REGULAR,size,'bold') if bold and size>=18 else (family,size)
        return tk.Label(parent,text=text,textvariable=var,bg=bg or self.c['bg'],fg=self.c['muted'] if muted else self.c['text'],font=face,anchor=anchor,justify='center' if anchor=='center' else 'left',**kwargs)
    def card(self,parent,padding=16):return Panel(parent,self,padding)
    def button(self,parent,text,command,primary=False,compact=False,**kwargs):
        kwargs.pop('width',None)
        return Button(parent,self,text,command,primary=primary,compact=compact,**kwargs)
    def field(self,parent,variable,width=18):return Field(parent,self,variable,width)
    def separator(self,parent,vertical=False):
        line=tk.Frame(parent,bg=self.c['border'],bd=0,highlightthickness=0,
                      width=self.p(1),height=self.p(1))
        if vertical:line.pack(side='left',fill='y',padx=self.p(7),pady=self.p(9))
        else:line.pack(fill='x')
        return line
    def build_shell(self):
        if self.current_page=='Home':self.current_page='Dashboard'
        if not hasattr(self,'outlined_page'):self.outlined_page=None
        if not hasattr(self,'library_selected'):self.library_selected='Retrobubble' if 'Retrobubble' in self.palettes else next(iter(self.visible_palettes()),None)
        if hasattr(self,'shell'):self.shell.destroy()
        self.scroll_areas=[];self.slot_widgets={};self.library_controls={}
        self.c=THEMES[self.effective_mode()];self.rendered_mode=self.effective_mode();self.styles()
        c=self.c;self.root.configure(bg=c['bg'])
        self.shell=self.frame(self.root);self.shell.pack(fill='both',expand=True)
        self.separator(self.shell)
        header=self.frame(self.shell,c['panel']);header.pack(fill='x')
        header.columnconfigure(0,weight=1,uniform='header-edge');header.columnconfigure(2,weight=1,uniform='header-edge')
        pages=self.frame(header,c['panel']);pages.grid(row=0,column=1,pady=self.p(8))
        self.nav={}
        for index,name in enumerate(('Dashboard','Palettes','Themes','Settings')):
            if index:self.separator(pages,vertical=True)
            b=Button(pages,self,name,lambda n=name:self.navigate(n),selected=self.current_page==name,outlined=self.outlined_page==name,compact=True,navigation=True)
            b.pack(side='left',padx=self.p(3));self.nav[name]=b
        self.separator(self.shell)
        self.context=self.frame(self.shell,c['bg'])
        self.viewport=self.frame(self.shell);self.viewport.pack(fill='both',expand=True,padx=self.p(24),pady=self.p(20))
        self.page_content=self.frame(self.viewport)
        self.page_content.place(relx=.5,y=0,anchor='n',width=self.p(1200),relheight=1)
        self.viewport.bind('<Configure>',lambda e:self.page_content.place_configure(width=min(e.width,self.p(1200))))
        self.root.after_idle(self.update_caption)
        if not getattr(self.root,'_veil_caption_map_binding',None):
            self.root._veil_caption_map_binding=self.root.bind('<Map>',
                lambda event:self.root.after_idle(self.update_caption) if event.widget is self.root else None,add='+')
        self.show_page();self.sync_chrome()
    def show_about(self):
        from veil_about import show_about
        return show_about(self)
    def update_caption(self):
        if not self.root.winfo_exists():return
        self.root.title(f'Veil · {VERSION}')
        from window_chrome import theme_caption
        self.caption_results=theme_caption(self.root,self.effective_mode()=='Dark',self.c['panel'],self.c['text'])
    def install_system_about(self):
        if not hasattr(self.root,'_veil_system_about'):
            from veil_system_menu import SystemAboutMenu
            self.root._veil_system_about=SystemAboutMenu(self.root,self.show_about,app=self)
    def navigate(self,page):
        self.outlined_page=page
        super().navigate(page)
    def show_page(self):
        menu=getattr(self,'editor_menu',None)
        if menu and not menu.closed:menu.close(restore=False)
        if not hasattr(self,'page_content'):return
        for child in self.page_content.winfo_children():child.destroy()
        for child in self.context.winfo_children():child.destroy()
        self.scroll_areas=[];self.slot_widgets={};self.library_controls={};self.restore_button=NullControl()
        self.rename_open=False
        for name,button in self.nav.items():button.configure(selected=name==self.current_page,outlined=name==self.outlined_page)
        if self.current_page=='Palettes':
            self.context.pack(fill='x',before=self.viewport)
            tabs=self.frame(self.context,self.c['bg']);tabs.pack(side='top',anchor='center',pady=self.p(8))
            for index,name in enumerate(('Library','Editor')):
                if index:self.separator(tabs,vertical=True)
                Button(tabs,self,name,lambda n=name:self.change_tab(n),selected=self.current_tab==name,compact=True,navigation=True).pack(side='left')
            self.separator(self.context)
        else:self.context.pack_forget()
        getattr(self,self.PAGES[self.current_page])();self.sync_chrome()
    def alive_widget(self,name):
        w=getattr(self,name,None)
        return w if w and getattr(w,'winfo_exists',lambda:False)() else None
    def sync_chrome(self):
        if self.alive_widget('connection_indicator'):
            connected=bool(self.session and not self.failed and not self.connection_problem)
            color=('#82BD93' if self.effective_mode()=='Dark' else '#39784C') if connected else ('#D7AE70' if self.effective_mode()=='Dark' else '#9A651D') if self.incompatible_version else ('#E78282' if self.effective_mode()=='Dark' else '#A33B3B')
            self.connection_indicator.itemconfigure('status',fill=color)
            text='Connected to DaVinci Resolve' if connected else f'Resolve {self.incompatible_version} · Apply unavailable' if self.incompatible_version else 'Connect to DaVinci Resolve'
            if self.busy and not self.session:text='Connecting…'
            self.connect_button.configure(text=text,state='disabled' if self.session or self.demo or self.busy or self.closing else 'normal')
        enabled=bool(self.session and not self.failed and not self.busy and not self.demo and not self.closing)
        self.restore_button.configure(state='normal' if enabled else 'disabled')
        if self.alive_widget('workspace_apply'):self.workspace_apply.configure(state='normal' if enabled and (self.library_selected in self.visible_palettes() if self.current_tab=='Library' else self.valid()) else 'disabled')
        if self.alive_widget('validation'):
            try:self.editor();self.display_names();text=''
            except ValueError as exc:text=str(exc)
            self.validation.configure(text=text)
            if text:self.validation.pack(fill='x',pady=(0,self.p(8)),before=self.clip_preview)
            else:self.validation.pack_forget()
        if self.alive_widget('editor_delete'):self.editor_delete.configure(state='normal' if self.selection.get() in self.users and not self.busy and not self.closing and not self.storage_error else 'disabled')
        if self.alive_widget('save_button'):self.save_button.configure(state='normal' if self.valid() and not self.storage_error else 'disabled')
        for name,(card,swatch) in getattr(self,'library_cards',{}).items():
            if card.winfo_exists() and name in self.palettes:card.set_active(self.palette_is_applied(name))
        if self.alive_widget('unsaved_label'):self.unsaved_label.configure(text='Unsaved changes' if self.dirty else '')
    def home(self):
        footer=self.frame(self.page_content);footer.pack(side='bottom',fill='x',pady=(self.p(20),0))
        self.connection_group=self.frame(footer);self.connection_group.pack(anchor='center')
        self.connection_indicator=tk.Canvas(self.connection_group,width=self.p(20),height=self.p(20),bg=self.c['bg'],highlightthickness=0,takefocus=False)
        self.connection_indicator.pack(side='left',padx=(0,self.p(8)))
        self.connection_indicator.create_oval(self.p(4),self.p(4),self.p(16),self.p(16),fill='#A33B3B',outline='',tags='status')
        self.connect_button=self.button(self.connection_group,'Connect to DaVinci Resolve',self.connect,focus_outline=False)
        self.connect_button.configure(width=max(self.connect_button.font.measure(text) for text in ('Connect to DaVinci Resolve','Connected to DaVinci Resolve','Connecting…'))+self.p(24))
        self.connect_button.pack(side='left')
        area=ScrollArea(self.page_content,self);area.pack(fill='both',expand=True)
        host=area.body;host.columnconfigure(0,weight=1,uniform='module');host.columnconfigure(1,weight=1,uniform='module')
        for index,(name,desc,action) in enumerate((('Palettes','Color your editing workspace.','Explore palettes'),('Themes','A new look for Resolve.','View preview'))):
            tile=self.card(host,padding=22);tile.grid(row=0,column=index,sticky='nsew',padx=(0,self.p(18) if index==0 else 0))
            canvas=tk.Canvas(tile,height=self.p(200),bg=self.c['panel'],highlightthickness=0);canvas.pack(fill='x')
            canvas.bind('<Destroy>',lambda e,c=canvas:setattr(c,'photos',[]))
            canvas.bind('<Configure>',lambda e,c=canvas,n=name:self.draw_art(c,n))
            self.label(tile,name,size=18,bold=True,bg=self.c['panel']).pack(fill='x',pady=(self.p(18),self.p(6)))
            self.label(tile,desc,muted=True,bg=self.c['panel']).pack(fill='x')
            self.button(tile,action,lambda n=name:self.navigate(n)).pack(anchor='w',pady=(self.p(22),0))
    def draw_art(self,canvas,name):
        canvas.delete('all');w,h=canvas.winfo_width(),canvas.winfo_height();canvas.photos=[]
        if name=='Palettes':
            palette=self.palettes.get(self.library_selected,STOCK)
            for index,label in enumerate(DISPLAY_ORDER):
                row,col=divmod(index,4);pw=(w-self.p(44))/4;ph=self.p(26)
                left,right=palette[LABELS.index(label)]
                photo=image(max(2,pw-self.p(8)),ph,left,right,radius=ph/2);canvas.photos.append(photo)
                canvas.create_image(self.p(18)+col*pw,self.p(28)+row*self.p(36),image=photo,anchor='nw')
        else:
            photo=image(max(2,w-self.p(24)),max(2,h-self.p(24)),self.c['field'],radius=self.p(12));canvas.photos.append(photo)
            canvas.create_image(self.p(12),self.p(12),image=photo,anchor='nw')
            canvas.create_line(self.p(26),self.p(42),w-self.p(26),self.p(42),fill=self.c['muted'],width=2)
            for row in range(3):
                canvas.create_rectangle(self.p(28),self.p(61+31*row),self.p(73),self.p(78+31*row),fill=self.c['control'],outline='')
                canvas.create_rectangle(self.p(91),self.p(61+31*row),w-self.p(28),self.p(78+31*row),fill=self.c['selected'],outline='')
    def palette_page(self):
        if self.current_tab=='Library':
            self.library_page()
        else:self.editor_page()
    def library_page(self):
        toolbar=self.frame(self.page_content);toolbar.pack(fill='x',pady=(0,self.p(16)))
        self.library_toolbar=toolbar
        self.label(toolbar,'Search',size=10,muted=True).pack(side='left',padx=(0,self.p(12)))
        self.library_search=Field(toolbar,self,self.filter,width=16,defer_entry=True)
        search=self.library_search;search.pack(side='left')
        search.entry.bind('<KeyRelease>',lambda e:self.render_library())
        self.restore_button=self.button(toolbar,'Restore Defaults',self.restore,focus_outline=False)
        self.restore_button.pack(side='right',padx=(0,self.p(28)))
        self.workspace_apply=self.button(toolbar,'Apply Palette',lambda:self.apply_saved(self.library_selected),focus_outline=False)
        self.workspace_apply.pack(side='right',padx=(0,self.p(8)))
        self.selection_bar=self.frame(toolbar)
        self.selection_toolbar()
        self.library_area=ScrollArea(self.page_content,self);self.library_area.pack(fill='both',expand=True)
        self.library_columns=0;self.library_area.canvas.bind('<Configure>',self.library_resize,add='+');self.render_library()
    def selection_toolbar(self):
        for child in self.selection_bar.winfo_children():child.destroy()
    def select_library(self,name):
        self.library_selected=None if self.library_selected==name else name;self.selection_toolbar()
        for n,(card,swatch) in self.library_cards.items():
            card.set_selected(n==self.library_selected);self.draw_collection(swatch,n,swatch==self.root.focus_get())
        self.sync_chrome()
    def library_resize(self,event):
        self.restore_button.pack_configure(padx=(0,self.library_area.winfo_width()-event.width+self.p(12)))
        cols=max(1,min(3,event.width//self.p(225)))
        if cols!=self.library_columns:self.library_columns=cols;self.render_library()
    def render_library(self):
        if not self.alive_widget('library_area'):return
        host=self.library_area.body
        for child in host.winfo_children():child.destroy()
        cols=self.library_columns or 3
        for col in range(4):host.columnconfigure(col,weight=1 if col<cols else 0,uniform='collection' if col<cols else '')
        names=[n for n in self.visible_palettes() if self.filter.get().casefold() in n.casefold()]
        if not names:self.label(host,'No palettes match this search.' if self.filter.get() else 'Import a palette to start your collection.',muted=True).grid(sticky='w')
        self.library_cards={}
        for index,name in enumerate(names):
            card=self.card(host,padding=16);card.grid(row=index//cols,column=index%cols,sticky='nsew',padx=(0,self.p(12)),pady=(0,self.p(12)))
            swatch=tk.Canvas(card,height=self.p(72),bg=self.c['panel'],highlightthickness=0,takefocus=True,cursor='hand2')
            swatch.pack(fill='x');swatch.bind('<Configure>',lambda e,c=swatch,n=name:self.draw_collection(c,n))
            swatch.bind('<Destroy>',lambda e,c=swatch:setattr(c,'photos',[]))
            swatch.bind('<FocusIn>',lambda e,c=swatch,n=name:self.draw_collection(c,n,True))
            swatch.bind('<FocusOut>',lambda e,c=swatch,n=name:self.draw_collection(c,n))
            title=self.label(card,name,bold=True,size=12,bg=self.c['panel'],wraplength=self.p(200));title.pack(fill='x',pady=(self.p(10),self.p(4)))
            card.set_active(self.palette_is_applied(name));card.set_selected(name==self.library_selected)
            for widget in (swatch,title,card,card.back):
                widget.configure(cursor='hand2')
                widget.bind('<Button-1>',lambda e,n=name:self.select_library(n))
            swatch.bind('<Return>',lambda e,n=name:self.select_library(n));swatch.bind('<space>',lambda e,n=name:self.select_library(n))
            self.library_cards[name]=(card,swatch)
    def draw_collection(self,canvas,name,focused=False):
        w,h=max(2,canvas.winfo_width()),canvas.winfo_height();canvas.delete('all');canvas.photos=[]
        if focused:
            canvas.photos.append(image(w,h,self.c['focus'],radius=self.p(10)))
            canvas.create_image(0,0,image=canvas.photos[-1],anchor='nw')
            inset=self.p(2)
            canvas.photos.append(image(max(2,w-2*inset),max(2,h-2*inset),canvas.cget('bg'),radius=self.p(8)))
            canvas.create_image(inset,inset,image=canvas.photos[-1],anchor='nw')
        for index,label in enumerate(DISPLAY_ORDER):
            row,col=divmod(index,8);pw=(w-self.p(12))/8;ph=self.p(19)
            left,right=self.palettes[name][LABELS.index(label)]
            canvas.photos.append(image(max(2,pw-self.p(3)),ph,left,right,radius=ph/2))
            canvas.create_image(self.p(7)+col*pw,self.p(9)+row*self.p(27),image=canvas.photos[-1],anchor='nw')
    def palette_is_applied(self,name):
        return self.applied is not None and self.applied_name==name and fingerprint(self.palettes[name],self.palette_names.get(name,list(LABELS)))==self.applied
    def editor_button(self,parent,text,command,primary=False,**kwargs):
        return self.button(parent,text,command,primary=primary,polished=True,**kwargs)
    def editor_field(self,parent,variable,width=18):
        return Field(parent,self,variable,width,polished=True)
    def pick(self,label,index):
        from veil_color_picker import ColorPicker
        picker=ColorPicker(self,self.safe_color(self.values[label][index].get()),
                           self.names[label].get(),'Primary' if index==0 else 'Secondary')
        color=picker.show()
        if color:self.values[label][index].set(color)
    def open_editor_menu(self,trigger,entries):
        menu=getattr(self,'editor_menu',None)
        if menu and not menu.closed:menu.close()
        self.editor_menu=RoundedMenu(self,trigger,entries)
    def show_palette_menu(self):
        enabled=not self.busy and not self.closing
        self.open_editor_menu(self.palette_selector,[(name,lambda n=name:self.choose_palette(n),enabled) for name in self.visible_palettes()])
    def show_actions_menu(self):
        ready=not self.busy and not self.closing
        valid=ready and self.valid(); stored=ready and not self.storage_error
        self.open_editor_menu(self.actions_button,[
            ('New Palette',self.new_palette,ready),
            ('Rename',lambda:self.start_rename(self.selection.get()),stored and self.selection.get() in self.palettes),None,
            ('Undo  ·  Ctrl+Z',self.undo_edit,ready and bool(getattr(self,'undo_stack',[]))),
            ('Redo  ·  Ctrl+Shift+Z',self.redo_edit,ready and bool(getattr(self,'redo_stack',[]))),None,
            ('Save  ·  Ctrl+S',self.save,valid and stored),
            ('Save As  ·  Ctrl+Shift+S',self.save_as,valid and stored),None,
            ('Import',self.import_palette,ready),
            ('Export',self.export_palette,valid),None,
            ('Delete',lambda:self.delete_palette(self.selection.get()),stored and self.selection.get() in self.users)])
    def reset_undo(self):
        self.undo_stack=[];self.redo_stack=[];self.undo_snapshot=self.raw_snapshot()
        self.undo_key=None;self.undo_time=0
    def edited(self,*args):
        if not self.loading and hasattr(self,'undo_snapshot'):
            state=self.raw_snapshot();now=time.monotonic();key=args[0] if args else None
            if state!=self.undo_snapshot:
                self.redo_stack=[]
                if key!=self.undo_key or now-self.undo_time>.65:
                    self.undo_stack.append(self.undo_snapshot)
                    self.undo_stack=self.undo_stack[-100:]
                self.undo_snapshot=state;self.undo_key=key;self.undo_time=now
        super().edited(*args)
    def undo_shortcut(self,event=None):
        if self.current_page=='Palettes' and self.current_tab=='Editor':
            self.undo_edit();return 'break'
    def undo_edit(self):
        if self.busy or self.closing or not getattr(self,'undo_stack',[]):return
        self.redo_stack.append(self.raw_snapshot())
        self.restore_edit(self.undo_stack.pop(),'Undid the last palette edit.')
    def redo_shortcut(self,event=None):
        if self.current_page=='Palettes' and self.current_tab=='Editor':
            self.redo_edit();return 'break'
    def redo_edit(self):
        if self.busy or self.closing or not getattr(self,'redo_stack',[]):return
        self.undo_stack.append(self.raw_snapshot())
        self.restore_edit(self.redo_stack.pop(),'Redid the last palette edit.')
    def restore_edit(self,state,message):
        colors,names=state
        self.loading=True
        try:
            for label,pair,name in zip(LABELS,colors,names):
                for variable,color in zip(self.values[label],pair):variable.set(color)
                self.names[label].set(name)
        finally:self.loading=False
        self.undo_snapshot=self.raw_snapshot();self.undo_key=None;self.undo_time=0
        self.refresh_editor();self.set_status(message)
    def choose_palette(self,name):
        before=(self.selection.get(),self.baseline)
        super().choose_palette(name)
        if (self.selection.get(),self.baseline)!=before:self.reset_undo()
    def new_palette(self):
        if self.busy or self.closing or not self.confirm_discard():return
        name='Untitled palette';number=2
        while name in self.palettes:
            name=f'Untitled palette {number}';number+=1
        self.loading=True
        try:
            self.selection.set(name);self.show_palette(STOCK)
            for label in LABELS:self.names[label].set(label)
        finally:self.loading=False
        self.baseline=None;self.reset_undo();self.active_slot=DISPLAY_ORDER[0]
        self.current_page='Palettes';self.current_tab='Editor';self.outlined_page='Palettes'
        self.show_page();self.set_status('New Palette. Choose your colors, then Save As to add it to the Library.')
    def editor_page(self):
        if self.selection.get() in builtin_palettes():self.selection.set('New Palette')
        toolbar=self.frame(self.page_content);toolbar.pack(fill='x',pady=(0,self.p(16)))
        self.palette_selector=self.editor_button(toolbar,self.selection.get(),self.show_palette_menu,dropdown=True,text_align='left')
        self.palette_selector.configure(width=self.p(200));self.palette_selector.pack(side='left')
        self.actions_button=self.editor_button(toolbar,'Actions',self.show_actions_menu,dropdown=True);self.actions_button.pack(side='left',padx=self.p(12))
        self.unsaved_label=self.label(toolbar,'',size=10,muted=True);self.unsaved_label.pack(side='left',padx=self.p(8))
        self.separator(self.page_content)
        self.rename_bar=self.frame(self.page_content);self.rename_bar.pack(fill='x')
        self.editor_scroll=ScrollArea(self.page_content,self);self.editor_scroll.pack(fill='both',expand=True,pady=(self.p(18),0))
        self.editor_body=self.editor_scroll.body;self.editor_body.columnconfigure(0,weight=1)
        self.slot_panel=Panel(self.editor_body,self,padding=18,editor_surface=True);self.slot_panel.grid(row=0,column=0,sticky='new',padx=(0,self.p(18)))
        self.slots_area=self.frame(self.slot_panel,self.c['panel']);self.slots_area.pack(fill='x');self.slots_area.body=self.slots_area
        self.detail_area=self.frame(self.editor_body);self.detail_area.body=self.detail_area
        self.slot_columns=4;self.editor_compact=None
        self.editor_scroll.canvas.bind('<Configure>',self.editor_resize,add='+')
        for col in range(4):self.slots_area.columnconfigure(col,weight=1,uniform='slots')
        for index,label in enumerate(DISPLAY_ORDER):
            cell=self.frame(self.slots_area,self.c['panel'])
            cell.grid(row=index//4,column=index%4,sticky='nsew',padx=(0 if index%4==0 else self.p(10),0),pady=(0,self.p(24) if index//4<3 else 0))
            pill=Pill(cell,self,*[self.safe_color(v.get()) for v in self.values[label]],height=48,command=lambda n=label:self.select_slot(n));pill.pack(fill='x')
            title=self.label(cell,self.names[label].get(),size=11,bg=self.c['panel'],wraplength=self.p(165));title.pack(fill='x',padx=self.p(5),pady=(self.p(10),0))
            self.slot_widgets[label]=(cell,title,pill,index)
        self.slots_area.bind('<Configure>',lambda e:self.root.after_idle(self.fit_inspector))
        self.editor_resize(type('Size',(),{'width':self.page_content.winfo_width()})())
    def editor_resize(self,event):
        compact=event.width<self.p(1000)
        if compact==self.editor_compact:return
        self.editor_compact=compact;self.detail_area.grid_forget()
        self.editor_body.columnconfigure(1,minsize=0 if compact else self.p(350))
        if compact:
            self.detail_area.grid(row=1,column=0,sticky='ew',pady=(self.p(18),0));self.slot_panel.grid_configure(padx=0)
        else:
            self.detail_area.grid(row=0,column=1,sticky='new');self.slot_panel.grid_configure(padx=(0,self.p(18)))
        self.select_slot(self.active_slot)
    def fit_inspector(self):
        if not self.alive_widget('inspector_panel'):return
        panel=self.inspector_panel
        if self.editor_compact:panel.pack_propagate(True)
        else:
            height=self.slot_panel.winfo_reqheight()
            panel.pack_propagate(False)
            if int(panel.cget('height'))!=height:panel.configure(height=height)
    def draw_slot(self,label):
        cell,title,pill,index=self.slot_widgets[label]
        title.configure(text=self.names[label].get());pill.left,pill.right=[self.safe_color(v.get()) for v in self.values[label]]
        pill.selected=label==self.active_slot;pill.draw()
    def select_slot(self,label):
        self.active_slot=label
        for name in self.slot_widgets:self.draw_slot(name)
        if not self.alive_widget('detail_area'):return
        parent=self.detail_area.body
        for child in parent.winfo_children():child.destroy()
        panel=Panel(parent,self,padding=20,editor_surface=True);panel.pack(fill='x');self.inspector_panel=panel
        self.label(panel,'Color inspector',size=15,bold=True,bg=self.c['panel']).pack(fill='x',pady=(0,self.p(12)))
        controls=self.frame(panel,self.c['panel']);controls.pack(fill='both',expand=not self.editor_compact)
        name_host=self.frame(controls,self.c['panel']) if self.editor_compact else controls
        if self.editor_compact:
            for col in range(3):controls.columnconfigure(col,weight=1,uniform='inspector')
            name_host.grid(row=0,column=0,sticky='nsew',padx=(0,self.p(6)))
        name_field=self.editor_field(name_host,self.names[label],width=18);name_field.pack(fill='x',pady=(0,self.p(10 if self.editor_compact else 20)))
        self.endpoint_chips=[]
        for index,text in enumerate(('Primary','Secondary')):
            host=self.frame(controls,self.c['panel']) if self.editor_compact else controls
            if self.editor_compact:host.grid(row=0,column=index+1,sticky='nsew',padx=(self.p(6),self.p(6) if index==0 else 0))
            row=self.frame(host,self.c['panel']);row.pack(fill='x',expand=not self.editor_compact,pady=(0,self.p(10)))
            picker=self.editor_button(row,text,lambda n=label,i=index:self.pick(n,i),compact=True,dropdown=True)
            picker.configure(width=picker.font.measure('Secondary')+self.p(40),height=self.p(40));picker.pack(side='left')
            chip=ColorChip(row,self,*[self.safe_color(self.values[label][index].get())]*2,height=40,command=lambda n=label,i=index:self.pick(n,i),label='Choose '+text.lower()+' color');chip.configure(width=self.p(40));chip.pack(side='left',padx=self.p(6));self.endpoint_chips.append(chip)
            color_field=self.editor_field(row,self.values[label][index],width=9);color_field.pack(side='left',fill='x',expand=True)
        self.validation=self.label(panel,'',size=10,bg=self.c['panel'],anchor_override='center',wraplength=self.p(240))
        self.clip_preview=Pill(panel,self,*[self.safe_color(v.get()) for v in self.values[label]],height=40);self.clip_preview.pack(fill='x',pady=(self.p(8),0))
        self.root.after_idle(self.fit_inspector)
        self.sync_chrome()
    def draw_clip(self):
        if self.alive_widget('clip_preview'):
            self.clip_preview.left,self.clip_preview.right=[self.safe_color(v.get()) for v in self.values[self.active_slot]];self.clip_preview.draw()
            for index,chip in enumerate(self.endpoint_chips):chip.left=chip.right=self.safe_color(self.values[self.active_slot][index].get());chip.draw()
    def refresh_editor(self):
        self.render_job=None
        if self.current_page=='Palettes' and self.current_tab=='Editor':
            for name in self.slot_widgets:self.draw_slot(name)
            self.draw_clip()
        self.sync_chrome()
    def start_rename(self,name):
        if self.busy or self.closing:return
        if name not in self.palettes:self.set_status('Save this draft before renaming.');return
        parent=self.selection_bar if self.current_tab=='Library' else self.rename_bar
        for child in parent.winfo_children():child.destroy()
        self.rename_open=True;self.rename_value=tk.StringVar(self.root,value=name)
        field=self.field(parent,self.rename_value,width=26);field.pack(side='left')
        self.button(parent,'Confirm',lambda:self.finish_rename(name),compact=True).pack(side='left',padx=self.p(8))
        self.button(parent,'Cancel',self.cancel_rename,compact=True).pack(side='left')
        self.rename_error=self.label(parent,'',size=10,muted=True);self.rename_error.pack(side='left',padx=self.p(10))
        field.entry.bind('<Return>',lambda e:self.finish_rename(name));field.entry.bind('<Escape>',lambda e:self.cancel_rename())
        field.entry.focus_set();field.entry.selection_range(0,'end')
    def cancel_rename(self):self.rename_open=False;self.show_page()
    def finish_rename(self,old):
        try:
            if self.storage_error:raise RuntimeError('Saved palette storage needs attention.')
            new=self.library.rename(old,self.rename_value.get())
            self.palettes,self.users,self.palette_names=self.library.palettes,self.library.users,self.library.names
            if self.selection.get()==old:self.selection.set(new) # raw draft and baseline unchanged
            if self.applied_name==old and old not in builtin_palettes():self.applied_name=new
            elif self.applied_name==old+' (edited)':self.applied_name=new+' (edited)'
            self.library_selected=new;self.rename_open=False;self.show_page()
            self.set_status('Created '+new+'.' if old in builtin_palettes() and old!=new else 'Renamed palette.','success')
        except Exception as exc:self.rename_error.configure(text=str(exc))
    def export_selected(self):
        name=self.library_selected
        if name not in self.visible_palettes():return
        path=filedialog.asksaveasfilename(parent=self.root,title='Export palette',initialfile=name,defaultextension='.json',filetypes=[('Palette JSON','*.json'),('Hex palette','*.hex')])
        if path:
            try:self.library.export(path,name,self.palettes[name],self.palette_names.get(name,list(LABELS)));self.set_status(self.export_feedback(path),'success')
            except Exception as exc:self.error(exc)
    def export_feedback(self,path):
        return 'Exported 16 colors with their names. JSON retains both gradient endpoints.' if Path(path).suffix.lower()=='.hex' else 'Exported palette.'
    def export_palette(self):
        try:
            colors=self.editor();names=self.display_names()
            path=filedialog.asksaveasfilename(parent=self.root,title='Export palette',initialfile=self.selection.get(),defaultextension='.json',filetypes=[('Palette JSON','*.json'),('Hex palette','*.hex')])
            if path:
                self.library.export(path,self.selection.get(),colors,names)
                self.set_status(self.export_feedback(path),'success')
        except Exception as exc:self.error(exc)
    def save_named(self,name):
        result=super().save_named(name)
        if result:
            self.library_selected=self.selection.get()
            if self.current_page=='Palettes':self.show_page()
            self.set_status('Saved '+self.selection.get()+'.','success')
        return result
    def request_palette_name(self):
        from veil_dialogs import PaletteDialog
        name=self.selection.get()
        return PaletteDialog(self,'save',name+' copy' if name in self.palettes else name,self.editor()).show()
    def confirm_delete_palette(self,name):
        from veil_dialogs import PaletteDialog
        return PaletteDialog(self,'delete',name,self.palettes.get(name)).show()
    def confirm_replace_palette(self,name):
        from veil_dialogs import PaletteDialog
        return PaletteDialog(self,'replace',name,self.editor()).show()
    def import_palette(self):
        try:
            path=filedialog.askopenfilename(parent=self.root,title='Import palette',filetypes=[('Palette files','*.json *.hex'),('Hex palette','*.hex'),('Palette JSON','*.json')])
            if not path:return
            palette_name,colors,aliases=self.library.read_import(path)
            if not self.confirm_discard():return
            self.loading=True;self.show_palette(colors)
            for label,alias in zip(LABELS,aliases):self.names[label].set(alias)
            self.selection.set(palette_name);self.loading=False;self.baseline=None
            self.reset_undo()
            self.continue_editing();self.set_status('Imported draft. Save to keep it; Apply updates Resolve.')
        except Exception as exc:self.loading=False;self.error(exc)
    def themes(self):
        from studio_themes import build_themes
        build_themes(self)
    def settings(self):
        self.label(self.page_content,'Settings',size=18,bold=True).pack(anchor='w',pady=(0,self.p(18)))
        area=ScrollArea(self.page_content,self);area.pack(fill='both',expand=True)
        panel=self.card(area.body,padding=20);panel.pack(fill='x')
        self.label(panel,'Veil appearance',size=12,bold=True,bg=self.c['panel']).pack(anchor='w')
        self.label(panel,'Changes Veil’s appearance. Resolve themes are separate.',size=10,muted=True,bg=self.c['panel']).pack(anchor='w',pady=(self.p(4),self.p(14)))
        row=self.frame(panel,self.c['panel']);row.pack(fill='x')
        for mode in APPEARANCES:Button(row,self,mode,lambda m=mode:self.appearance.set(m),selected=self.appearance.get()==mode).pack(side='left',padx=(0,self.p(8)))
        updates=self.card(area.body,padding=20);updates.pack(fill='x',pady=(self.p(14),0))
        self.label(updates,'Updates',size=12,bold=True,bg=self.c['panel']).pack(anchor='w')
        self.label(updates,'Stable releases from Omen2LLC on GitHub.',size=10,muted=True,bg=self.c['panel']).pack(anchor='w',pady=(self.p(4),self.p(12)))
        self.button(updates,'Check for updates',lambda:veil_update_ui.check_in_background(self,manual=True)).pack(anchor='w')
        self.diagnostic_button=self.button(area.body,'Show compatibility & recovery',self.toggle_diagnostics,compact=True);self.diagnostic_button.pack(anchor='w',pady=(self.p(20),self.p(8)))
        self.diagnostics=self.frame(area.body);self.diagnostics_open=False
    def toggle_diagnostics(self):
        self.diagnostics_open=not self.diagnostics_open
        if not self.diagnostics_open:self.diagnostics.pack_forget();self.diagnostic_button.configure(text='Show compatibility & recovery');return
        self.diagnostic_button.configure(text='Hide compatibility & recovery')
        for child in self.diagnostics.winfo_children():child.destroy()
        self.diagnostics.pack(fill='x')
        self.label(self.diagnostics,'Latest operation',bold=True).pack(anchor='w',pady=(self.p(4),self.p(5)))
        self.label(self.diagnostics,var=self.status,size=10,muted=True,wraplength=self.p(900)).pack(anchor='w',pady=(0,self.p(10)))
        for text in ('Native palette profile: Resolve Studio 21.1.1.10 only. Other builds are disabled.','Normal close restores colors, menu names and dots. Keep the Clip Color menu closed during Apply or Restore.','Palettes replace 16 existing slots. Unassigned audio follows slot 6; video follows slot 9.','If recovery fails, restart Resolve before continuing.','Operation timings and errors: veil.log','Shortcuts: Ctrl+S Save · Ctrl+Shift+S Save As · Ctrl+O Import · Alt+1–4 Navigation'):
            self.label(self.diagnostics,text,size=10,muted=True,wraplength=self.p(900)).pack(anchor='w',pady=self.p(5))
