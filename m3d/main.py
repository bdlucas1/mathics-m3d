import sys
import threading

import os
if not "MATHICS3_TIMING" in os.environ:
    os.environ["MATHICS3_TIMING"] = "-1"

import panel as pn

from m3d import core, sym, util # noqa
import m3d.app


#
# startup action depends on mode -
# building for pyodide, running under pyodide, or running as a server
#

if "DEMO_BUILD_PYODIDE" in os.environ:

    print("building for pyodide")
    app = m3d.app.App(load=[])
    app.servable()


elif "pyodide" in sys.modules:

    print("running under pyodide")
    app = m3d.app.App(load=["data/help.m3d"])
    app.servable()

else:
    print("running as local server")

    import argparse
    parser = argparse.ArgumentParser(
        prog="m3d",
        description="Mathics3+Markdown notebook viewer and editor")
    parser.add_argument(
        "--initial-mode", "-i",
        choices=["view","edit","help","open","save"],
        default="view"
    )
    parser.add_argument("--no-autorun", action="store_true")
    parser.add_argument("--show-code", action="store_true")        
    parser.add_argument("--test", action="store_true")
    parser.add_argument("--test-ui", action="store_true")
    parser.add_argument("--classic", action="store_true")
    parser.add_argument("--browser", "-b", default=None)
    parser.add_argument("file", nargs="*", type=str)
    args = parser.parse_args()

    # trigger tests if requested
    if args.test:
        import test.test
        m3d.app.test = test.test

    # exit when browser window closes
    # seems to take about 30 sec, probably a timeout
    def session_destroyed(session_context):
        if not pn.state.session_info["live"]:
            # delay to avoid races
            def quit():
                print("server exiting")
                os._exit(0) 
            threading.Timer(0.5, quit).start()
    pn.state.on_session_destroyed(session_destroyed)

    # start the app and point a browser at it
    app = m3d.app.App(
        load=args.file,
        initial_mode=args.initial_mode,
        show_code=args.show_code,
        autorun=not args.no_autorun,
        test_ui_run=args.test_ui,
        classic=args.classic,
    )
    title =  args.file
    util.show(app, title, browser=args.browser)
