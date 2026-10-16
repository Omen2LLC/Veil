"""Resolve actions retained from v0.22. UI and storage live in other modules."""
import logging
from tkinter import messagebox
from pathlib import Path
from palette_core import LABELS, STOCK
from palette_names import validate_names
from dot_palette import PaletteSession
from resolve_palette import UnsupportedResolveVersion
from menu_names import NativeMenuNames
HERE=Path(__file__).resolve().parent

class ResolveActions:
    def connect(self):
        if self.session:return
        session=PaletteSession(HERE)
        try:
            session.connect();self.menu_names=NativeMenuNames(session);self.session=session;self.failed=False
            self.connection.set(f'Connected · Resolve {session.version} · ready to apply')
            self.connect_button.configure(state='disabled')
            self.restore_button.configure(state='normal')
            self.status.set('Previous session detected. Restore Defaults is available.' if session.recovered else 'Connected. Choose a palette and click Apply.')
        except UnsupportedResolveVersion as exc:
            session.close();self.incompatible_version=exc.detected
            self.connection.set(f'Resolve {exc.detected} · palette Apply unavailable')
            self.set_status(str(exc))
        except Exception as exc:session.close();self.error(exc)

    def schedule_refresh(self):
        if not self.session:return
        if self.refresh_job:
            self.root.after_cancel(self.refresh_job)
        self.refresh_job=self.root.after(150,self.repaint_media_pool)

    def repaint_media_pool(self):
        self.refresh_job=None
        if not self.session or not self.session.alive():return
        try:
            self.pool_refresh.repaint(self.session.pid)
            logging.info('Requested automatic Media Pool repaint')
        except Exception as exc:
            logging.warning('Media Pool repaint skipped: %s',exc)
            self.status.set('Palette applied; Media Pool repaint skipped: '+str(exc))

    def apply(self):
        try:
            palette=self.editor()
            names=validate_names([self.names[n].get() for n in LABELS])
            if not self.session:raise RuntimeError('Connect to Resolve first.')
            previous=list(self.menu_names.names)
            self.menu_names.set_names(names)
            try:self.session.apply(palette)
            except Exception:
                self.menu_names.set_names(previous)
                raise
            self.status.set('Palette applied. Timeline, native menu, and loaded media-pool dots follow the 16 slots.')
            self.schedule_refresh()
            logging.info('Applied a palette to the verified Resolve session')
        except Exception as exc:self.error(exc)

    def restore(self):
        try:
            if not self.session:raise RuntimeError('Connect to Resolve first.')
            errors=[]
            try:self.menu_names.set_names(list(LABELS))
            except Exception as exc:errors.append(f'Native menu names: {exc}')
            try:self.session.restore()
            except Exception as exc:errors.append(f'Palette and dots: {exc}')
            if errors:raise RuntimeError('Some defaults could not be restored. Restart Resolve before continuing. '+'; '.join(errors))
            self.selection.set('Resolve Original');self.show_palette(STOCK)
            for label in LABELS:self.names[label].set(label)
            self.status.set('Original colors restored and verified.')
            self.schedule_refresh()
        except Exception as exc:self.error(exc)

    def poll(self):
        if self.session and not self.failed:
            try:
                self.session.check()
                if self.menu_names:self.menu_names.check()
                if self.session.refresh_thumbnails():self.schedule_refresh()
            except Exception as exc:
                if not self.session.alive():
                    self.session.close();self.session=None
                    self.connect_button.configure(state='normal')
                    self.connection.set('Resolve closed · open it again, then Connect')
                else:
                    self.failed=True;self.connection.set('Connection changed · restart Resolve before continuing')
                self.restore_button.configure(state='disabled')
                self.status.set(str(exc));logging.warning('%s',exc)
        self.root.after(500,self.poll)

    def close(self):
        if self.refresh_job:
            self.root.after_cancel(self.refresh_job);self.refresh_job=None
        if self.session:
            if self.menu_names and self.session.alive():
                try:self.menu_names.require_closed()
                except Exception as exc:
                    messagebox.showerror('Close the Clip Color menu first',str(exc),parent=self.root)
                    return
            if self.session.alive() and self.session.dirty:
                try:self.session.restore()
                except Exception as exc:
                    if not messagebox.askyesno('Restoration needs attention',str(exc)+'\n\nRestart Resolve to reload its original palette. Close this app anyway?',parent=self.root):return
                else:
                    try:self.pool_refresh.repaint(self.session.pid)
                    except Exception as exc:logging.warning('Media Pool repaint after restore skipped: %s',exc)
            if self.menu_names and self.session.alive():
                try:self.menu_names.close()
                except Exception as exc:
                    messagebox.showerror('Menu name restoration needs attention',str(exc)+'\n\nResolve remains connected. Restart Resolve before continuing.',parent=self.root)
                    return
            self.session.close();self.session=None;self.menu_names=None
        identity=getattr(self.root,'_taskbar_identity',None)
        if identity:
            try:identity.close()
            except Exception:logging.exception('Could not clear taskbar properties')
        # Cancel periodic callbacks only after the existing close / restoration
        # checks succeed. A cancelled close must keep all monitoring active.
        for job in self.root.tk.call('after','info'):
            self.root.after_cancel(job)
        self.root.destroy()
