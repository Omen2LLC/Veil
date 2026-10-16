"""Cherry Blossom approved preview. Illustration is not a Resolve capture."""
import tkinter as tk
import queue,logging
from studio_controls import Button,image
from studio_fonts import REGULAR,SEMIBOLD
from resolve_theme import load_profile,capability,apply_cherry_theme,restore_cherry_original
from application_theme import capability as application_capability,cleanup_failed_start

STATES=('Normal','Hover','Selected','Disabled','Warning','Error')

class ThemePreview(tk.Canvas):
    """AI-edited Fusion concept asset. It is not native coverage evidence."""
    def __init__(self,parent,app,profile):
        from pathlib import Path
        self.app=app;self.profile=profile;self.photos=[];self.asset_width=None
        self.folder=Path(__file__).resolve().parent/'Themes'/'Fusion-preview'
        self.sizes=sorted(int(p.stem) for p in self.folder.glob('*.png'))
        if not self.sizes:raise FileNotFoundError('Fusion theme preview is missing.')
        super().__init__(parent,height=app.p(420),bg=app.c['panel'],highlightthickness=0,bd=0,takefocus=False)
        self.bind('<Configure>',self.draw)
        self.bind('<Destroy>',lambda event:self.photos.clear())
    def draw(self,event=None):
        w=max(2,self.winfo_width())
        size=max((s for s in self.sizes if s<=w),default=self.sizes[0])
        if size!=self.asset_width:
            self.photos=[tk.PhotoImage(file=str(self.folder/(str(size)+'.png')))]
            self.asset_width=size
        photo=self.photos[0]
        if int(self.cget('height'))!=photo.height():self.configure(height=photo.height())
        self.delete('all');self.create_image(w/2,0,image=photo,anchor='n')

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
    title=app.label(heading,'Cherry Blossom',size=20,bold=True,bg=app.c['panel']);title.grid(row=0,column=0,sticky='w')
    scope=app.label(heading,'Experimental',size=10,muted=True,bg=app.c['panel']);scope.grid(row=0,column=1,sticky='e')
    desc=app.label(panel,'A softer workspace for Resolve.',muted=True,bg=app.c['panel'])
    desc.pack(fill='x',pady=(app.p(6),app.p(24)))
    preview=ThemePreview(panel,app,profile);preview.pack(fill='x');app.theme_preview=preview
    caption=app.label(panel,'Fusion preview · viewers hidden · concept image',size=9,muted=True,bg=app.c['panel'])
    caption.pack(fill='x',pady=(app.p(8),app.p(20)))
    app.theme_state_buttons={}
    def status_text(fusion,main):
        if main.get('can_start') and fusion_start_allowed(fusion):
            return 'Ready to apply' if fusion.get('can_apply') else 'Ready to open with Cherry Blossom'
        if main.get('can_cleanup'):return 'Startup needs attention. Use Clear stalled startup below.'
        if 'running' in main.get('status','').lower():return 'Close Resolve normally to apply or restore the theme.'
        return main.get('reason') or fusion.get('reason') or 'Theme unavailable. See Details.'
    def capability_signature(fusion,main):
        return tuple(fusion.get(key) for key in ('status','reason','can_apply','can_restore'))+tuple(main.get(key) for key in ('status','reason','can_start','can_restore','can_cleanup'))
    last_signature=[capability_signature(support,application)]
    app.theme_status_label=app.label(panel,status_text(support,application),size=10,bold=True,bg=app.c['panel'])
    app.theme_status_label.pack(fill='x',pady=(0,app.p(12)))
    row=app.frame(panel,app.c['panel']);row.pack(fill='x',pady=(0,app.p(10)))
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
                    app.theme_status_label.configure(text=prefix+str(error) if error else status_text(app.theme_capability,app.application_theme_capability))
            except Exception:
                logging.exception('Cherry Blossom completion UI failed')
                if app.alive_widget('theme_status_label'):app.theme_status_label.configure(text='Theme operation ended. Reopen Themes to check its status.')
        tasks={'apply':lambda:apply_cherry_theme(folder,progress.put),'start':lambda:apply_cherry_theme(folder,progress.put),'restore':lambda:restore_cherry_original(folder,progress.put),'cleanup':lambda:cleanup_failed_start(folder,confirm_no_project=True)}
        app.root.after(100,show_progress)
        app.worker.submit('Cherry Blossom '+action,tasks[action],complete)
    app.theme_apply_button=app.button(row,'Apply theme',lambda:operation('apply'),primary=True,state='normal' if application['can_start'] and fusion_start_allowed(support) and not app.busy else 'disabled')
    # Backward-compatible controller alias, one visible action.
    app.theme_start_button=app.theme_apply_button
    app.theme_restore_button=app.button(row,'Restore original',lambda:operation('restore'),state='normal' if (support['can_restore'] or application['can_restore']) and not app.busy else 'disabled')
    app.theme_recovery_button=app.button(row,'Clear stalled startup',lambda:operation('cleanup'),state='normal' if application.get('can_cleanup') and not app.busy else 'disabled')
    action_buttons=(app.theme_apply_button,app.theme_restore_button,app.theme_recovery_button)
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
    note=app.label(panel,'Save your work and close Resolve before applying. Native coverage is still in progress.',size=10,muted=True,bg=app.c['panel'])
    note.pack(fill='x',pady=(0,app.p(4)))
    def update_controls(result=None,main=None):
        if result is None:result=capability(folder)
        if main is None:main=application_capability(folder)
        app.theme_capability=result;app.application_theme_capability=main
        app.theme_apply_button.configure(state='normal' if main['can_start'] and fusion_start_allowed(result) and not app.busy else 'disabled')
        app.theme_start_button.configure(state='normal' if main['can_start'] and fusion_start_allowed(result) and not app.busy else 'disabled')
        app.theme_restore_button.configure(state='normal' if (result['can_restore'] or main['can_restore']) and not app.busy else 'disabled')
        app.theme_recovery_button.configure(state='normal' if main.get('can_cleanup') and not app.busy else 'disabled')
        layout_actions(max(app.p(120),panel.winfo_width()-app.p(48)))
        last_signature[0]=capability_signature(result,main)
    app.refresh_theme_controls=update_controls
    details=app.frame(area.body);shown=[False]
    def toggle():
        shown[0]=not shown[0]
        if shown[0]:details.pack(fill='x');app.theme_details_button.configure(text='Hide details')
        else:details.pack_forget();app.theme_details_button.configure(text='Details')
    app.theme_details_button=app.button(area.body,'Details',toggle,compact=True)
    app.theme_details_button.pack(anchor='w',pady=(app.p(18),app.p(10)))
    detail_labels=[]
    for line in ('Resolve '+support['reviewed_version']+' · experimental appearance integration',
                 'Apply theme installs the Fusion skin and opens a themed Resolve session. The Fusion skin stays installed until Restore original; application styling lasts for that session.',
                 'The preview is an illustrated empty Fusion layout, not a Resolve capture. Complete native coverage remains unverified.',
                 'Projects, media, clip colors, native icons and controls are preserved. Version checks, backups and guarded restoration remain enabled.',
                 'Compatibility: '+str(support.get('reason') or support.get('status','')),
                 'Session: '+status_text(support,application)):
        label=app.label(details,line,size=10,muted=True);label.pack(fill='x',pady=app.p(4));detail_labels.append(label)
    def resize(event):
        width=max(app.p(120),event.width-app.p(48))
        for label in (desc,caption,note,app.theme_status_label):label.configure(wraplength=width)
        for label in detail_labels:label.configure(wraplength=max(app.p(120),event.width))
        if event.width<app.p(580):scope.grid_configure(row=1,column=0,columnspan=2,sticky='w',pady=(app.p(5),0))
        else:scope.grid_configure(row=0,column=1,columnspan=1,sticky='e',pady=0)
        layout_actions(width)
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
