"""Guarded experimental Fusion theme; independent of clip-color memory patches."""
import json,re,sys,logging,traceback
from pathlib import Path

class ThemeUnavailable(RuntimeError):pass

REASON='Experimental Fusion skin. Additional application surfaces use a separate themed session; whole-application coverage remains unverified.'
INSTALL=Path('C:/Program Files/Blackmagic Design/DaVinci Resolve')
TARGET=INSTALL/'Skins/Fusion.fuskin'
# Only the independently reviewed Step 1 candidate may be upgraded automatically.
REVIEWED_UPGRADE_SKINS={'dfd01ab2d90c085571343e7c714cbba2462497951ca36baf8da0ed6a51670442'}

def load_profile(folder):
    data=json.loads((Path(folder)/'Themes/Cherry Blossom.json').read_text(encoding='utf-8'))
    if data.get('schema')!=1 or data.get('name')!='Cherry Blossom':raise ValueError('Invalid theme profile.')
    required={'background','panel','raised','border','text','muted','hover','selected','disabled','accent','on_accent','warning','error','viewer'}
    if set(data.get('tokens',{}))!=required:raise ValueError('Incomplete theme tokens.')
    if not all(re.fullmatch('#[0-9A-Fa-f]{6}',v) for v in data['tokens'].values()):raise ValueError('Invalid theme color.')
    colors=['#E6CED5','#DDB0BC','#D9A0B0','#D9829B','#D46986']
    if data.get('source_colors')!=colors:raise ValueError('Cherry Blossom palette has changed.')
    if any(data['tokens'][key] not in colors for key in ('background','panel','raised','border','hover','selected','accent','viewer')):raise ValueError('Theme surfaces must use the supplied palette.')
    return data

def capability(folder):
    from theme_transaction import digest
    from resolve_palette import file_version
    folder=Path(folder)
    report=json.loads((Path(folder)/'Themes/Compatibility.json').read_text(encoding='utf-8'))
    recipe=json.loads((folder/'Themes/Skin recipe.json').read_text())
    try:
        if file_version(str(INSTALL/'Resolve.exe'))!=recipe['resolve_version']:raise ThemeUnavailable('Resolve version differs from the tested build.')
        current=digest(TARGET)
        backup=folder/'Backup/Themes/Original-Fusion.fuskin'
        legacy=folder.parent.parent/'Oxygen-Fusion-Skin-Test/Original-Fusion.fuskin'
        original_available=any(p.exists() and digest(p)==recipe['source_sha256'] for p in (backup,legacy))
        if current==recipe['source_sha256']:status='Original skin installed';apply=True;restore=False
        elif current==recipe['candidate_sha256']:status='Cherry Blossom installed · Fusion skin';apply=False;restore=original_available
        elif current in REVIEWED_UPGRADE_SKINS and current in recipe.get('legacy_candidate_sha256',[]):
            status='Step 1 Cherry Blossom installed · Step 2 upgrade available';apply=original_available;restore=original_available
        elif current in recipe.get('legacy_candidate_sha256',[]):status='Previous theme installed · restore before applying Cherry Blossom';apply=False;restore=original_available
        else:raise ThemeUnavailable('Unknown skin resource. Apply and Restore are unavailable for this installation.')
        return dict(can_apply=apply,can_restore=restore,reason=REASON,status=status,reviewed_version=recipe['resolve_version'],report=report)
    except (OSError,RuntimeError) as exc:
        return dict(can_apply=False,can_restore=False,reason=str(exc),status='Unavailable',reviewed_version=recipe['resolve_version'],report=report)

def direct_operation(folder,action,progress=lambda message:None,guard=lambda:None):
    import shutil
    from theme_transaction import digest,atomic_bytes,SkinTransaction,require_resolve_closed
    from resolve_palette import file_version
    from fusion_skin_patch import build_candidate
    guard()
    folder=Path(folder);recipe=json.loads((folder/'Themes/Skin recipe.json').read_text())
    progress('Checking that Resolve is closed…')
    if file_version(str(INSTALL/'Resolve.exe'))!=recipe['resolve_version']:raise ThemeUnavailable('Resolve version differs from the tested build.')
    require_resolve_closed()
    current=digest(TARGET);legacy_hashes=recipe.get('legacy_candidate_sha256',[]);known=(recipe['source_sha256'],recipe['candidate_sha256'],*legacy_hashes)
    if current not in known:raise ThemeUnavailable('Installed skin has changed. Refusing to overwrite it.')
    storage=folder/'Backup/Themes';storage.mkdir(parents=True,exist_ok=True)
    backup=storage/'Original-Fusion.fuskin';candidate=storage/'Cherry-Blossom-Fusion.fuskin'
    if not backup.exists():
        progress('Backing up the original Fusion skin…')
        if current==recipe['source_sha256']:atomic_bytes(backup,TARGET.read_bytes())
        else:
            legacy=folder.parent.parent/'Oxygen-Fusion-Skin-Test/Original-Fusion.fuskin'
            if not legacy.exists() or digest(legacy)!=recipe['source_sha256']:raise ThemeUnavailable('The original backup is unavailable. Restore the earlier test with its original helper.')
            atomic_bytes(backup,legacy.read_bytes())
    if digest(backup)!=recipe['source_sha256']:raise ThemeUnavailable('Original backup changed. Refusing to write.')
    upgrading=action=='apply' and current in REVIEWED_UPGRADE_SKINS and current in legacy_hashes
    if action=='apply':
        if current in legacy_hashes and not upgrading:raise ThemeUnavailable('Restore the previous theme first, then apply Cherry Blossom.')
        guard();progress('Building and verifying the Fusion theme…')
        build_candidate(backup,candidate,load_profile(folder)['tokens'])
        if digest(candidate)!=recipe['candidate_sha256']:raise ThemeUnavailable('Generated patch differs from the reviewed candidate.')
    candidate_hash=current if action=='restore' and current in legacy_hashes else recipe['candidate_sha256']
    def checked_closed():guard();require_resolve_closed()
    if upgrading:
        progress('Restoring the verified original before the Step 2 upgrade…')
        SkinTransaction(TARGET,backup,candidate,storage/'Upgrade-Restore.json',
                        recipe['source_sha256'],current,checked_closed,progress).execute('restore')
    progress('Installing the Fusion theme…' if action=='apply' else 'Restoring the original Fusion skin…')
    tx=SkinTransaction(TARGET,backup,candidate,storage/'Transaction.json',recipe['source_sha256'],candidate_hash,checked_closed,progress)
    try:return tx.execute(action)
    except Exception as exc:
        if upgrading:raise ThemeUnavailable('Step 2 upgrade did not complete. The original backup is intact. Check theme status and use Restore Original before reopening Resolve. '+str(exc)) from exc
        raise

def operate(folder,action,progress=lambda message:None):
    if action not in ('apply','restore'):raise ValueError('Unknown theme action.')
    from theme_transaction import wait_for_resolve_closed
    progress('Checking that Resolve is closed…')
    wait_for_resolve_closed(progress) # Observe graceful exit before requesting UAC.
    import ctypes
    from theme_elevation import run_elevated,run_direct
    # Never attempt a protected write from the in-process UI worker. The first
    # write used to stall before PermissionError could trigger elevation.
    if ctypes.windll.shell32.IsUserAnAdmin():return run_direct(folder,action,progress)
    logging.info('Fusion theme %s requesting administrator access before installation',action)
    return run_elevated(folder,action,progress)

def apply_theme(folder,progress=lambda message:None):return operate(folder,'apply',progress)
def restore_original(folder,progress=lambda message:None):return operate(folder,'restore',progress)

def apply_cherry_theme(folder,progress=lambda message:None):
    """Preflight both layers before installing Fusion and starting a themed session."""
    from application_theme import validate_theme,launch_theme
    progress('Checking Cherry Blossom application resources…')
    validate_theme(folder) # Read-only and complete before any persistent change.
    support=capability(folder)
    if support['status']=='Unavailable':raise ThemeUnavailable(support['reason'])
    if support['can_apply']:
        apply_theme(folder,progress)
    elif not support['status'].startswith('Cherry Blossom installed'):
        raise ThemeUnavailable('Restore the previous Fusion skin before applying Cherry Blossom.')
    progress('Starting Resolve with Cherry Blossom application surfaces…')
    try:
        message=launch_theme(folder,progress)
    except Exception as exc:
        raise ThemeUnavailable('The Cherry Blossom Fusion skin is installed, but the application theme launch did not complete. '+str(exc)+' Close Resolve normally before Restore Original.') from exc
    return 'Cherry Blossom Fusion skin installed. '+message

def restore_cherry_original(folder,progress=lambda message:None):
    """Disable future application sessions and restore installed Fusion when needed.

    Session overrides disappear when Resolve closes. This operation never kills
    an active Resolve or changes its ordinary shortcuts.
    """
    from application_theme import disable_theme
    disable_theme(folder)
    support=capability(folder)
    if support['status']=='Unavailable':
        raise ThemeUnavailable(support['reason'])
    if support['can_restore']:
        return restore_original(folder,progress)
    if support['status']=='Original skin installed':
        return 'Original Fusion skin is installed. Application theme launch is disabled; use your regular Resolve shortcut for original application styles.'
    raise ThemeUnavailable('The original Fusion backup is unavailable. Application theme launch is disabled, but the installed Fusion skin has not been restored.')

def worker_main(folder,action,nonce):
    import faulthandler
    from theme_elevation import guard_request,paths,phase,write_json
    _,result,_,log=paths(folder,nonce)
    with log.with_suffix('.worker.log').open('a',encoding='utf-8') as output:
        faulthandler.dump_traceback_later(20,repeat=True,file=output)
        try:
            guard=lambda:guard_request(folder,nonce,action)
            guard()
            if action=='probe':
                import ctypes
                message='Read-only isolated worker completed (administrator access: '+('yes' if ctypes.windll.shell32.IsUserAnAdmin() else 'no')+'). No Resolve resources were changed.'
            else:message=direct_operation(folder,action,lambda text:phase(folder,nonce,text),guard)
            data={'ok':True,'message':message}
        except Exception as exc:
            traceback.print_exc(file=output)
            data={'ok':False,'message':str(exc)}
        finally:faulthandler.cancel_dump_traceback_later()
    write_json(result,data)

if __name__=='__main__':
    if len(sys.argv)!=4 or sys.argv[1]!='--theme-worker' or sys.argv[2] not in ('apply','restore','probe') or not re.fullmatch('[0-9a-f]{32}',sys.argv[3]):raise SystemExit(2)
    worker_main(Path(__file__).resolve().parent,*sys.argv[2:])
