"""Serialize Resolve work without calling Tk from a worker thread."""
from concurrent.futures import ThreadPoolExecutor
import logging
import time
from types import SimpleNamespace
from palette_core import LABELS
from resolve_actions import ResolveActions

class ResolveWorker:
    def __init__(self):
        self.executor=ThreadPoolExecutor(max_workers=1,thread_name_prefix='OmenResolve')
        self.jobs=[]

    def submit(self,label,work,complete):
        def timed():
            start=time.monotonic()
            try:return work()
            finally:logging.info('Resolve %s finished in %.3fs',label,time.monotonic()-start)
        self.jobs.append((self.executor.submit(timed),complete))

    def drain(self):
        # Called only by Tk's main thread. Workers return values, never UI calls.
        while self.jobs and self.jobs[0][0].done():
            future,complete=self.jobs.pop(0)
            try:value=future.result();error=None
            except Exception as exc:value=None;error=exc
            try:complete(value,error)
            except Exception:logging.exception('Resolve completion callback failed')

    def shutdown(self):
        self.executor.shutdown(wait=True)

def apply_palette(session,menu,colors,names):
    def fail(exc):raise exc
    payload=SimpleNamespace(editor=lambda:colors,
        names={label:SimpleNamespace(get=lambda value=value:value) for label,value in zip(LABELS,names)},
        session=session,menu_names=menu,status=SimpleNamespace(set=lambda value:None),
        schedule_refresh=lambda:None,error=fail)
    ResolveActions.apply(payload)

def restore_palette(session,menu):
    errors=[]
    try:menu.set_names(list(LABELS))
    except Exception as exc:errors.append(f'Native menu names: {exc}')
    try:session.restore()
    except Exception as exc:errors.append(f'Palette and dots: {exc}')
    if errors:raise RuntimeError('Some defaults could not be restored. Restart Resolve before continuing. '+'; '.join(errors))

def check_session(session,menu,validate=True):
    if not validate:
        # A failed compatibility check must stop memory validation, not process-lifetime tracking.
        if not session.alive():raise RuntimeError('Resolve closed. Reconnect after opening it again.')
        return False
    session.check()
    if menu:menu.check()
    return session.refresh_thumbnails()
