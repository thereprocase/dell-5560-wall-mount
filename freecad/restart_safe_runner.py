from pathlib import Path
p=Path(__file__).with_name('live_runner.FCMacro')
exec(compile(p.read_text(encoding='utf-8-sig'),str(p),'exec'),{'__name__':'__main__','__file__':str(p)})
