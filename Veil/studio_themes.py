"""Cherry Blossom approved preview. Illustration is not a Resolve capture."""
import tkinter as tk
import queue,logging
from studio_controls import Button,image
from studio_fonts import REGULAR,SEMIBOLD
from resolve_theme import load_profile,capability,apply_cherry_theme,restore_cherry_original
from application_theme import capability as application_capability,cleanup_failed_start

STATES=('Normal','Hover','Selected','Disabled','Warning','Error')

class ThemePreview(tk.Canvas):
    """Approved Petal visual and a separate semantic state sample."""
    def __init__(self,parent,app,profile):
        import pathlib
        self.app=app;self.profile=profile;self.state_name='Selected';self.photos=[]
        self.source=tk.PhotoImage(file=str(pathlib.Path(app_theme_folder(app))/profile['preview']))
        super().__init__(parent,height=app.p(340),bg=app.c['panel'],highlightthickness=0,bd=0,takefocus=False)
        self.bind('<Configure>',self.draw)
        self.bind('<Destroy>',lambda e:setattr(self,'photos',[]))
    def set_state(self,name):
        if name not in STATES:raise ValueError('Unknown preview state.')
        self.state_name=name;self.draw()
    def draw(self,event=None):
        import math
        self.delete('all');self.photos=[]
        w=max(2,self.winfo_width());p=self.app.p;t=self.profile['tokens']
        factor=max(1,math.ceil(self.source.width()/max(1,w)))
        photo=self.source.subsample(factor);self.photos.append(photo)
        self.create_image(w/2,0,image=photo,anchor='n')
        h=photo.height()+p(52)
        if int(self.cget('height'))!=h:self.configure(height=h)
        state=self.state_name
        fill={'Normal':t['raised'],'Hover':t['hover'],'Selected':t['selected'],'Disabled':t['panel'],'Warning':t['warning'],'Error':t['error']}[state]
        sample_w=min(p(180),w-p(16));sample_h=p(30);y=photo.height()+p(12)
        self.photos.append(image(max(2,sample_w),sample_h,fill,radius=p(8)))
        self.create_image(w/2,y,image=self.photos[-1],anchor='n')
        self.create_text(w/2,y+sample_h/2,text=state+' sample',fill=t['text'],font=(REGULAR,9))

def fusion_start_allowed(support):
    return bool(support.get('can_apply') or support.get('status', '').startswith('Cherry Blossom installed'))

def build_themes(app):
    # Late import avoids a cycle with studio_ui.ScrollArea.
    from studio_ui import ScrollArea
    folder=app_theme_folder(app)
    profile=load_profile(folder);support=capability(folder);application=application_capability(folder)
    app.theme_capability=support;app.application_theme_capability=application;app.theme_profile=profile
    area=ScrollArea(app.page_content,app);area.pack(fill='both',expand=True)
    panel=app.card(area.body,padding=24);panel.pack(fill='x')
    heading=app.frame(panel,app.c['panel']);heading.pack(fill='x')
    heading.columnconfigure(0,weight=1)
    title=app.label(heading,'Cherry Blossom · Step 3 test',size=18,bold=True,bg=app.c['panel']);title.grid(row=0,column=0,sticky='w')
    scope=app.label(heading,'Experimental · Resolve + Fusion',size=10,muted=True,bg=app.c['panel']);scope.grid(row=0,column=1,sticky='e')
    desc=app.label(panel,'Step 3 Edit-page test: timeline toolbar, viewer toolbar and transport backing, alongside Inspector and filmstrip label tests. The working parameter-label and Fusion canvas changes are retained. Full-program coverage remains unverified.',muted=True,bg=app.c['panel'])
    desc.pack(fill='x',pady=(app.p(6),app.p(20)))
    preview=ThemePreview(panel,app,profile);preview.pack(fill='x');app.theme_preview=preview
    caption=app.label(panel,'Approved workspace concept · not a Resolve capture or a guarantee of complete coverage',size=9,muted=True,bg=app.c['panel'])
    caption.pack(fill='x',pady=(app.p(7),app.p(14)))
    states=app.frame(panel,app.c['panel']);states.pack(fill='x')
    app.theme_state_buttons={}
    def choose(name):
        preview.set_state(name)
        for label,button in app.theme_state_buttons.items():button.configure(selected=label==name)
    for name in STATES:
        button=Button(states,app,name,lambda n=name:choose(n),compact=True,selected=name=='Selected')
        button.grid(row=0,column=STATES.index(name),padx=(0,app.p(6)),pady=(0,app.p(6)))
        app.theme_state_buttons[name]=button
    app.label(panel,'Coverage',bold=True,bg=app.c['panel']).pack(fill='x',pady=(app.p(20),app.p(6)))
    reason=app.label(panel,'This workspace test adds petal backgrounds to shared sidebars, inspector content, Media containers, Deliver settings, Color tool containers and Project Manager bodies. Broad descendant text overrides have been removed after contrast problems in native captures. The Metadata panel and enabled fields have paired colors. This staged extension also pairs the Quick Export preset header and updates Fusion Effects Library tile gradients; native checks are pending. Native button backing and icon artwork remain intact. Custom-painted timelines, grading displays, viewers and some panels still retain Resolve’s native appearance. Live readability and behavior checks are still required.',size=10,muted=True,bg=app.c['panel'])
    reason.pack(fill='x')
    def status_text(fusion,main):
        fusion_text=fusion['reason'] if fusion['status']=='Unavailable' else fusion['status']
        main_text=main['status']
        if not main['can_start'] and main.get('reason'):main_text+=' · '+main['reason']
        return fusion_text+'\n'+main_text
    def capability_signature(fusion,main):
        return tuple(fusion.get(key) for key in ('status','reason','can_apply','can_restore'))+tuple(main.get(key) for key in ('status','reason','can_start','can_restore','can_cleanup'))
    last_signature=[capability_signature(support,application)]
    app.theme_status_label=app.label(panel,status_text(support,application),size=10,bold=True,bg=app.c['panel'])
    app.theme_status_label.pack(fill='x',before=preview,pady=(0,app.p(10)))
    row=app.frame(panel,app.c['panel']);row.pack(fill='x',before=preview,pady=(0,app.p(10)))
    def operation(action):
        if app.busy or app.closing:return
        if action=='cleanup':
            from tkinter import messagebox
            if not app.application_theme_capability.get('can_cleanup'):return
            confirmed=messagebox.askyesno('Clear stalled Resolve startup?',
                'Confirm that no Resolve window is open and no project is currently loading.\n\n'
                'This stops only the background process created by this failed Cherry Blossom launch. '
                'Do you want to clear it?',parent=app.root,default='no',icon='warning')
            if not confirmed:return
        app.busy=True;app.busy_label='Starting Cherry Blossom' if action=='start' else 'Updating Cherry Blossom'
        for button in action_buttons:button.configure(state='disabled')
        app.sync_chrome()
        app.theme_status_label.configure(text={'apply':'Checking Resolve and preparing Cherry Blossom…','start':'Checking Resolve and preparing the application session…','restore':'Checking Resolve and preparing restoration…','cleanup':'Checking the stalled startup process…'}[action])
        progress=queue.SimpleQueue();finished=[False]
        def show_progress():
            if finished[0]:return
            message=None
            while not progress.empty():message=progress.get()
            if message and app.alive_widget('theme_status_label'):app.theme_status_label.configure(text=message)
            if not finished[0]:app.root.after(100,show_progress)
        def complete(value,error):
            finished[0]=True;app.busy=False
            if error:logging.error('Cherry Blossom %s failed: %s',action,error)
            try:
                app.sync_chrome()
                if app.alive_widget('theme_status_label'):
                    app.refresh_theme_controls()
                    prefix={'apply':'Apply Theme did not complete: ','start':'Resolve startup not confirmed: ','restore':'Theme not restored: ','cleanup':'Startup not cleared: '}[action]
                    app.theme_status_label.configure(text=prefix+str(error) if error else str(value))
            except Exception:
                logging.exception('Cherry Blossom completion UI failed')
                if app.alive_widget('theme_status_label'):app.theme_status_label.configure(text='Theme operation ended. Reopen Themes to check its status.')
        tasks={'apply':lambda:apply_cherry_theme(folder,progress.put),'start':lambda:apply_cherry_theme(folder,progress.put),'restore':lambda:restore_cherry_original(folder,progress.put),'cleanup':lambda:cleanup_failed_start(folder,confirm_no_project=True)}
        app.root.after(100,show_progress)
        app.worker.submit('Cherry Blossom '+action,tasks[action],complete)
    app.theme_apply_button=app.button(row,'Apply Theme',lambda:operation('apply'),state='normal' if support['can_apply'] and application['can_start'] and not app.busy else 'disabled')
    app.theme_start_button=app.button(row,'Start Resolve',lambda:operation('start'),state='normal' if application['can_start'] and fusion_start_allowed(support) and not app.busy else 'disabled')
    app.theme_restore_button=app.button(row,'Restore Original',lambda:operation('restore'),state='normal' if (support['can_restore'] or application['can_restore']) and not app.busy else 'disabled')
    app.theme_recovery_button=app.button(row,'Clear stalled startup',lambda:operation('cleanup'),state='normal' if application.get('can_cleanup') and not app.busy else 'disabled')
    action_buttons=(app.theme_apply_button,app.theme_start_button,app.theme_restore_button,app.theme_recovery_button)
    def layout_actions(width):
        used=0;action_row=0;action_column=0
        for button in action_buttons:
            if button is app.theme_recovery_button and not app.application_theme_capability.get('can_cleanup'):
                button.grid_remove();continue
            button_width=int(button.cget('width'))+app.p(8)
            if used and used+button_width>width:action_row+=1;action_column=0;used=0
            button.grid(row=action_row,column=action_column,sticky='w',padx=(0,app.p(8)),pady=(0,app.p(6)))
            used+=button_width;action_column+=1
    layout_actions(app.p(1000))
    note=app.label(panel,'Save your work and close Resolve normally first. Apply Theme installs the Fusion look and starts a themed session; Windows approval identifies the Fusion helper as Python. Start Resolve checks both layers and installs the Fusion skin if it is original; this can also request Windows approval. Your regular shortcut uses original application styling; the Fusion skin persists until Restore Original.',size=9,muted=True,bg=app.c['panel'])
    note.pack(fill='x',before=preview,pady=(0,app.p(18)))
    def update_controls(result=None,main=None):
        if result is None:result=capability(folder)
        if main is None:main=application_capability(folder)
        app.theme_capability=result;app.application_theme_capability=main
        app.theme_apply_button.configure(state='normal' if result['can_apply'] and main['can_start'] and not app.busy else 'disabled')
        app.theme_start_button.configure(state='normal' if main['can_start'] and fusion_start_allowed(result) and not app.busy else 'disabled')
        app.theme_restore_button.configure(state='normal' if (result['can_restore'] or main['can_restore']) and not app.busy else 'disabled')
        app.theme_recovery_button.configure(state='normal' if main.get('can_cleanup') and not app.busy else 'disabled')
        layout_actions(max(app.p(120),panel.winfo_width()-app.p(48)))
        last_signature[0]=capability_signature(result,main)
    app.refresh_theme_controls=update_controls
    details=app.frame(area.body);shown=[False]
    def toggle():
        shown[0]=not shown[0]
        if shown[0]:details.pack(fill='x');app.theme_details_button.configure(text='Hide compatibility details')
        else:details.pack_forget();app.theme_details_button.configure(text='Show compatibility details')
    app.theme_details_button=app.button(area.body,'Show compatibility details',toggle,compact=True)
    app.theme_details_button.pack(anchor='w',pady=(app.p(18),app.p(10)))
    detail_labels=[]
    for line in ('Reviewed installation: DaVinci Resolve '+support['reviewed_version'],
                 'Installed scripting API: no application theme setter found.',
                 'Fusion and the earlier menu/page-bar appearance were confirmed by the user. This larger workspace expansion still needs live verification.',
                 'Apply Theme changes two Fusion skin definition files and starts a themed Resolve session. Session startup changes reviewed stylesheet colors in its own new process; Resolve.exe on disk stays unchanged.',
                 'Application changes include larger sidebar, inspector, Media, Deliver, Color container and Project Manager backgrounds, plus the previous menu/page-bar accents, SoundLibrary keyword field and Inspector caption timecode field.',
                 'Menu popup backgrounds and rows, custom-painted timeline/viewer areas, grading visuals, Fairlight DLL surfaces and unreviewed controls retain their native appearance. This is not a complete application theme.',
                 'Recipes change colors only. Narrow enabled Metadata rules pair petal backgrounds with native dark text; broad descendant text overrides are removed. Native dark button backing is retained. Native fonts, bitmap icons, dimensions, semantic color declarations and interaction properties remain unchanged; runtime behavior still needs live verification.',
                 'Version/hash checks, original backup and atomic replacement guard Fusion installation and restoration. Startup refuses restricted Codex accounts and an already-running Resolve.',
                 'Apply Theme and Start Resolve launch only when Resolve is closed. Neither application is minimized or closed automatically. A startup timeout is reported without interrupting a possibly opening project.',
                 'All Resolve pages, menus, dialogs, interaction states and playback: comprehensive verification not performed.',
                 'Theme profile and findings: Themes/Cherry Blossom.json, Themes/Compatibility.json and Themes/Application/recipe.json.'):
        label=app.label(details,line,size=10,muted=True);label.pack(fill='x',pady=app.p(4));detail_labels.append(label)
    def resize(event):
        width=max(app.p(120),event.width-app.p(48))
        for label in (desc,caption,reason,note,app.theme_status_label):label.configure(wraplength=width)
        for label in detail_labels:label.configure(wraplength=max(app.p(120),event.width))
        if event.width<app.p(580):scope.grid_configure(row=1,column=0,columnspan=2,sticky='w',pady=(app.p(5),0))
        else:scope.grid_configure(row=0,column=1,columnspan=1,sticky='e',pady=0)
        layout_actions(width)
        columns=3 if event.width<app.p(670) else 6
        for index,name in enumerate(STATES):app.theme_state_buttons[name].grid_configure(row=index//columns,column=index%columns)
    panel.bind('<Configure>',resize,add='+')
    # Observe external, normal Resolve closure without hashing resources on Tk's
    # thread. Reuse the existing serialized worker and stop when this card dies.
    refresh_id=[None]
    def alive():return not app.closing and bool(panel.winfo_exists())
    def schedule_refresh():
        if alive():refresh_id[0]=app.root.after(3000,poll_status)
    def poll_status():
        refresh_id[0]=None
        if not alive():return
        if app.busy:schedule_refresh();return
        def refreshed(value,error):
            if not alive():return
            if not error and not app.busy:
                fusion,main=value
                changed=capability_signature(fusion,main)!=last_signature[0]
                update_controls(fusion,main)
                if changed:app.theme_status_label.configure(text=status_text(fusion,main))
            elif error:logging.warning('Cherry Blossom status refresh failed: %s',error)
            schedule_refresh()
        app.worker.submit('Cherry Blossom status',lambda:(capability(folder),application_capability(folder)),refreshed)
    def stop_refresh(event):
        if event.widget is panel and refresh_id[0] is not None:
            app.root.after_cancel(refresh_id[0]);refresh_id[0]=None
    panel.bind('<Destroy>',stop_refresh,add='+')
    schedule_refresh()

def app_theme_folder(app):
    # QA swaps the same HERE used by the library to keep user data isolated.
    import studio_ui
    return studio_ui.HERE
