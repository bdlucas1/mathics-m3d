import sys

import os
if not "MATHICS3_TIMING" in os.environ:
    os.environ["MATHICS3_TIMING"] = "-1"

import panel as pn

import mathics.builtin.drawing.plot
mathics.builtin.drawing.plot.use_vectorized_plot = True

import m3dlib
import util


#
# startup action depends on mode -
# building for pyodide, running under pyodide, or running as a server
#

if "DEMO_BUILD_PYODIDE" in os.environ:

    print("building for pyodide")
    app = m3dlib.App(load=[])
    app.servable()


elif "pyodide" in sys.modules:

    print("running under pyodide")
    app = m3dlib.App(load=["data/help.m3d"])
    app.servable()

else:
    print("running as local server")

    import argparse
    parser = argparse.ArgumentParser(description="m3d")
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
    parser.add_argument("files", nargs="*", type=str)
    args = parser.parse_args()

    # use vectorized plotting by default
    mathics.builtin.drawing.plot.use_vectorized_plot = not args.classic

    # trigger tests if requested
    if args.test:
        import test
        m3dlib.test = test

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
    app = m3dlib.App(
        load=args.files,
        initial_mode=args.initial_mode,
        show_code=args.show_code,
        autorun=not args.no_autorun,
        test_ui_run=args.test_ui,
    )
    title =  " ".join(["Markdown+Mathics3", *args.files])
    util.show(app, title, browser=args.browser)
