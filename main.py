import argparse
import logging
import os
import sys
from pathlib import Path


def main():
    parser = argparse.ArgumentParser(description="SWARM STUDIO desktop")
    parser.add_argument("--data-dir", type=Path)
    parser.add_argument("--demo", action="store_true")
    parser.add_argument("--smoke-report", type=Path, help=argparse.SUPPRESS)
    parser.add_argument("--smoke-recording", action="store_true", help=argparse.SUPPRESS)
    args = parser.parse_args()
    from PySide6.QtCore import QCoreApplication, Qt
    from PySide6.QtWidgets import QApplication
    QCoreApplication.setAttribute(Qt.ApplicationAttribute.AA_ShareOpenGLContexts)
    QApplication.setApplicationName("Swarm Studio")
    QApplication.setOrganizationName("SwarmStudio")
    app = QApplication(sys.argv[:1])
    root = args.data_dir or Path(os.environ.get("LOCALAPPDATA", str(Path.home()))) / "SwarmStudio"
    root.mkdir(parents=True, exist_ok=True)
    logging.basicConfig(filename=root / "studio.log", level=logging.INFO,
                        format="%(asctime)s %(levelname)s %(message)s")
    from app.desktop import MainWindow
    window = MainWindow(root)
    window.showMaximized()
    if args.demo or args.smoke_report:
        window.open_demo()
    if args.smoke_report:
        from PySide6.QtCore import QTimer
        import json
        timer = QTimer(window)
        state = {'elapsed': 0, 'stage': 'load'}
        def smoke():
            state['elapsed'] += 1
            if state['stage'] == 'load' and window.browser.ready and window.player_ready:
                window.speed.setCurrentText('5×')
                state['stage'] = 'capture'
                window.start_capture()
            elif state['stage'] == 'capture' and window.project and window.engine_ready and window.progress.value() == 1000:
                state['stage'] = 'compare'
                window.run_comparison()
            elif state['stage'] == 'compare' and (window.project / 'metadata/quality-report.json').exists():
                state['stage'] = 'export'
                window.export_to(args.smoke_report.with_suffix('.zip'))
            complete = state['stage'] == 'export' and window.export_worker and not window.export_worker.isRunning()
            if complete and args.smoke_recording:
                from app.recording_dialog import RecordingDialog
                dialog=RecordingDialog(window)
                window.recording_dialog=dialog
                dialog.resolution.setCurrentIndex(1);dialog.fps.setCurrentIndex(1);dialog.speed.setCurrentIndex(4);dialog.sound.setChecked(True)
                dialog.worker=None
                dialog.start(args.smoke_report.with_suffix('.mp4'))
                dialog.worker.ready.connect(lambda path,result:state.update(movie=result))
                dialog.worker.error.connect(lambda message:state.update(movie_error=message))
                state['stage']='recording';complete=False
            if state['stage']=='recording':complete=bool(state.get('movie')) and not window.recording_worker.isRunning()
            if complete or state['elapsed'] >= (180 if args.smoke_recording else 90) or state.get('movie_error'):
                args.smoke_report.parent.mkdir(parents=True, exist_ok=True)
                args.smoke_report.write_text(json.dumps({'native_window': window.isVisible(), 'demo_loaded': window.browser.ready,
                    'player_loaded': window.player_ready, 'frozen': bool(getattr(sys, 'frozen', False)),
                    'workflow_complete': bool(complete), 'stage': state['stage'], 'tasks': len(window.blueprint['tasks']) if window.blueprint else 0,
                    'export_exists': args.smoke_report.with_suffix('.zip').is_file(),
                    'recording': state.get('movie'), 'recording_error': state.get('movie_error'),
                    'web_assets': str(window.server.root / 'ui'), 'url': window.source.url().toString()}, indent=2), 'utf-8')
                window.grab().save(str(args.smoke_report.with_suffix('.png')))
                timer.stop()
                window.close()
        timer.timeout.connect(smoke)
        timer.start(1000)
    return app.exec()


if __name__ == "__main__":
    sys.exit(main())
